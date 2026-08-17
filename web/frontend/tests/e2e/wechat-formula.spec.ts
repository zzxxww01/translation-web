import { expect, test } from '@playwright/test';

/**
 * 公式渲染只能在**真实浏览器**里验证。
 *
 * 教训：`mathjax-full/js/**` 是 CommonJS，Node 与 jsdom 原生支持 require，所以
 * 单测一片绿；浏览器里却必定抛 `ReferenceError: require is not defined`，再被
 * getEngine 的 catch 静默吞掉，公式整篇降级成 LaTeX 原文。线上坏了很久，测试
 * 从未报警。这个 spec 就是为了堵住那个盲区——它必须跑在真实浏览器上。
 */

const MARKDOWN = String.raw`推导如下：

$$
\mathrm{Comm}_{\mathrm{cached}}
=
\underbrace{\frac{P(P-1)}{2}N_p d}_{\text{first virtual stage}}
+
\underbrace{(V-1)P^2N_p d}_{\text{subsequent virtual stages}}
$$

其中输出 token $t$ 是加权和，$tK/E$ 为每卡 token 数。

结束。`;

test('微信排版把公式渲染成公众号可用的内嵌 SVG', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('pageerror', error => consoleErrors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  await page.goto('/wechat');

  await page.getByLabel('Markdown 内容').fill(MARKDOWN);
  await page.getByRole('button', { name: '转换' }).click();

  const preview = page.frameLocator('iframe[title="微信排版预览"]');
  // MathJax 是懒加载的（约 2.2MB），首次渲染要等 bundle 落地
  await expect(preview.locator('svg').first()).toBeVisible({ timeout: 60_000 });

  const html = await preview.locator('body').innerHTML();

  // 1 条块级 + 2 条行内，一条都不能降级。
  // 只数顶层 svg：MathJax 对拉伸构造（\underbrace 的花括号）会产出嵌套 <svg>，
  // 直接数标签会多出来。嵌套的那些用无单位用户坐标，不受 ex→px 换算影响。
  const topLevelSvgCount = await preview.locator('body').evaluate(
    body =>
      Array.from(body.querySelectorAll('svg')).filter(
        svg => !svg.parentElement?.closest('svg')
      ).length
  );
  expect(topLevelSvgCount).toBe(3);
  expect(html).not.toContain('data-latex');
  expect(html).not.toContain('$$');

  // 公众号的硬限制：不能有 <use>/xlink（path 上不允许 id），不能有自定义标签，
  // 更不能留 data-mml-node="TeXAtom"——公众号会把它及之外的所有组一起删掉。
  expect(html).not.toContain('<use');
  expect(html).not.toContain('xlink');
  expect(html).not.toContain('mjx-container');
  expect(html).not.toContain('TeXAtom');
  expect(html).not.toContain('data-mml-node');
  expect(html).not.toMatch(/<path[^>]*\sid=/);

  // 尺寸必须是 px：公众号里字体不受控，ex 会随字体飘
  expect(html).toMatch(/width="[\d.]+px"/);
  expect(html).not.toMatch(/width="[\d.]+ex"/);

  // 预览 iframe 故意不给 allow-scripts，浏览器每拦一次脚本就报一条——这是安全
  // 设置生效的表现，不是缺陷。剩下的错误一条都不该有：当初 MathJax 在浏览器里
  // 抛 require is not defined 时，正是被 catch 吞掉、既不报错也不渲染。
  const unexpectedErrors = consoleErrors.filter(
    message => !message.includes('frame is sandboxed')
  );
  expect(unexpectedErrors).toEqual([]);
});
