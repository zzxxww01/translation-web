/**
 * 把后端标记出来的公式节点渲染成公众号能承载的内嵌 SVG。
 *
 * 为什么是 SVG：公众号正文没有 MathJax/KaTeX 运行环境，也不执行 JS，公式只能在
 * 发布前变成图形。而公众号正文**支持以 DOM 形式内嵌 SVG**（"SVG 互动排版"就是
 * 基于这一点），所以矢量内嵌比转位图更好——不失真，也不需要图床和公网可达地址。
 *
 * 为什么是 MathJax 而不是 KaTeX：KaTeX 至今没有 SVG 输出（KaTeX#375），它产出的是
 * HTML+CSS，而外部样式表进了公众号会被剥掉，公式会散架。
 *
 * ## 为什么用 es5 bundle 而不是 js/ 下的模块
 *
 * `mathjax-full/js/**` 是 CommonJS，内部（components/version.js）有 vite 无法静态
 * 转换的动态 require。它在 Node 下正常，所以单测全绿；但在浏览器里必定抛
 * `ReferenceError: require is not defined`，而 getEngine 的 catch 会把它静默吞掉，
 * 于是公式**整篇降级成 LaTeX 原文**——线上一直是这个状态，测试却一片绿。
 * `es5/tex-svg-full.js` 是官方给浏览器用的预打包 bundle，自包含、无 require。
 *
 * ## 公众号对 SVG 的限制（决定了 sanitizeSvg 做哪些事）
 *
 * 1. **`<path>` 上不允许有 id**，因此不能用 `<use xlink:href>` 引用字形——
 *    `fontCache: 'none'` 让字形直接内联成 path，没有 id 也没有引用。
 * 2. **`data-*` 不在属性白名单里**。最危险的是 `data-mml-node="TeXAtom"`：
 *    公众号会把这个组元素**以及它之外的所有组一起删掉**，公式直接变白纸。
 *    统一删掉所有 `data-*` 即可——`<g>` 元素本身和它的 transform 都保留，
 *    结构完整。
 * 3. **`<mjx-container>` 是自定义标签**，不在白名单，会被当未知元素处理成块级，
 *    行内公式于是条条断行、正文被切碎。只保留 `<svg>`。
 * 4. **尺寸 `ex` 换算成 px**：公众号里正文字体不受我们控制，ex 取决于字体的
 *    x-height，换个字体公式大小就飘了。
 */

/** 传给 tex2svg 的度量基准：SVG 里的 ex 尺寸都以它为准，换算 px 时要一致。 */
const EX_IN_PX = 8;
const EM_IN_PX = 16;

type MathJaxGlobal = {
  startup: { promise: Promise<unknown> };
  tex2svg: (latex: string, options: Record<string, unknown>) => HTMLElement;
};

let enginePromise: Promise<MathJaxGlobal> | null = null;

/** MathJax 体积较大（约 2.2MB），只在真正遇到公式时才拉起来，且全应用只初始化一次。 */
async function getEngine(): Promise<MathJaxGlobal> {
  if (!enginePromise) {
    enginePromise = (async () => {
      const scope = window as unknown as Record<string, unknown>;
      // 启动配置必须在 bundle 加载**之前**挂上去，加载后 window.MathJax 会被
      // 替换成 API 对象。
      scope.MathJax = {
        startup: { typeset: false },
        svg: { fontCache: 'none' },
        options: { enableMenu: false },
      };
      await import('mathjax-full/es5/tex-svg-full.js');
      const mathJax = scope.MathJax as MathJaxGlobal;
      if (!mathJax?.startup?.promise || typeof mathJax.tex2svg !== 'function') {
        throw new Error('MathJax bundle loaded but tex2svg is unavailable');
      }
      await mathJax.startup.promise;
      return mathJax;
    })().catch(error => {
      // 允许下次重试，不要把失败永久缓存住
      enginePromise = null;
      throw error;
    });
  }
  return enginePromise;
}

/** `ex` 是相对单位，公众号里字体不受控，统一换成 px。 */
function exToPx(value: string): string {
  return value.replace(
    /(-?[\d.]+)ex/g,
    (_match, num: string) => `${(parseFloat(num) * EX_IN_PX).toFixed(2)}px`
  );
}

/**
 * 把 MathJax 的 SVG 整理成公众号能安全承载的形态。理由见文件头「公众号对 SVG
 * 的限制」。纯字符串处理，不碰 DOM，因此可以在 Node 下直接测试。
 */
