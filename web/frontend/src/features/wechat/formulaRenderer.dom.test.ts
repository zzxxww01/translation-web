// @vitest-environment jsdom
//
// renderFormulas 的另一半——真正操作 DOM 的那半——此前完全没有覆盖：项目没装
// jsdom，"通过"的测试只跑到了 latexToSvg。而公式在公众号里散架，恰恰散在这一层：
// 节点换成了什么、还在不在原来的段落里、失败时降级成什么。
import { describe, expect, it } from 'vitest';

import { renderFormulas } from './formulaRenderer';

/** 后端 _restore_math 的真实产出形态 */
const inlineNode = (latex: string) =>
  `<code data-formula="inline" data-latex="${latex}" style="font-family:Consolas;">$${latex}$</code>`;
const blockNode = (latex: string) =>
  `<section data-formula="block" data-latex="${latex}" style="margin:16px 0;">` +
  `<code style="font-family:Consolas;">$$${latex}$$</code></section>`;

describe('renderFormulas（DOM）', () => {
  it('没有公式时原样返回，不动 HTML', async () => {
    const html = '<p>一段没有公式的正文。</p>';
    const result = await renderFormulas(html);
    expect(result).toEqual({ html, rendered: 0, failed: 0 });
  });

  it('行内公式替换为 svg 且留在原段落内', async () => {
    // 这条钉的就是"行内公式条条断行"的回归：公式必须还是段落的行内子节点，
    // 既不能被提成块级，也不能把段落拆成两半。
    const html = `<p>只有 ${inlineNode('m')} 会影响这个比值。</p>`;
    const result = await renderFormulas(html);

    expect(result.rendered).toBe(1);
    expect(result.failed).toBe(0);

    const container = document.createElement('div');
    container.innerHTML = result.html;

    const paragraphs = container.querySelectorAll('p');
    expect(paragraphs).toHaveLength(1);

    const svg = paragraphs[0].querySelector('svg');
    expect(svg).not.toBeNull();
    // 不包 wrapper：svg 是段落的直接子节点
    expect(svg!.parentElement!.tagName.toLowerCase()).toBe('p');
    expect(container.querySelector('section')).toBeNull();
    // 公式两侧的正文都还在，没有被切断
    expect(paragraphs[0].textContent).toContain('只有');
    expect(paragraphs[0].textContent).toContain('会影响这个比值');
  });

  it('块级公式包进居中的 section', async () => {
    const html = `<p>推导如下：</p>${blockNode('E = mc^2')}`;
    const result = await renderFormulas(html);

    expect(result.rendered).toBe(1);
    const container = document.createElement('div');
    container.innerHTML = result.html;

    const section = container.querySelector('section');
    expect(section).not.toBeNull();
    expect(section!.getAttribute('style')).toContain('text-align:center');
    expect(section!.querySelector('svg')).not.toBeNull();
    expect(section!.querySelector('code')).toBeNull();
  });

  it('列表项里的行内公式不破坏列表结构', async () => {
    const html =
      `<ul><li>${inlineNode('t')}：输入 token 总数</li>` +
      `<li>${inlineNode('K')}：激活的专家数</li></ul>`;
    const result = await renderFormulas(html);

    expect(result.rendered).toBe(2);
    const container = document.createElement('div');
    container.innerHTML = result.html;

    const items = container.querySelectorAll('li');
    expect(items).toHaveLength(2);
    for (const item of items) {
      expect(item.querySelector('svg')).not.toBeNull();
      expect(item.textContent).toContain('：');
    }
  });

  it('单条公式渲染失败只降级该条，其余照常', async () => {
    // 空的 data-latex 必定拿不到 SVG，用它触发降级路径
    const html = `<p>${inlineNode('')} 和 ${inlineNode('x^2')}</p>`;
    const result = await renderFormulas(html);

    expect(result.rendered).toBe(1);
    expect(result.failed).toBe(1);

    const container = document.createElement('div');
    container.innerHTML = result.html;
    // 失败那条保留原样（等宽 LaTeX 降级），成功那条变成 svg
    expect(container.querySelector('code[data-formula]')).not.toBeNull();
    expect(container.querySelector('svg')).not.toBeNull();
  });

  it('同一篇里的多条公式互不干扰', async () => {
    const html =
      `<p>${inlineNode('a')} 与 ${inlineNode('b')}</p>` +
      `${blockNode('\\frac{a}{b}')}${blockNode('\\sqrt{x}')}`;
    const result = await renderFormulas(html);

    expect(result.rendered).toBe(4);
    expect(result.failed).toBe(0);

    const container = document.createElement('div');
    container.innerHTML = result.html;
    expect(container.querySelectorAll('svg')).toHaveLength(4);
    // 公众号里每条公式都是独立 DOM 岛：不能有跨 SVG 的 id 引用
    expect(result.html).not.toContain('<use');
    expect(result.html).not.toContain('xlink:href');
  });

  it('渲染后不残留 data-latex 标记与 mjx-container', async () => {
    const html = `<p>${inlineNode('m')}</p>${blockNode('E = mc^2')}`;
    const result = await renderFormulas(html);

    expect(result.html).not.toContain('data-latex');
    expect(result.html).not.toContain('data-formula');
    expect(result.html).not.toContain('mjx-container');
  });
});
