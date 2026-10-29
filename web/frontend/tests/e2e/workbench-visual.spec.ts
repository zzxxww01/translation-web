import { expect, test, type Page } from '@playwright/test';

const status = { active: false, run_id: null, status: null, current_step: null, translated: 2, total: 2, error: null };
const rows = [
  { key: 'section:s1', kind: 'section', section_id: 's1', paragraph_id: null, source: 'The base die moves to logic',
    web: '基底裸片改用逻辑工艺', alt: { 'v--codex': '基底裸片转向逻辑工艺' } },
  { key: 's1/p0', kind: 'p', section_id: 's1', paragraph_id: 'p0',
    source: 'HBM4 moves the base die from a DRAM process to a logic process, and that single change reshapes the cost stack in three ways.',
    web: 'HBM4 把基底裸片从 DRAM 工艺换成逻辑工艺，这一处改动从三个方面重塑了成本结构。',
    alt: { 'v--codex': 'HBM4 将基底裸片由 DRAM 制程改为逻辑制程，仅此一项变化便从三方面重塑成本结构。' } },
];
const codex = { id: 'v--codex', kind: 'claude', label: 'Codex', title_translation: null, progress: { total: 2, approved: 0 }, status,
  import: { run_id: 'r0', agent: 'codex', model: 'gpt-5.5', aligned: 2, unaligned: 0, merged_blocks: 0, imported_at: '2026-10-28T10:00:00' } };
const project = { id: 'v', title: 'HBM4 Cost Structure', title_translation: 'HBM4 的成本结构', original_url: null, created_at: '',
  progress: { total: 2, approved: 0 }, status, primary_target: null };
const run = { title: 't', skill: 'four-step-translate', created_at: 0, updated_at: 0, session_id: 's', error: null };

const CASES = {
  'web-primary-codex-waiting': { project: { ...project, claude_run_id: 'r1', primary: 'v' }, variants: [codex],
    run: { ...run, id: 'r1', status: 'idle', awaiting_reply: true, auto_reply_at: 1_793_250_000, harness: 'codex' } },
  'codex-primary-retranslating': { project: { ...project, claude_run_id: 'r2', primary: 'v--codex' }, variants: [codex],
    run: { ...run, id: 'r2', status: 'running', model: 'gpt-5.5-codex', harness: 'codex' } },
  'web-only': { project: { ...project, claude_run_id: null, primary: 'v' }, variants: [], run: null },
  // Gemini 跑完了，但它的英文稿和下载的原文对不上：对照栏状态行写「没导入：…」和「仍然导入」
  'gemini-alignment-low': { project: { ...project, claude_run_id: 'r3', primary: 'v' }, variants: [codex],
    run: { ...run, id: 'r3', status: 'idle', model: 'gemini-3.8-pro', harness: 'antigravity' } },
} as const;

async function open(page: Page, name: keyof typeof CASES, readingMark: { key: string; at: string } | null = null) {
  const item = CASES[name];
  await page.route('**/api/substack/**', route => route.fulfill({ json: { articles: [], total: 0, added: 0, next_offset: null } }));
  await page.route('**/api/projects/v/workbench', route => route.fulfill({ json: {
    project: item.project, variants: item.variants, rows, reading_mark: readingMark } }));
  await page.route('**/api/projects/v/workbench/changes**', route => route.fulfill({ json: { total: 2, changed: 1, changes: [] } }));
  await page.route('**/api/skills/runs/*', route => route.fulfill({ json: item.run }));
  await page.route('**/api/skills/runs/*/files', route => route.fulfill({ json: [
    { path: 'output/zh.md', size: 10, mtime: 2 }, { path: 'output/en.md', size: 10, mtime: 1 },
  ] }));
  await page.route('**/api/skills/runs/*/files/**', route => route.fulfill({ body: '# t\n\ntext\n' }));
  await page.route('**/api/projects/v/variants/claude', route => route.fulfill({
    status: 409, json: { detail: 'Agent 的英文稿只对上 40/57 段，可能不是这篇下载的原文', error_code: 'ALIGNMENT_LOW' } }));
  await page.route('**/api/skills/models/*', route => route.fulfill({ json: {
    models: [{ id: 'gpt-5.5-codex', label: 'gpt-5.5-codex' }, { id: 'gpt-5.4-mini', label: 'gpt-5.4-mini' }],
    default_model: 'gpt-5.5', source: 'cache', warning: null } }));
  await page.goto('/articles/v');
  await expect(page.getByRole('article', { name: '主译本正文' })).toBeVisible();
  await page.evaluate(() => document.fonts.ready);
}

async function shoot(page: Page, file: string) {
  // 动画直接跳到结束，截到的是静止的样子
  await page.screenshot({ path: `test-results/${file}.png`, fullPage: false, animations: 'disabled' });
}

