import { expect, test, type Page } from '@playwright/test';

// 「继续阅读」（顶栏的「读到 N%」）必须真的把三栏都带到标记那一段：同时滚三栏、标记上方的图片晚加载也不能漂走
const status = { active: false, run_id: null, status: null, current_step: null, translated: 40, total: 40, error: null };
const zh = (n: number) => `第 ${n} 段：HBM4 把基底裸片从 DRAM 工艺换成逻辑工艺，这一处改动从三个方面重塑了成本结构。`.repeat(2 + (n % 3));
const rows = Array.from({ length: 40 }, (_, n) => n % 6 === 5
  ? { key: `s1/p${n}`, kind: 'image', section_id: 's1', paragraph_id: `p${n}`, source: `https://img.example.com/${n}.svg`,
      image: `https://img.example.com/${n}.svg`, web: null, alt: { 'v--codex': null } }
  : { key: `s1/p${n}`, kind: 'p', section_id: 's1', paragraph_id: `p${n}`,
      source: `Paragraph ${n}: HBM4 moves the base die from a DRAM process to a logic process, and that single change reshapes the cost stack.`,
      web: zh(n), alt: { 'v--codex': `码·${zh(n)}` } });
const codex = { id: 'v--codex', kind: 'claude', label: 'Codex', title_translation: null, progress: { total: 40, approved: 0 }, status,
  import: { run_id: 'r0', agent: 'codex', model: 'gpt-5.5', aligned: 40, unaligned: 0, merged_blocks: 0, imported_at: '2026-10-28T10:00:00' } };
const project = { id: 'v', title: 'HBM4 Cost Structure', title_translation: 'HBM4 的成本结构', original_url: null, created_at: '',
  progress: { total: 40, approved: 0 }, status, primary_target: null, claude_run_id: null, primary: 'v' };
// 没写宽高的图：加载出来之前高度是 0，加载后 300px 高，会把下面的段落往下推
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300"><rect width="600" height="300" fill="#ebc5d6"/></svg>';

async function open(page: Page, imageDelay: number) {
  await page.route('**/api/substack/**', route => route.fulfill({ json: { articles: [], total: 0, added: 0, next_offset: null } }));
  await page.route('**/api/projects/v/workbench', route => route.fulfill({ json: {
    project, variants: [codex], rows, reading_mark: { key: 's1/p26', at: '2026-10-29T13:40:00Z' } } }));
  await page.route('https://img.example.com/**', async route => {
    await new Promise(resolve => setTimeout(resolve, imageDelay));
    await route.fulfill({ contentType: 'image/svg+xml', body: SVG });
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/articles/v');
  await expect(page.getByRole('article', { name: '主译本正文' })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

/** 每一栏里标记那一段离这一栏可视区顶边多远（px） */
const offsets = (page: Page) => page.evaluate(() => Array.from(document.querySelectorAll<HTMLElement>('[data-pane-body]')).map(pane => {
  const block = pane.querySelector<HTMLElement>('[data-reading-mark="true"]')!;
  return Math.round(block.getBoundingClientRect().top - pane.getBoundingClientRect().top);
}));

for (const delay of [0, 1200]) {
  test(`继续阅读 lands every pane on the mark (images load after ${delay} ms)`, async ({ page }) => {
    await open(page, delay);
    await page.getByRole('button', { name: /^读到 \d+%/ }).click();
    // 平滑滚动结束、晚到的图片也加载完以后
    await page.waitForTimeout(delay + 1500);
    const settled = await offsets(page);
    for (const offset of settled) {
      expect(offset).toBeGreaterThanOrEqual(8);
      expect(offset).toBeLessThanOrEqual(48);
    }
    // 三栏都在可视区里看得到标记那一段
    expect(settled).toHaveLength(3);
  });
}

test('继续阅读 stops correcting once you scroll yourself', async ({ page }) => {
  await open(page, 1500);
  await page.getByRole('button', { name: /^读到 \d+%/ }).click();
  await page.waitForTimeout(800);
  const main = page.getByRole('article', { name: '主译本正文' });
  await main.hover();
  await page.mouse.wheel(0, 600);
  await page.waitForTimeout(400);
  const mine = await main.evaluate(element => element.scrollTop);
  await page.waitForTimeout(2000); // 图片这时才加载完
  expect(Math.abs((await main.evaluate(element => element.scrollTop)) - mine)).toBeLessThan(320);
});
