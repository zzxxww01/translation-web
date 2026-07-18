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
