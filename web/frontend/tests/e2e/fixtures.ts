import { test as base } from '@playwright/test';

export { expect, type Page } from '@playwright/test';

// 全站登录门（AuthGate）先查 /api/skills/me；CI 里没有 skill-runner，这里统一当作已登录。
// 个别 spec 自己再 route 这个地址时，后注册的优先。
export const test = base.extend({
  page: async ({ page }, provide) => {
    await page.route('**/api/skills/me', route => route.fulfill({ json: { ok: true, max_active: 2, max_upload_mb: 95 } }));
    await provide(page);
  },
});
