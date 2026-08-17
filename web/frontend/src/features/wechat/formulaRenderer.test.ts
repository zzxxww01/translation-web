import { describe, expect, it } from 'vitest';

import { sanitizeSvg } from './formulaRenderer';

// 真实的 MathJax es5(tex-svg-full, fontCache:'none') 输出，取自浏览器里渲染的
// `tK/E`，仅把超长的 path d 截短。结构原样保留：aria-hidden、ex 尺寸、
// data-mml-node / data-c / data-mjx-texclass，以及一个带 transform 的 TeXAtom 组。
const REAL_INLINE_SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" width="5.688ex" height="2.262ex" ' +
  'role="img" focusable="false" viewBox="0 -750 2514 1000" aria-hidden="true" ' +
  'style="vertical-align: -0.566ex;">' +
  '<g stroke="currentColor" fill="currentColor" stroke-width="0" transform="scale(1,-1)">' +
  '<g data-mml-node="math">' +
  '<g data-mml-node="mi"><path data-c="1D461" d="M26 385Q19 392 19 395Z"></path></g>' +
  '<g data-mml-node="mi" transform="translate(361,0)">' +
  '<path data-c="1D43E" d="M285 628Q285 635 228 637Z"></path></g>' +
  '<g data-mml-node="TeXAtom" data-mjx-texclass="ORD" transform="translate(1250,0)">' +
  '<g data-mml-node="mo"><path data-c="2F" d="M423 750Q432 750 438 744Z"></path></g></g>' +
  '</g></g></svg>';

describe('sanitizeSvg（公众号 SVG 净化）', () => {
  it('删光 data-*，但保留 <g> 与它的 transform', () => {
    // data-mml-node="TeXAtom" 是最危险的一个：公众号会把这个组元素以及它之外的
    // 所有组一起删掉，公式直接变白纸。但组上的 transform 是坐标偏移，丢了公式错位，
    // 所以只能删属性、不能删元素。
    const out = sanitizeSvg(REAL_INLINE_SVG, false)!;

    expect(out).not.toContain('data-');
    expect(out).not.toContain('TeXAtom');
    expect(out).toContain('<g transform="translate(1250,0)">');
    expect(out).toContain('transform="translate(361,0)"');
    expect(out).toContain('transform="scale(1,-1)"');
    // 组的层级数量不变，只是没了标记属性
    expect((out.match(/<g/g) || []).length).toBe(
      (REAL_INLINE_SVG.match(/<g/g) || []).length
    );
  });

  it('删掉 aria-hidden 与 xmlns:xlink，保留 xmlns', () => {
    const withXlink = REAL_INLINE_SVG.replace(
      '<svg ',
      '<svg xmlns:xlink="http://www.w3.org/1999/xlink" '
    );
    const out = sanitizeSvg(withXlink, false)!;

    expect(out).not.toContain('aria-hidden');
    expect(out).not.toContain('xlink');
    expect(out).toContain('xmlns="http://www.w3.org/2000/svg"');
  });

  it('不含 <use> 与 <path id>：公众号不允许 path 上有 id', () => {
    // fontCache:'none' 的产出本就不该有这两样，这里把契约钉住——一旦有人把
    // fontCache 改回 local/global，公式在公众号里会整条变空白。
    const out = sanitizeSvg(REAL_INLINE_SVG, false)!;
    expect(out).not.toContain('<use');
    expect(out).not.toContain('<path id=');
    expect(out).toContain('<path');
  });

  it('根标签的 ex 换成 px，内部用户坐标不动', () => {
    const out = sanitizeSvg(REAL_INLINE_SVG, false)!;

    expect(out).toContain('width="45.50px"'); // 5.688ex * 8
    expect(out).toContain('height="18.10px"'); // 2.262ex * 8
    expect(out).toMatch(/vertical-align:\s*-4\.53px/); // -0.566ex * 8
    expect(out).not.toMatch(/[\d.]+ex/);
    // viewBox 与 path 的 d 是用户坐标，必须原样
    expect(out).toContain('viewBox="0 -750 2514 1000"');
    expect(out).toContain('d="M26 385Q19 392 19 395Z"');
  });

  it('行内公式声明 inline-block 并保留基线偏移', () => {
    const out = sanitizeSvg(REAL_INLINE_SVG, false)!;
    expect(out).toContain('display:inline-block');
    expect(out).toMatch(/vertical-align:\s*-?[\d.]+px/);
  });

  it('块级公式不加 inline-block', () => {
    const out = sanitizeSvg(REAL_INLINE_SVG, true)!;
    expect(out).not.toContain('display:inline-block');
  });

  it('根标签没有 style 时也能补上 inline-block', () => {
    // display 公式常常没有 vertical-align。若不单独处理，行内声明会被塞到
    // SVG 内部某个元素上，公式当场错位。
    const noStyle = REAL_INLINE_SVG.replace(' style="vertical-align: -0.566ex;"', '');
    const out = sanitizeSvg(noStyle, false)!;

    expect(out.startsWith('<svg style="display:inline-block;"')).toBe(true);
    expect(out).toContain('width="45.50px"');
  });

  it('剥掉外层 mjx-container，只留 svg', () => {
    const wrapped = `<mjx-container class="MathJax" jax="SVG">${REAL_INLINE_SVG}</mjx-container>`;
    const out = sanitizeSvg(wrapped, false)!;

    expect(out).not.toContain('mjx-container');
    expect(out.startsWith('<svg')).toBe(true);
    expect(out.endsWith('</svg>')).toBe(true);
  });

  it('拿不到 svg 的输入返回 null', () => {
    expect(sanitizeSvg('<mjx-container></mjx-container>', false)).toBeNull();
    expect(sanitizeSvg('', true)).toBeNull();
  });
});
