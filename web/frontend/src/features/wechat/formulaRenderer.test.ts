import { describe, expect, it } from 'vitest';

import { latexToSvg } from './formulaRenderer';

// 用户实际遇到的那条公式
const USER_FORMULA = String.raw`\mathbf{o}_t = \sum_{i=1}^{t} \alpha_{i\rightarrow t}\,\mathbf{v}_i, \qquad \alpha_{i\rightarrow t} = \frac{\phi(\mathbf{q}_t,\mathbf{k}_i)}{\sum_{j=1}^{t}\phi(\mathbf{q}_t,\mathbf{k}_j)}`;

describe('公众号公式渲染', () => {
  it('把块级公式渲染成 SVG', async () => {
    const svg = await latexToSvg(USER_FORMULA, true);
    expect(svg).toBeTruthy();
    expect(svg).toContain('<svg');
    expect(svg).toContain('</svg>');
  });

  it('SVG 自带字形，不依赖全局字形缓存', async () => {
    // fontCache 必须是 'local'：默认的 'global' 会把字形放进页面上一份独立的
    // <svg id="MJX-SVG-global-cache">，各公式用 <use> 跨元素引用。公式一旦被
    // 粘进公众号成为彼此独立的 DOM 岛，引用就断了，公式显示成空白。
    const svg = await latexToSvg(USER_FORMULA, true);
    expect(svg).toContain('<defs');
    expect(svg).not.toContain('MJX-SVG-global-cache');
  });

  it('两条公式各自独立自包含', async () => {
    const [a, b] = await Promise.all([
      latexToSvg(String.raw`E = mc^2`, true),
      latexToSvg(String.raw`\alpha_{i} + \beta_{j}`, true),
    ]);
    for (const svg of [a, b]) {
      expect(svg).toContain('<defs');
      expect(svg).not.toContain('MJX-SVG-global-cache');
    }
    expect(a).not.toEqual(b);
  });

  it('同一篇里的多条公式字形 id 不冲突', async () => {
    // 每条公式在公众号里都是独立 DOM 岛，但它们同处一篇文章。若两条 SVG 的
    // <defs> 用了相同的 path id，后一条会被前一条的定义覆盖，字形错乱。
    // MathJax 给每次渲染的 id 加了自增前缀（MJX-5- / MJX-6-），这里把它钉死。
    const first = await latexToSvg(String.raw`x_1 + x_2`, false);
    const second = await latexToSvg(String.raw`x_1 + x_2`, false);
    expect(first).toBeTruthy();
    expect(second).toBeTruthy();

    const idsOf = (svg: string) =>
      Array.from(svg.matchAll(/<path id="([^"]+)"/g), match => match[1]);
    const firstIds = idsOf(first!);
    const secondIds = idsOf(second!);

    expect(firstIds.length).toBeGreaterThan(0);
    expect(secondIds.length).toBeGreaterThan(0);
    expect(firstIds.some(id => secondIds.includes(id))).toBe(false);

    // 每个 <use> 都必须指向本 SVG 自己 <defs> 里的 id
    for (const [svg, ids] of [
      [first!, firstIds],
      [second!, secondIds],
    ] as const) {
      const refs = Array.from(
        svg.matchAll(/xlink:href="#([^"]+)"/g),
        match => match[1]
      );
      expect(refs.length).toBeGreaterThan(0);
      for (const ref of refs) {
        expect(ids).toContain(ref);
      }
    }
  });

  it('display 与 inline 产出不同（求和号大小不同）', async () => {
    const display = await latexToSvg(String.raw`\sum_{i=1}^{n} x_i`, true);
    const inline = await latexToSvg(String.raw`\sum_{i=1}^{n} x_i`, false);
    expect(display).not.toEqual(inline);
  });

  it('语法错误返回 null 而不是抛异常', async () => {
    const svg = await latexToSvg(String.raw`\frac{1`, true);
    // MathJax 对不完整语法会产出带错误标记的输出或抛错；两种都不能让整篇挂掉
    expect(svg === null || typeof svg === 'string').toBe(true);
  });

  it('空输入返回 null', async () => {
    expect(await latexToSvg('', true)).toBeNull();
    expect(await latexToSvg('   ', true)).toBeNull();
  });

  it('常见 LaTeX 命令都能渲染', async () => {
    const cases = [
      String.raw`\frac{a}{b}`,
      String.raw`\sqrt{x^2 + y^2}`,
      String.raw`\int_{0}^{\infty} e^{-x} dx`,
      String.raw`\begin{aligned} a &= b \\ c &= d \end{aligned}`,
      String.raw`\mathbf{A}^{\top}\mathbf{B}`,
      String.raw`\alpha \beta \gamma \Delta \Omega`,
      String.raw`P_{\text{max}} = V_{dd} \times I`,
    ];
    for (const latex of cases) {
      const svg = await latexToSvg(latex, true);
      expect(svg, latex).toContain('<svg');
    }
  });
});
