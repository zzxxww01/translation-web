/**
 * 把后端标记出来的公式节点渲染成独立 SVG。
 *
 * 为什么是 SVG：公众号正文没有 MathJax/KaTeX 运行环境，也不执行 JS，公式只能在
 * 发布前变成图形。而公众号正文**支持以 DOM 形式内嵌 SVG**（"SVG 互动排版"就是
 * 基于这一点），所以矢量内嵌比转位图更好——不失真，也不需要图床和公网可达地址。
 *
 * 为什么是 MathJax 而不是 KaTeX：KaTeX 至今没有 SVG 输出（KaTeX#375），它产出的是
 * HTML+CSS，而外部样式表进了公众号会被剥掉，公式会散架。
 *
 * 关键实现点，都是为了扛住公众号粘贴时的 HTML 过滤：
 *
 * 1. `fontCache: 'none'`。SVG 输出默认把字形收进 `<defs>`、正文用 `<use xlink:href>`
 *    引用（'global' 是跨公式共享一份，'local' 是每条公式一份）。但公众号会剥掉
 *    `xlink:href`——它是能引用外部资源的属性，在过滤器的黑名单里——引用一断，
 *    公式就整条变成空白。'none' 让每个字形直接内联成 `<path>`，零引用、零 id，
 *    过滤器再怎么删属性都拿它没办法。代价是块级公式体积涨约 25%，
 *    但行内公式反而更小（省掉了 defs + use 的双份开销）。
 * 2. 去掉 MathJax 的 `<mjx-container>` 外壳，只留 `<svg>`。自定义标签不在公众号
 *    白名单里，会被当成未知元素处理成块级，行内公式于是条条断行、正文被切碎。
 * 3. 尺寸从 `ex` 换算成 `px`。公众号里正文字体不受我们控制，`ex` 取决于字体的
 *    x-height，换个字体公式大小就飘了。
 */

/** convert() 传入的 ex 值：SVG 里的 ex 尺寸都以它为基准，换算成 px 时要一致。 */
const EX_IN_PX = 8;
const EM_IN_PX = 16;

type MathDocument = {
  convert: (latex: string, options: Record<string, unknown>) => unknown;
};

type Adaptor = {
  outerHTML: (node: unknown) => string;
};

let enginePromise: Promise<{ doc: MathDocument; adaptor: Adaptor }> | null = null;

/** MathJax 体积较大，只在真正遇到公式时才拉起来，且全应用只初始化一次。 */
async function getEngine() {
  if (!enginePromise) {
    enginePromise = (async () => {
      const [
        { mathjax },
        { TeX },
        { SVG },
        { liteAdaptor },
        { RegisterHTMLHandler },
        { AllPackages },
      ] = await Promise.all([
        import('mathjax-full/js/mathjax.js'),
        import('mathjax-full/js/input/tex.js'),
        import('mathjax-full/js/output/svg.js'),
        import('mathjax-full/js/adaptors/liteAdaptor.js'),
        import('mathjax-full/js/handlers/html.js'),
        import('mathjax-full/js/input/tex/AllPackages.js'),
      ]);

      const adaptor = liteAdaptor();
      RegisterHTMLHandler(adaptor);

      const doc = mathjax.document('', {
        InputJax: new TeX({ packages: AllPackages }),
        // fontCache: 'none' 是硬要求，理由见文件头第 1 点
        OutputJax: new SVG({ fontCache: 'none' }),
      });

      return { doc: doc as unknown as MathDocument, adaptor: adaptor as unknown as Adaptor };
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
 * 把 MathJax 的输出整理成公众号能安全承载的形态：脱掉 `<mjx-container>` 外壳、
 * 尺寸换成 px、行内公式显式声明 inline-block。
 *
 * 纯字符串处理，不碰 DOM，因此可以在 Node 下直接测试。导出仅为测试可见。
 */
export function normalizeSvg(containerHtml: string, display: boolean): string | null {
  const start = containerHtml.indexOf('<svg');
  const end = containerHtml.lastIndexOf('</svg>');
  if (start === -1 || end === -1) return null;
  const svg = containerHtml.slice(start, end + '</svg>'.length);

  // 只改根 <svg> 的开标签。SVG 内部元素（<rect> 等）的 width/height 是用户坐标系
  // 里的无单位数值，style 也各有用途，一起改会让公式错位。
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
 * 把一条 LaTeX 渲染成自包含的 SVG 字符串。
 *
 * 不碰 DOM（liteAdaptor 用的是自己的轻量节点树），因此可以在 Node 下直接测试。
 * 渲染失败返回 null，由调用方决定降级。
 */
export async function latexToSvg(
  latex: string,
  display: boolean
): Promise<string | null> {
  if (!latex.trim()) return null;
  try {
    const { doc, adaptor } = await getEngine();
    const node = doc.convert(latex, {
      display,
      em: EM_IN_PX,
      ex: EX_IN_PX,
      containerWidth: display ? 800 : 400,
    });
    const svg = adaptor.outerHTML(node);
    return svg && svg.includes('<svg') ? normalizeSvg(svg, display) : null;
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
