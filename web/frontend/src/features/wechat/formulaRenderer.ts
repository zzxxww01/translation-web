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
 * ## 按需构建
 * 仅加载 TeX、SVG 和内置数学扩展，不加载完整 startup/menu bundle。
 * MathJax 3.2.1 的 Node 版本查询由 Vite 的 PACKAGE_VERSION 常量消除；
 * Chromium 回归同时验证导入成功和 SVG 实际生成，不能只看 Node 单测。
 * 外部 require/autoload 扩展不允许在导入文档中触发网络加载。
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

type FormulaEngine = {
  tex2svg: (latex: string, options: Record<string, unknown>) => HTMLElement;
};
let enginePromise: Promise<FormulaEngine> | null = null;

async function getEngine(): Promise<FormulaEngine> {
  if (!enginePromise) {
    enginePromise = import('./mathjaxEngine')
      .then(module => module.createEngine())
      .catch(error => {
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
  if (!latex.trim() || latex.length > 32 * 1024) return null;
  try {
    const mathJax = await getEngine();
    const container = mathJax.tex2svg(latex, {
      display,
      em: EM_IN_PX,
      ex: EX_IN_PX,
      containerWidth: display ? 800 : 400,
    });
    if (container.querySelector('[data-mjx-error], [data-mml-node="merror"]')) return null;
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
    // Large documents must yield so progress, cancellation and user edits paint.
    if ((rendered + failed) % 20 === 0) {
      await new Promise<void>(resolve => setTimeout(resolve, 0));
    }
  }

  return { html: container.innerHTML, rendered, failed };
}
