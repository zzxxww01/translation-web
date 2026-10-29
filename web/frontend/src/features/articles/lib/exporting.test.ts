// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest';

const wechat = vi.hoisted(() => ({ format: vi.fn() }));
vi.mock('@/features/wechat/api', () => ({ wechatApi: wechat }));

import { copyForWechat, markdownToHtml, printDocument, sendToWechatEditor } from './exporting';
import { WECHAT_DRAFT_STORAGE_KEY } from '@/features/wechat/draft';

describe('export helpers', () => {
  beforeEach(() => {
    localStorage.clear();
    wechat.format.mockReset();
  });

  it('renders the exported Markdown with images but without scripts or inline styles', () => {
    const html = markdownToHtml('# 标题\n\n正文 **重点**\n\n![](https://cdn.example.com/a.png)\n\n<script>alert(1)</script><p style="color:red">x</p>');
    expect(html).toContain('<h1>标题</h1>');
    expect(html).toContain('<strong>重点</strong>');
    expect(html).toContain('<img src="https://cdn.example.com/a.png"');
    expect(html).not.toContain('<script');
    expect(html).not.toContain('style=');
  });

  it('builds a print page titled after the article', () => {
    const page = printDocument('正文', '华为 <与> DeepSeek');
    expect(page).toContain('<title>华为 &lt;与&gt; DeepSeek</title>');
    expect(page).toContain('@page');
    expect(page).toContain('<article><p>正文</p>');
  });

  it('formats for WeChat with the theme and image handling last chosen on the WeChat page', async () => {
    localStorage.setItem(WECHAT_DRAFT_STORAGE_KEY, JSON.stringify({ markdown: '旧稿', selectedTheme: 'elegant', imageMode: 'upload' }));
    wechat.format.mockResolvedValue({ html: '<p class="t">排好的</p>', css: '.t{color:#123456}', image_count: 0, image_urls: [] });
    const write = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('ClipboardItem', class { constructor(public items: Record<string, Promise<Blob>>) {} });
    Object.defineProperty(navigator, 'clipboard', { value: { write }, configurable: true });
    await copyForWechat(Promise.resolve('# 稿子'));
    expect(wechat.format).toHaveBeenCalledWith({ markdown: '# 稿子', theme: 'elegant', upload_images: true, image_to_base64: false });
    const item = write.mock.calls[0][0][0] as { items: Record<string, Promise<Blob>> };
    const html = await (await item.items['text/html']).text();
    expect(html).toContain('color: #123456'); // 样式已内联
    expect(await (await item.items['text/plain']).text()).toBe('排好的');
    vi.unstubAllGlobals();
  });

  it('hands the Markdown to the WeChat page draft without losing its settings', () => {
    localStorage.setItem(WECHAT_DRAFT_STORAGE_KEY, JSON.stringify({ markdown: '旧稿', selectedTheme: 'elegant', imageMode: 'base64' }));
    sendToWechatEditor('# 新稿');
    expect(JSON.parse(localStorage.getItem(WECHAT_DRAFT_STORAGE_KEY)!)).toEqual({ markdown: '# 新稿', selectedTheme: 'elegant', imageMode: 'base64' });
  });
});
