import { expect, test, type Page } from '@playwright/test';

async function mockDocument(page: Page, sourceHtml?: string) {
  const paragraphs = [
    { id: 'p1', index: 0, source: 'English source.', translation: '原有译文', status: 'translated', element_type: sourceHtml ? 'table' : 'p', source_html: sourceHtml },
    { id: 'p2', index: 1, source: 'Another source.', translation: '下一段译文', status: 'translated', element_type: 'p' },
  ];
  const section = { section_id: 's1', title: 'Test section', total_paragraphs: 2, approved_count: 0, is_complete: false, paragraphs };
  const project = { id: 'editor-safety', title: 'Editor safety', status: 'created', created_at: '2026-01-01T00:00:00', progress: { total: 2, total_sections: 1, total_paragraphs: 2, approved: 0, percent: 0 }, sections: [section] };
  await page.route('**/api/projects/editor-safety/translation-status', route => route.fulfill({ json: { status: 'idle', project_id: project.id, total_paragraphs: 2, translated_paragraphs: 2 } }));
  await page.route('**/api/projects/editor-safety', route => route.fulfill({ json: project }));
  await page.route('**/api/projects', route => route.fulfill({ json: [project] }));
  await page.route('**/api/projects/editor-safety/sections/s1', route => route.fulfill({ json: section }));
  await page.route('**/api/projects/editor-safety/sections/s1/paragraphs/p1', route => {
    const data = route.request().postDataJSON() as { translation?: string };
    return route.fulfill({ json: { id: 'p1', translation: data.translation ?? '原有译文', status: 'modified' } });
  });
}

test('imported table HTML cannot execute app-origin script', async ({ page }) => {
  await mockDocument(page, '<table><tr><td>SAFE_CELL</td><td><img src="invalid-image" onerror="window.__unsafeTable=1"></td><td><a href="javascript:window.__unsafeTable=2">bad</a></td></tr></table><script>window.__unsafeTable=3</script>');
  await page.goto('/document/editor-safety/s1');
  await expect(page.getByText('SAFE_CELL', { exact: true }).first()).toBeVisible();
  expect(await page.evaluate(() => Reflect.get(window, '__unsafeTable'))).toBeUndefined();
  await expect(page.locator('table [onerror], table a[href^="javascript:"]')).toHaveCount(0);
});

test('side editor keeps new typing when retranslation finishes', async ({ page }) => {
  await mockDocument(page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/projects/editor-safety/sections/s1/paragraphs/p1/translate', async route => {
    await gate;
    await route.fulfill({ json: { id: 'p1', translation: '模型生成的译文', status: 'translated' } });
  });
  await page.goto('/document/editor-safety/s1?paragraph=p1');
  const field = page.getByLabel('段落译文');
  await expect(field).toHaveValue('原有译文');
  const outgoing = page.waitForRequest('**/paragraphs/p1/translate');
  await page.getByRole('button', { name: '重新翻译', exact: true }).click();
  await outgoing;
  await field.fill('等待期间输入的新稿');
  release();
  await expect(page.getByRole('button', { name: '重新翻译', exact: true })).toBeEnabled();
  await expect(field).toHaveValue('等待期间输入的新稿');
});

test('confirming an older draft does not advance away from newer input', async ({ page }) => {
  await mockDocument(page);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/projects/editor-safety/sections/s1/paragraphs/p1/confirm', async route => {
    await gate;
    await route.fulfill({ json: { success: true } });
  });
  await page.goto('/document/editor-safety/s1?paragraph=p1');
  const field = page.getByLabel('段落译文');
  await expect(field).toHaveValue('原有译文');
  const outgoing = page.waitForRequest('**/paragraphs/p1/confirm');
  await page.getByRole('button', { name: /确认.*下一|确认译文|确认并/ }).last().click();
  await outgoing;
  await field.fill('确认期间输入的新稿');
  release();
  await expect(field).toHaveValue('确认期间输入的新稿');
  await expect(page).toHaveURL(/paragraph=p1/);
});
