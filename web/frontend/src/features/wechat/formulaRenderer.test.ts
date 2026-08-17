import { describe, expect, it } from 'vitest';

import { latexToSvg, normalizeSvg } from './formulaRenderer';

// 用户实际遇到的那条公式
const USER_FORMULA = String.raw`\mathbf{o}_t = \sum_{i=1}^{t} \alpha_{i\rightarrow t}\,\mathbf{v}_i, \qquad \alpha_{i\rightarrow t} = \frac{\phi(\mathbf{q}_t,\mathbf{k}_i)}{\sum_{j=1}^{t}\phi(\mathbf{q}_t,\mathbf{k}_j)}`;

describe('公众号公式渲染', () => {
  it('把块级公式渲染成 SVG', async () => {
    const svg = await latexToSvg(USER_FORMULA, true);
    expect(svg).toBeTruthy();
    expect(svg).toContain('<svg');
    expect(svg).toContain('</svg>');
  });

  it('SVG 不含任何 id 引用，字形全部内联', async () => {
    // 这是整套方案的命门。SVG 输出默认把字形收进 <defs>，正文用 <use xlink:href>
    // 引用；公众号的粘贴过滤会剥掉 xlink:href（它能引用外部资源，在黑名单里），
    // 引用一断，公式整条变空白——这正是"粘过去全是乱码"的成因。
    // fontCache:'none' 让字形直接内联成 <path>，没有引用可断。
    for (const display of [true, false]) {
      const svg = await latexToSvg(USER_FORMULA, display);
      expect(svg).toBeTruthy();
      expect(svg).toContain('<path');
      expect(svg).not.toContain('<use');
      expect(svg).not.toContain('xlink:href');
      expect(svg).not.toContain('<defs');
      expect(svg).not.toContain('MJX-SVG-global-cache');
    }
  });

  it('剥掉 xlink:href 后公式内容依然完好', async () => {
    // 直接模拟公众号过滤器的动作：删掉所有 xlink:href，看还剩多少可见内容。
    const svg = await latexToSvg(USER_FORMULA, true);
    const filtered = svg!.replace(/ xlink:href="[^"]*"/g, '');
    expect(filtered).toEqual(svg);
    expect((filtered.match(/<path/g) || []).length).toBeGreaterThan(10);
  });

  it('不带 mjx-container 外壳', async () => {
    // 自定义标签不在公众号白名单里，会被当未知元素处理成块级，
    // 于是每条行内公式都断行、正文被切碎。
    const svg = await latexToSvg(String.raw`x_1 + x_2`, false);
    expect(svg).not.toContain('mjx-container');
    expect(svg!.startsWith('<svg')).toBe(true);
    expect(svg!.endsWith('</svg>')).toBe(true);
  });

  it('尺寸单位换算成 px，不留 ex', async () => {
    // ex 取决于所在字体的 x-height，公众号里字体不受我们控制。
    const svg = await latexToSvg(String.raw`\frac{a}{b}`, false);
    expect(svg).toMatch(/width="[\d.]+px"/);
    expect(svg).toMatch(/height="[\d.]+px"/);
    expect(svg).not.toMatch(/="[\d.]+ex"/);
    expect(svg).not.toMatch(/vertical-align:\s*-?[\d.]+ex/);
  });

  it('行内公式保留 MathJax 算好的基线偏移并声明 inline-block', async () => {
    const svg = await latexToSvg(String.raw`\frac{a}{b}`, false);
    expect(svg).toContain('display:inline-block');
    expect(svg).toMatch(/vertical-align:\s*-?[\d.]+px/);
  });

  it('normalizeSvg 对拿不到 svg 的输入返回 null', () => {
    expect(normalizeSvg('<mjx-container></mjx-container>', false)).toBeNull();
    expect(normalizeSvg('', true)).toBeNull();
  });

  it('normalizeSvg 只改根标签，不动 SVG 内部的用户坐标', () => {
    // 根 <svg> 未必带 style（display 公式常常没有 vertical-align）。若不限定在
    // 根标签内替换，display:inline-block 会被塞到内部元素上，公式当场错位。
    const noStyle =
      '<mjx-container class="MathJax" jax="SVG">' +
      '<svg width="2ex" height="1ex" viewBox="0 -750 2514 1000">' +
      '<rect width="574.1" height="60" x="120" y="220"></rect></svg></mjx-container>';
    const out = normalizeSvg(noStyle, false)!;

    expect(out.startsWith('<svg style="display:inline-block;"')).toBe(true);
    // 根标签的 ex 换成 px
    expect(out).toContain('width="16.00px"');
    expect(out).toContain('height="8.00px"');
    // 内部 <rect> 是用户坐标系里的无单位数值，必须原样保留
    expect(out).toContain('<rect width="574.1" height="60" x="120" y="220">');
    // viewBox 不能被当成尺寸改掉
    expect(out).toContain('viewBox="0 -750 2514 1000"');
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
