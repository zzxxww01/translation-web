import { expect, test } from '@playwright/test';

test('mobile article reading preserves a bookmark across refresh and saves a fragment', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  const status = { active: false, run_id: null, status: null, current_step: null, translated: 2, total: 2, error: null };
  let mark: { key: string; at: string } | null = null;
  const rows = [
    { key: 's/p1', kind: 'p', section_id: 's', paragraph_id: 'p1', block: 'b1', source: 'First sentence.', web: '第一句。', alt: {} },
    { key: 's/p2', kind: 'p', section_id: 's', paragraph_id: 'p2', block: 'b1', source: 'Second sentence.', web: '第二句。', alt: {} },
  ];
  await page.route('**/api/substack/**', route => route.fulfill({ json: { articles: [], total: 0, added: 0, next_offset: null } }));
  await page.route('**/api/projects/reading/workbench', route => route.fulfill({ json: {
    project: { id: 'reading', title: 'Continuous reading', title_translation: '连续阅读', original_url: null,
      created_at: '', claude_run_id: null, progress: { total: 2, approved: 0 }, status, primary: 'reading', primary_target: null },
    variants: [], rows, reading_mark: mark,
  } }));
  await page.route('**/api/projects/reading/workbench/reading-mark', async route => {
    const key = route.request().postDataJSON().key;
    mark = key ? { key, at: '2026-10-27T00:00:00Z' } : null;
    await route.fulfill({ json: { ok: true, reading_mark: mark } });
  });
  await page.route('**/api/projects/reading/workbench/text', async route => {
    const body = route.request().postDataJSON();
    rows.find(row => row.paragraph_id === body.paragraph_id)!.web = body.text;
    await route.fulfill({ json: { ok: true } });
  });
  await page.goto('/articles/reading');
  await expect(page.getByRole('article', { name: '主译本正文' })).toContainText('第一句。第二句。');
  // 段落工具条要先把鼠标移到段落上才出现、才点得到
  await page.getByRole('button', { name: '编辑：主译本：First sentence.', exact: true }).hover();
  await page.getByRole('button', { name: '主译本：标记读到这里 — First sentence.', exact: true }).click();
  await expect(page.getByRole('button', { name: /^读到 \d+%/ })).toBeVisible();
  await page.reload();
  await expect(page.locator('[data-reading-mark="true"]')).toHaveCount(1);
  await page.getByRole('button', { name: /^读到 \d+%/ }).click();
  await page.getByRole('button', { name: '编辑：主译本：Second sentence.', exact: true }).click();
  await page.getByRole('textbox', { name: '主译本：Second sentence.', exact: true }).fill('第二句改好了。');
  await page.getByRole('button', { name: '保存', exact: true }).click();
  await expect.poll(() => rows[1].web).toBe('第二句改好了。');
  await page.getByRole('tab', { name: '英文', exact: true }).click();
  await expect(page.getByRole('article', { name: '英文正文' })).toContainText('First sentence. Second sentence.');
  await expect(page.locator('[data-reading-mark="true"]')).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
  await page.getByRole('button', { name: '英文：取消标记 — First sentence.', exact: true }).click();
  await expect(page.locator('[data-reading-mark="true"]')).toHaveCount(0);
});