for (const [width, height] of [[1440, 900], [390, 844]] as const) {
  for (const name of Object.keys(CASES) as (keyof typeof CASES)[]) {
    test(`workbench ${name} at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height });
      await open(page, name);
      if (name === 'gemini-alignment-low') {
        if (width < 768) await page.getByRole('tab', { name: '对照', exact: true }).click();
        await expect(page.getByRole('button', { name: '仍然导入', exact: true })).toBeVisible();
      }
      expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
      await expect(page.getByText('在等你确认', { exact: false })).toHaveCount(0); // 旧横幅文案不该再出现
      if (width >= 768) {
        // 三栏栏头一样高（对齐另有一条用例）
        const heights = await page.locator('[data-pane]').evaluateAll(cells => cells.map(cell => Math.round(cell.getBoundingClientRect().height)));
        expect(new Set(heights).size).toBe(1);
      } else {
        await expect(page.getByRole('tablist', { name: '切换栏' })).toBeVisible();
      }
      await shoot(page, `workbench-${name}-${width}`);
    });
  }
}

test('workbench popovers at 1440px', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page, 'web-primary-codex-waiting');
  await page.getByRole('button', { name: '用 Agent 再翻一版' }).click();
  const add = page.getByRole('dialog');
  await expect(add.getByRole('radiogroup', { name: 'Agent' })).toBeVisible();
  await expect(add.getByRole('radiogroup', { name: '模型' })).toBeVisible();
  await shoot(page, 'workbench-popover-add-agent-1440');
  await page.keyboard.press('Escape');
  await expect(add).toHaveCount(0);

  await page.getByRole('button', { name: '重新翻译' }).click();
  const retranslate = page.getByRole('dialog');
  await expect(retranslate.getByRole('radiogroup', { name: '模型' })).toBeVisible();
  await expect(retranslate.getByText('翻完会整篇替换现在的 Codex 版')).toBeVisible();
  await shoot(page, 'workbench-popover-retranslate-1440');
});

test('compare tabs move with the arrow keys and show the focus ring; ＋ is not a tab', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page, 'gemini-alignment-low');
  const tabs = page.getByRole('tablist', { name: '对照版本' });
  await expect(tabs.getByRole('tab')).toHaveCount(2);
  await expect(tabs.getByRole('button', { name: '用 Agent 再翻一版' })).toHaveCount(0);
  await tabs.getByRole('tab', { name: 'Gemini' }).focus();
  await page.keyboard.press('ArrowLeft');
  await expect(tabs.getByRole('tab', { name: 'Codex' })).toBeFocused();
  await expect(tabs.getByRole('tab', { name: 'Codex' })).toHaveAttribute('aria-selected', 'true');
  await shoot(page, 'workbench-focus-tabs-1440');
  // 用键盘走到「更多导出方式」，看焦点描边没有被圆角胶囊裁掉
  await page.getByRole('button', { name: '更多导出方式' }).focus();
  await page.keyboard.press('Shift+Tab');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: '更多导出方式' })).toBeFocused();
  await page.screenshot({ path: 'test-results/workbench-focus-export-1440.png', clip: { x: 1100, y: 70, width: 340, height: 64 }, animations: 'disabled' });
});

test('compare tabs fold into a dropdown when the column is narrower than 420px', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page, 'web-primary-codex-waiting');
  await expect(page.getByRole('tablist', { name: '对照版本' })).toBeVisible();
  await page.setViewportSize({ width: 1180, height: 900 });
  await expect(page.getByRole('tablist', { name: '对照版本' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /^对照版本：/ })).toBeVisible();
  await shoot(page, 'workbench-narrow-compare-1180');
});

test('a collapsed column keeps header and text on one left edge; hover tint and reading mark', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page, 'codex-primary-retranslating', { key: 's1/p0', at: '2026-10-28T10:00:00Z' });
  await page.getByRole('button', { name: '收起英文', exact: true }).click();
  for (const pane of ['main', 'compare']) {
    const [header, text] = await Promise.all([
      page.locator(`[data-pane="${pane}"] > div > div`).first().boundingBox(),
      page.locator(`[data-pane-body="${pane}"] > [data-reading-block]`).first().boundingBox(),
    ]);
    expect(Math.abs(header!.x - text!.x)).toBeLessThan(1);
    expect(Math.abs(header!.width - text!.width)).toBeLessThan(1);
  }
  await expect(page.getByRole('button', { name: '阅读标记', exact: true })).toBeVisible();
  await page.locator('[data-pane-body="compare"] > [data-reading-block]').nth(1).hover();
  await shoot(page, 'workbench-collapsed-source-1440');
});
