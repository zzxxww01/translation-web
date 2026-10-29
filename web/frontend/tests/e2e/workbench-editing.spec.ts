import { expect, test, type Page } from '@playwright/test';

// 真浏览器里才看得出来的编辑手感：点哪改哪、不乱跳、复制粘贴、撤销、沉浸模式
const status = { active: false, run_id: null, status: null, current_step: null, translated: 30, total: 30, error: null };
const zh = (n: number) => `第 ${n} 段：HBM4 把基底裸片从 DRAM 工艺换成逻辑工艺，这一处改动从三个方面重塑了成本结构。`.repeat(n === 9 ? 12 : 3);
const LINK = '见[行业模型](https://example.com/a/rather/long/link/that/takes/up/space)。';
const rows = Array.from({ length: 30 }, (_, n) => ({
  key: `s1/p${n}`, kind: 'p', section_id: 's1', paragraph_id: `p${n}`,
  source: `Paragraph ${n}: HBM4 moves the base die from a DRAM process to a logic process, and that single change reshapes the cost stack.`,
  web: n === 4 || n === 8 ? `${LINK}${zh(n)}` : zh(n),
  alt: { 'v--codex': `码·${zh(n)}` },
}));
const codex = { id: 'v--codex', kind: 'claude', label: 'Codex', title_translation: null, progress: { total: 30, approved: 0 }, status,
  import: { run_id: 'r0', agent: 'codex', model: 'gpt-5.5', aligned: 30, unaligned: 0, merged_blocks: 0, imported_at: '2026-10-28T10:00:00' } };
const project = { id: 'v', title: 'HBM4 Cost Structure', title_translation: 'HBM4 的成本结构', original_url: null, created_at: '',
  progress: { total: 30, approved: 0 }, status, primary_target: null, claude_run_id: null, primary: 'v' };