export function sanitizeSvg(svgHtml: string, display: boolean): string | null {
  const start = svgHtml.indexOf('<svg');
  const end = svgHtml.lastIndexOf('</svg>');
  if (start === -1 || end === -1) return null;
  let svg = svgHtml.slice(start, end + '</svg>'.length);

  // data-* 全部去掉（含 data-mml-node="TeXAtom"，留着会让公众号删光整片公式）；
  // aria-hidden / xlink 同样在白名单之外。
  svg = svg
    .replace(/\sdata-[\w-]+="[^"]*"/g, '')
    .replace(/\saria-hidden="[^"]*"/g, '')
    .replace(/\sxmlns:xlink="[^"]*"/g, '');

  // 只改根 <svg> 的开标签：SVG 内部元素的 width/height 是用户坐标系里的无单位
  // 数值，style 也各有用途，一起改会让公式错位。
  const tagEnd = svg.indexOf('>');
  if (tagEnd === -1) return null;
  let openTag = svg.slice(0, tagEnd + 1);
  const body = svg.slice(tagEnd + 1);

  openTag = openTag.replace(
    /\s(width|height)="([^"]*)"/g,
    (_match, attr: string, value: string) => ` ${attr}="${exToPx(value)}"`
  );

  // MathJax 把行内公式相对基线的偏移写在 style 的 vertical-align 里，必须保留：
  // 用外层 wrapper 的 vertical-align 覆盖掉，公式就会相对文字上下错位。
  if (/\sstyle="/.test(openTag)) {
    openTag = openTag.replace(/\sstyle="([^"]*)"/, (_match, style: string) => {
      const declarations = exToPx(style)
        .split(';')
        .map(part => part.trim())
        .filter(Boolean);
      if (!display) declarations.push('display:inline-block');
      return ` style="${declarations.join(';')};"`;
    });
  } else if (!display) {
    openTag = openTag.replace(/^<svg/, '<svg style="display:inline-block;"');
  }

  return openTag + body;
}

/**
 * 把一条 LaTeX 渲染成公众号可用的自包含 SVG 字符串。
 *
 * 渲染失败返回 null，由调用方决定降级。
 */
export async function latexToSvg(
  latex: string,
  display: boolean
): Promise<string | null> {
  if (!latex.trim()) return null;
  try {
    const mathJax = await getEngine();
    const container = mathJax.tex2svg(latex, {
      display,
      em: EM_IN_PX,
      ex: EX_IN_PX,
      containerWidth: display ? 800 : 400,
    });
    const svg = container.querySelector('svg');
    if (!svg) return null;
    return sanitizeSvg(svg.outerHTML, display);
  } catch {
    return null;
  }
}

export interface FormulaRenderResult {
  html: string;
  rendered: number;
  failed: number;
}

const BLOCK_WRAPPER_STYLE =
  'margin:16px 0;text-align:center;overflow-x:auto;';

/**
 * 渲染 `html` 里所有带 `data-latex` 的节点。
 *
 * 渲染失败的单条公式**保持原样**（后端留的等宽 LaTeX 降级），不会让整篇失败。
 */
export async function renderFormulas(html: string): Promise<FormulaRenderResult> {
  if (!html || !html.includes('data-latex')) {
    return { html, rendered: 0, failed: 0 };
  }

  const container = document.createElement('div');
  container.innerHTML = html;
  const nodes = Array.from(container.querySelectorAll<HTMLElement>('[data-latex]'));
  if (nodes.length === 0) {
    return { html, rendered: 0, failed: 0 };
  }

  try {
    await getEngine();
  } catch {
    // 引擎起不来就整体降级，正文与等宽公式仍然可用
    return { html, rendered: 0, failed: nodes.length };
  }

  let rendered = 0;
  let failed = 0;

  for (const node of nodes) {
    const latex = node.getAttribute('data-latex') || '';
    const isBlock = node.getAttribute('data-formula') === 'block';
    const svg = await latexToSvg(latex, isBlock);
    if (!svg) {
      failed += 1;
      continue;
    }

    if (isBlock) {
      const wrapper = document.createElement('section');
      wrapper.setAttribute('style', BLOCK_WRAPPER_STYLE);
      wrapper.innerHTML = svg;
      node.replaceWith(wrapper);
    } else {
      // 行内公式不包 wrapper：多一层元素就多一次被公众号过滤器改写的机会，
      // 而且 SVG 自己的 vertical-align 已经对好了基线，外层再对齐只会打架。
      const holder = document.createElement('span');
      holder.innerHTML = svg;
      const svgElement = holder.firstElementChild;
      if (!svgElement) {
        failed += 1;
        continue;
      }
      node.replaceWith(svgElement);
    }
    rendered += 1;
  }

  return { html: container.innerHTML, rendered, failed };
}
