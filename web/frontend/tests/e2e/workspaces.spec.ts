import { expect, test } from '@playwright/test';


test('post workspace keeps actions inside a mobile viewport', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/post');

  const source = page.getByLabel('帖子原文');
  await expect(source).toBeVisible();
  await source.fill('A source post that is long enough to exercise the editor layout.');
  await expect(page.getByRole('button', { name: '翻译帖子' })).toBeEnabled();

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth
  );
  expect(hasHorizontalOverflow).toBe(false);
  await page.screenshot({
    path: '/tmp/translation-agent-post-mobile.png',
    fullPage: true,
  });
});


test('document workspace exposes its mobile navigation sheet', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/document');

  const navigationButton = page.getByRole('button', {
    name: '打开文档导航',
  });
  await expect(navigationButton).toBeVisible();
  await navigationButton.click();
  await expect(
    page.getByRole('complementary', { name: '文档项目与章节导航' })
  ).toBeVisible();

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth
  );
  expect(hasHorizontalOverflow).toBe(false);
  await page.screenshot({
    path: '/tmp/translation-agent-document-mobile.png',
    fullPage: true,
  });
});


test('background translation tray survives an in-app route change', async ({ page }) => {
  const project = {
    id: 'demo',
    title: 'Demo project',
    status: 'created',
    progress: {
      total: 4,
      total_sections: 1,
      total_paragraphs: 4,
      approved: 0,
      percent: 0,
    },
    created_at: '2026-08-09T00:00:00',
    sections: [],
  };

  await page.route('**/api/projects/demo/translation-status', route =>
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'processing',
        translated_paragraphs: 1,
        total_paragraphs: 4,
        active_project_id: 'demo',
        active_run_id: 'run-1',
        current_step: '章节术语预扫描',
      }),
    })
  );
  await page.route('**/api/projects/demo', route =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify(project) })
  );
  await page.route('**/api/projects', route =>
    route.fulfill({ contentType: 'application/json', body: JSON.stringify([project]) })
  );

  await page.goto('/document/demo');
  const taskTray = page.getByRole('region', { name: '后台任务' });
  await expect(taskTray).toContainText('正在翻译：Demo project');

  await page.getByRole('link', { name: '帖子翻译' }).click();
  await expect(page).toHaveURL(/\/post$/);
  await expect(taskTray).toContainText('正在翻译：Demo project');
});
