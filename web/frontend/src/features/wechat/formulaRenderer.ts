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
 * 关键实现点：`fontCache: 'local'`。MathJax 的 SVG 输出默认把字形放进一份全局
 * `<defs>`，各公式用 `<use>` 引用。一旦每条公式变成公众号正文里彼此独立的 DOM
 * 岛，引用就断了，公式会显示成空白。local 让每个 SVG 自带字形路径。
 */

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
        // fontCache: 'local' 是硬要求，理由见文件头
        OutputJax: new SVG({ fontCache: 'local' }),
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
      em: 16,
      ex: 8,
      containerWidth: display ? 800 : 400,
    });
    const svg = adaptor.outerHTML(node);
    return svg && svg.includes('<svg') ? svg : null;
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
const INLINE_WRAPPER_STYLE = 'display:inline-block;vertical-align:middle;';

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

    const wrapper = document.createElement(isBlock ? 'section' : 'span');
    wrapper.setAttribute('style', isBlock ? BLOCK_WRAPPER_STYLE : INLINE_WRAPPER_STYLE);
    wrapper.innerHTML = svg;
    node.replaceWith(wrapper);
    rendered += 1;
  }

  return { html: container.innerHTML, rendered, failed };
}
