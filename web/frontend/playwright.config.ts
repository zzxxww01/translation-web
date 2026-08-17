import { defineConfig } from '@playwright/test';


export default defineConfig({
  testDir: './tests/e2e',
  outputDir: '/tmp/translation-agent-playwright',
  // 公式那条 spec 要等 MathJax 懒加载（约 2.2MB），30s 不够
  timeout: 90_000,
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:54321',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    // 没装 playwright 自带浏览器时，可用系统装的 Chrome/Edge：
    // PLAYWRIGHT_CHANNEL=msedge npx playwright test
    ...(process.env.PLAYWRIGHT_CHANNEL
      ? { channel: process.env.PLAYWRIGHT_CHANNEL }
      : {}),
  },
});
