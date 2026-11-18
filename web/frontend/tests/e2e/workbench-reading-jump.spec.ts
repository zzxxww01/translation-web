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
    // 平滑滚动结束、晚到的图片也加载完以后：轮询到落位为止（CI 机器慢，固定等待会偶发失败）
    await expect.poll(async () => {
      const settled = await offsets(page);
      // 三栏都在可视区里看得到标记那一段
      return settled.length === 3 && settled.every(offset => offset >= 8 && offset <= 48);
    }, { timeout: delay + 5000, intervals: [250] }).toBe(true);
  });
}

/** 等这一栏不再滚动（平滑滚动、滚轮动画都结束），返回停下来的 scrollTop */
async function settle(page: Page, name: string) {
  const pane = page.getByRole('article', { name });
  let last = -1;
  await expect.poll(async () => {
    const now = await pane.evaluate(element => element.scrollTop);
    const still = now === last;
    last = now;
    return still;
  }, { timeout: 5000, intervals: [250] }).toBe(true);
  return last;
}

/** 主译本栏里标记那一段离栏顶多远（看位置而不是 scrollTop：浏览器的滚动锚定会在图片加载时改 scrollTop 但不挪内容） */
const mainOffset = (page: Page) => page.evaluate(() => {
  const pane = document.querySelector<HTMLElement>('[data-pane-body="main"]')!;
  const block = pane.querySelector<HTMLElement>('[data-reading-mark="true"]')!;
  return Math.round(block.getBoundingClientRect().top - pane.getBoundingClientRect().top);
});

test('继续阅读 stops correcting once you scroll yourself', async ({ page }) => {
  await open(page, 3000); // 图片在你自己滚完之后才加载完
  await page.getByRole('button', { name: /^读到 \d+%/ }).click();
  await settle(page, '主译本正文');
  const main = page.getByRole('article', { name: '主译本正文' });
  await main.hover();
  await page.mouse.wheel(0, 600);
  await settle(page, '主译本正文');
  const mine = await mainOffset(page);
  expect(mine).toBeLessThan(-200); // 确实滚走了，标记在可视区上方
  await page.waitForTimeout(3500); // 图片这时才加载完
  // 没有被拉回标记处（拉回的话会回到 24px 左右，差 600 多）
  expect(Math.abs((await mainOffset(page)) - mine)).toBeLessThan(320);
});
