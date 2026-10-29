import { expect, test, type Page } from '@playwright/test';

// 导出主译本的几种去处：Markdown、PDF（浏览器打印）、复制全文、复制成公众号格式、在微信排版中打开
const status = { active: false, run_id: null, status: null, current_step: null, translated: 2, total: 2, error: null };
const EXPORTED = '# 华为与 DeepSeek 的共生关系\n\n就在中国国庆假期之前，DeepSeek 发布了昇腾支持。\n\n![](https://cdn.example.com/chip.png)\n';
const rows = [
  { key: 's1/p0', kind: 'p', section_id: 's1', paragraph_id: 'p0', source: 'Right before the holidays.', web: '就在假期之前。', alt: {} },
];
const project = { id: 'v', title: 'The Huawei-DeepSeek Symbiosis', title_translation: '华为与 DeepSeek 的共生关系', original_url: null,
  created_at: '', progress: { total: 1, approved: 0 }, status, primary_target: null, claude_run_id: null, primary: 'v' };

async function open(page: Page) {
  const exports: string[] = [];
  await page.route('**/api/substack/**', route => route.fulfill({ json: { articles: [], total: 0, added: 0, next_offset: null } }));
  await page.route('**/api/projects/v/workbench', route => route.fulfill({ json: { project, variants: [], rows, reading_mark: null } }));
  await page.route('**/api/projects/v/export**', async route => {
    exports.push(route.request().url());
    await route.fulfill({ json: { filename: '华为与 DeepSeek 的共生关系.md', content: EXPORTED } });
  });
  await page.route('**/api/wechat/themes', route => route.fulfill({ json: { themes: [{ id: 'default', name: '默认', description: '' }] } }));
  await page.route('**/api/wechat/format', route => route.fulfill({ json: {
    html: '<section class="wx"><h1>华为与 DeepSeek 的共生关系</h1><p>就在中国国庆假期之前。</p></section>',
    css: '.wx p { color: #3f3f3f; line-height: 1.8; }', image_count: 1, image_urls: [] } }));
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/articles/v');
  await expect(page.getByRole('article', { name: '主译本正文' })).toBeVisible();
  return exports;
}

const menuItem = async (page: Page, name: string) => {
  await page.getByRole('button', { name: '更多导出方式' }).click();
  await page.getByRole('menuitem', { name }).click();
};

test('copy the whole translation, or as WeChat-ready rich text', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await open(page);
  await menuItem(page, '复制全文');
  await expect(page.getByRole('button', { name: '已复制全文' })).toBeVisible();
  // Windows 的系统剪贴板会把换行存成 \r\n
  expect((await page.evaluate(() => navigator.clipboard.readText())).replace(/\r\n/g, '\n')).toBe(EXPORTED);

  await menuItem(page, '复制为公众号格式');
  await expect(page.getByRole('button', { name: '已复制，可粘到公众号' })).toBeVisible();
  const html = await page.evaluate(async () => {
    const [item] = await navigator.clipboard.read();
    return (await item.getType('text/html')).text();
  });
  expect(html).toContain('就在中国国庆假期之前');
  expect(html).toMatch(/style="[^"]*color: #3f3f3f/); // 样式内联，公众号编辑器认得
  // 两秒半后按钮恢复原样
  await expect(page.getByRole('button', { name: '导出主译本' })).toBeVisible({ timeout: 5_000 });
});

test('export a PDF through the print dialog, titled after the article', async ({ page }) => {
  await open(page);
  // 浏览器的打印框没法在测试里点：截住打印用的 iframe，记下它要打印的内容和当时的页面标题
  await page.evaluate(() => {
    const w = window as unknown as { printed?: { html: string; title: string } };
    new MutationObserver(records => {
      for (const record of records) {
        record.addedNodes.forEach(node => {
          if (!(node instanceof HTMLIFrameElement) || !node.contentWindow) return;
          node.contentWindow.print = () => {
            w.printed = { html: node.contentDocument!.documentElement.outerHTML, title: document.title };
          };
        });
      }
    }).observe(document.body, { childList: true });
  });
  const before = await page.title();
  await menuItem(page, '导出 PDF');
  await expect.poll(() => page.evaluate(() => (window as unknown as { printed?: unknown }).printed ?? null)).not.toBeNull();
  const printed = await page.evaluate(() => (window as unknown as { printed: { html: string; title: string } }).printed);
  expect(printed.title).toBe('华为与 DeepSeek 的共生关系');
  expect(printed.html).toContain('<h1>华为与 DeepSeek 的共生关系</h1>');
  expect(printed.html).toContain('<img src="https://cdn.example.com/chip.png"');
  expect(printed.html).toContain('@page');
  expect(printed.html).toContain('Noto Serif SC');
  // 没有 afterprint（打印被截住了）也不能让页面标题一直是文章名：取消后由 afterprint / 超时还原，这里手动触发一下
  await page.evaluate(() => document.querySelectorAll('iframe').forEach(frame => frame.contentWindow?.dispatchEvent(new Event('afterprint'))));
  await expect.poll(() => page.title()).toBe(before);
});

test('open the translation in the WeChat formatter to pick a theme first', async ({ page }) => {
  await open(page);
  await menuItem(page, '在微信排版中打开');
  await expect(page).toHaveURL(/\/wechat$/);
  await expect(page.getByRole('textbox').first()).toHaveValue(EXPORTED);
});