async function open(page: Page) {
  const saved: { paragraph_id: string; text: string }[] = [];
  const current = rows.map(row => ({ ...row }));
  await page.route('**/api/substack/**', route => route.fulfill({ json: { articles: [], total: 0, added: 0, next_offset: null } }));
  await page.route('**/api/projects/v/workbench', route => route.fulfill({ json: { project, variants: [codex], rows: current, reading_mark: null } }));
  await page.route('**/api/projects/v/workbench/text', async route => {
    const body = route.request().postDataJSON();
    saved.push(body);
    current.find(row => row.paragraph_id === body.paragraph_id)!.web = body.text;
    await route.fulfill({ json: { ok: true } });
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/articles/v');
  await expect(page.getByRole('article', { name: '主译本正文' })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
  return saved;
}

const main = (page: Page) => page.getByRole('article', { name: '主译本正文' });
const cell = (page: Page, n: number) => main(page).getByRole('button', { name: `编辑：主译本：Paragraph ${n}:`, exact: false }).first();
const editor = (page: Page) => main(page).locator('textarea');
const scrollTop = (page: Page) => main(page).evaluate(element => element.scrollTop);
const selected = (page: Page) => editor(page).evaluate(element => {
  const textarea = element as HTMLTextAreaElement;
  return textarea.value.slice(textarea.selectionStart, textarea.selectionEnd);
});

/** 浏览器认为屏幕上这一点落在段落里第几个字 */
const charAt = (page: Page, x: number, y: number) => page.evaluate(([px, py]) => {
  const range = document.caretRangeFromPoint(px, py)!;
  const owner = range.startContainer.parentElement!.closest('[role="button"]')!;
  const before = document.createRange();
  before.setStart(owner, 0);
  before.setEnd(range.startContainer, range.startOffset);
  return before.toString().length;
}, [x, y]);

test('one click edits right where it lands, and nothing on screen moves', async ({ page }) => {
  await open(page);
  // 很长的一段，段尾在屏幕下面：点它的第一行
  await cell(page, 9).evaluate(element => element.scrollIntoView({ block: 'start' }));
  await main(page).evaluate(element => { element.scrollTop -= 120; });
  const box = (await cell(page, 9).boundingBox())!;
  const [x, y] = [box.x + 140, box.y + 16];
  const expected = await charAt(page, x, y);
  const before = await scrollTop(page);
  await page.mouse.click(x, y);
  await expect(editor(page)).toBeFocused();
  expect(await editor(page).evaluate(element => (element as HTMLTextAreaElement).selectionStart)).toBe(expected);
  const after = (await editor(page).boundingBox())!;
  expect(Math.abs(after.y - box.y)).toBeLessThan(1);
  expect(Math.abs(after.height - box.height)).toBeLessThan(1);
  await page.keyboard.type('★');
  expect(await editor(page).inputValue()).toBe(`${zh(9).slice(0, expected)}★${zh(9).slice(expected)}`);
  expect(await scrollTop(page)).toBe(before);
});

test('pasting goes where you clicked and the page stays put', async ({ page, context }) => {
  await context.grantPermissions(['clipboard-read', 'clipboard-write']);
  await open(page);
  await cell(page, 13).evaluate(element => element.scrollIntoView({ block: 'center' }));
  const box = (await cell(page, 13).boundingBox())!;
  const [x, y] = [box.x + 120, box.y + 16];
  const expected = await charAt(page, x, y);
  await page.mouse.click(x, y);
  const pasted = '粘贴进来的一大段文字。'.repeat(20);
  await page.evaluate(text => navigator.clipboard.writeText(text), pasted);
  const before = await scrollTop(page);
  const top = (await editor(page).boundingBox())!.y;
  await page.keyboard.press('Control+V');
  await expect(editor(page)).toHaveValue(`${zh(13).slice(0, expected)}${pasted}${zh(13).slice(expected)}`);
  expect(await scrollTop(page)).toBe(before);
  expect(Math.abs((await editor(page).boundingBox())!.y - top)).toBeLessThan(1);
});

test('selecting to copy keeps the selection: inside a paragraph, across paragraphs, and inside a linked one', async ({ page }) => {
  await open(page);
  // 一段之内：选中的字还是选中的（换成编辑框，可以直接复制或改掉）
  await cell(page, 5).evaluate(element => element.scrollIntoView({ block: 'center' }));
  let box = (await cell(page, 5).boundingBox())!;
  await page.mouse.move(box.x + 30, box.y + 16);
  await page.mouse.down();
  await page.mouse.move(box.x + 300, box.y + 16, { steps: 8 });
  await page.mouse.up();
  expect((await selected(page)).length).toBeGreaterThan(10);
  await page.keyboard.press('Control+C');
  expect(await page.evaluate(() => navigator.clipboard.readText().catch(() => null)) ?? await selected(page)).toBeTruthy();
  await page.keyboard.press('Escape');

  // 跨段：留在排版视图里
  await main(page).evaluate(element => { element.scrollTop = 0; });
  const first = (await cell(page, 1).boundingBox())!;
  const second = (await cell(page, 2).boundingBox())!;
  await page.mouse.move(first.x + 30, first.y + 16);
  await page.mouse.down();
  await page.mouse.move(second.x + 200, second.y + 16, { steps: 8 });
  await page.mouse.up();
  await expect(editor(page)).toHaveCount(0);
  expect(await page.evaluate(() => window.getSelection()?.toString() ?? '')).toContain('第 2 段');

  // 带链接的一段：复制的是排好版的字
  await cell(page, 4).evaluate(element => element.scrollIntoView({ block: 'center' }));
  box = (await cell(page, 4).boundingBox())!;
  await page.mouse.move(box.x + 10, box.y + 16);
  await page.mouse.down();
  await page.mouse.move(box.x + 300, box.y + 16, { steps: 8 });
  await page.mouse.up();
  await expect(editor(page)).toHaveCount(0);
  expect(await page.evaluate(() => window.getSelection()?.toString() ?? '')).toContain('行业模型');
});

test('clicking the next paragraph while editing a linked one opens the paragraph you clicked', async ({ page }) => {
  await open(page);
  await cell(page, 8).evaluate(element => element.scrollIntoView({ block: 'start' }));
  const linked = (await cell(page, 8).boundingBox())!;
  await page.mouse.click(linked.x + linked.width - 40, linked.y + 16); // 别点在链接上
  await expect(editor(page)).toHaveAttribute('aria-label', /Paragraph 8:/);
  // 下一段的第一行：上一段换回排版视图会变矮，这一段会跟着往上挪
  const next = (await cell(page, 9).boundingBox())!;
  await page.mouse.click(next.x + 120, next.y + 16);
  await expect(editor(page)).toHaveCount(1);
  await expect(editor(page)).toHaveAttribute('aria-label', /Paragraph 9:/);
  await expect(editor(page)).toBeFocused();
});

test('the hidden paragraph tools cannot be clicked by accident; Ctrl+Z works after clicking away', async ({ page }) => {
  const saved = await open(page);
  // 鼠标不在段落上时，两段之间那条缝里点到的不是看不见的「采用整段」
  const adopt = main(page).getByRole('button', { name: '采用 Codex 整段' }).nth(14);
  await adopt.evaluate(element => element.closest('[data-reading-block]')!.scrollIntoView({ block: 'center' }));
  await page.mouse.move(5, 5);
  const spot = (await adopt.boundingBox())!;
  const [x, y] = [spot.x + spot.width / 2, spot.y + spot.height / 2];
  const hit = await page.evaluate(([px, py]) => document.elementFromPoint(px, py)?.closest('button')?.textContent ?? '', [x, y]);
  expect(hit).toBe('');
  await page.mouse.click(x, y);
  await page.waitForTimeout(300);
  expect(saved).toHaveLength(0);

  // 改错一段，点到别处，再按 Ctrl+Z 撤回
  await cell(page, 2).scrollIntoViewIfNeeded();
  await cell(page, 2).click();
  await page.keyboard.press('Control+A');
  await page.keyboard.type('改错了');
  await page.getByRole('article', { name: '英文正文' }).click({ position: { x: 20, y: 20 } });
  await expect.poll(() => saved.at(-1)?.text).toBe('改错了');
  await page.keyboard.press('Control+Z');
  await expect(editor(page)).toHaveValue(zh(2));
  await page.keyboard.press('Escape');
  await expect.poll(() => saved.at(-1)?.text).toBe(zh(2));
  // 整段采用也能撤回
  await cell(page, 5).hover();
  await main(page).getByRole('button', { name: '采用 Codex 整段' }).nth(5).click();
  await expect.poll(() => saved.at(-1)?.text).toBe(`码·${zh(5)}`);
  await page.keyboard.press('Control+Z');
  await page.keyboard.press('Escape');
  await expect.poll(() => saved.at(-1)?.text).toBe(zh(5));
});

test('immersive mode fills the screen with the three panes', async ({ page }) => {
  await open(page);
  await page.getByRole('button', { name: '沉浸模式', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'HBM4 的成本结构' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'momo 翻译工作台首页' })).toHaveCount(0);
  const grid = (await page.getByTestId('pane-grid').boundingBox())!;
  const viewport = page.viewportSize()!;
  expect(grid.y).toBe(0);
  expect(grid.x).toBe(0);
  expect(Math.round(grid.width)).toBe(viewport.width);
  expect(Math.round(grid.height)).toBe(viewport.height);
  await page.screenshot({ path: 'test-results/workbench-immersive.png', animations: 'disabled' });
  // 刷新后还在沉浸模式；不请求浏览器全屏
  expect(await page.evaluate(() => document.fullscreenElement)).toBeNull();
  await page.reload();
  await expect(page.getByRole('button', { name: '退出沉浸模式' })).toBeVisible();
  await page.getByRole('button', { name: '退出沉浸模式' }).click();
  await expect(page.getByRole('heading', { name: 'HBM4 的成本结构' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'momo 翻译工作台首页' })).toBeVisible();
});
