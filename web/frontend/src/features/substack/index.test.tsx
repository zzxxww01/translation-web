// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiErrorWrapper } from '@/shared/api/client';
import { documentApi } from '../document/api';
import { substackApi, type SubstackArticle } from './api';
import { SubstackFeature } from './index';

vi.mock('sonner', () => ({ toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() } }));

const article = (overrides: Partial<SubstackArticle>): SubstackArticle => ({
  title: 'Paid Post',
  subtitle: 'A subtitle',
  slug: 'paid-post',
  url: 'https://newsletter.semianalysis.com/p/paid-post',
  post_date: '2026-10-23T19:06:44.981Z',
  is_paid: true,
  cover_image: null,
  wordcount: 3308,
  zh_title: '付费文章的中文标题',
  zh_summary: '一句话中文摘要',
  project_id: null,
  status: 'not_imported',
  progress: 0,
  ...overrides,
});

const project = { id: 'paid-post-project', title: 'Paid Post' };

let root: Root;
let host: HTMLDivElement;
let client: QueryClient;

function buttons(label: string) {
  return Array.from(host.querySelectorAll('button')).filter(el => el.textContent?.trim() === label);
}
function button(label: string) {
  return buttons(label)[0];
}
async function settle() {
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 30)); });
}
async function click(label: string) {
  expect(button(label), `button「${label}」`).toBeDefined();
  await act(async () => { button(label)!.click(); });
  await settle();
}
function listWith(articles: SubstackArticle[], extra: Partial<{ digesting: boolean; pending_digests: number }> = {}) {
  return vi.spyOn(substackApi, 'listArticles').mockResolvedValue({
    articles,
    next_offset: null,
    total: articles.length,
    pending_digests: 0,
    digesting: false,
    ...extra,
  });
}
async function render() {
  await act(async () => {
    root.render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/substack']}>
          <Routes>
            <Route path="/substack" element={<SubstackFeature />} />
            <Route path="/document/:id" element={<div>项目页</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  });
  await settle();
}

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  vi.stubGlobal('IntersectionObserver', class { observe() {} disconnect() {} });
  localStorage.clear();
  vi.spyOn(substackApi, 'getCookieStatus').mockResolvedValue({ configured: false, domain: 'newsletter.semianalysis.com' });
  vi.spyOn(substackApi, 'syncArticles').mockResolvedValue({ added: 0, total: 2 });
  listWith([
    article({}),
    article({ slug: 'old-post', title: 'Old Post', is_paid: false, project_id: 'old-post-project', status: 'imported' }),
  ]);
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  host = document.createElement('div');
  document.body.appendChild(host);
  root = createRoot(host);
});

afterEach(() => {
  act(() => root.unmount());
  host.remove();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('SubstackFeature', () => {
  it('lists articles with date, Chinese digest, paid badge and status', async () => {
    await render();
    const text = host.textContent ?? '';
    expect(text).toContain('Paid Post');
    expect(text).toContain('付费文章的中文标题');
    expect(text).toContain('一句话中文摘要');
    expect(text).toContain('2026年10月'); // 不断言具体哪天：UTC 晚上发布的文章在东八区已是次日
    expect(text).toContain('付费');
    expect(text).toContain('3,308 词');
    expect(text).toContain('已导入，还没翻译');
    expect(button('开始翻译')).toBeDefined();
    expect(text).toContain('已经到底了，共 2 篇');
  });

  it('checks Substack for new articles once after the saved list shows', async () => {
    const sync = vi.mocked(substackApi.syncArticles).mockResolvedValue({ added: 3, total: 5 });
    const { toast } = await import('sonner');
    await render();
    expect(sync).toHaveBeenCalledTimes(1);
    expect(sync).toHaveBeenCalledWith();
    expect(toast.info).toHaveBeenCalledWith('有 3 篇新文章');
    expect(substackApi.listArticles).toHaveBeenCalledTimes(2); // 有新文章就重新读一次
  });

  it('refreshes the whole list on demand', async () => {
    const sync = vi.mocked(substackApi.syncArticles);
    await render();
    sync.mockResolvedValue({ added: 0, total: 2 });
    await click('刷新清单');
    expect(sync).toHaveBeenLastCalledWith(true);
  });

  it('passes the filter to the server', async () => {
    await render();
    await click('没导入');
    expect(substackApi.listArticles).toHaveBeenLastCalledWith(0, '', 'not_imported');
  });

  it('marks articles published after the last visit as new', async () => {
    localStorage.setItem('substack-library:last-visit', String(Date.parse('2026-10-01T00:00:00Z')));
    listWith([article({}), article({ slug: 'older', post_date: '2026-09-01T00:00:00Z' })]);
    await render();
    const badges = Array.from(host.querySelectorAll('span')).filter(el => el.textContent === '新');
    expect(badges).toHaveLength(1);
  });

  it('imports an article, stays on the list and offers to translate it', async () => {
    const importArticle = vi.spyOn(substackApi, 'importArticle').mockResolvedValue({ project, already_imported: false });
    const startWorkflow = vi.spyOn(documentApi, 'startLongformWorkflow');
    await render();
    await click('导入');
    expect(importArticle).toHaveBeenCalledWith('https://newsletter.semianalysis.com/p/paid-post');
    expect(startWorkflow).not.toHaveBeenCalled();
    expect(host.textContent).not.toContain('项目页');
    expect(button('导入')).toBeUndefined();
    expect(buttons('开始翻译')).toHaveLength(2);
  });

  it('opens the project after 导入并翻译 so the terms can be confirmed', async () => {
    vi.spyOn(substackApi, 'importArticle').mockResolvedValue({ project, already_imported: false });
    const startWorkflow = vi.spyOn(documentApi, 'startLongformWorkflow').mockResolvedValue({} as never);
    await render();
    await click('导入并翻译');
    expect(startWorkflow).toHaveBeenCalledWith('paid-post-project', 'four-step', undefined, undefined, {
      model_scope: 'all',
      efficiency: { compact_review: false },
    });
    expect(host.textContent).toContain('项目页');
  });

  it('does not restart translation for an article that was already imported', async () => {
    vi.spyOn(substackApi, 'importArticle').mockResolvedValue({ project, already_imported: true });
    const startWorkflow = vi.spyOn(documentApi, 'startLongformWorkflow');
    await render();
    await click('导入并翻译');
    expect(startWorkflow).not.toHaveBeenCalled();
  });

  it('starts translating an imported article and opens it', async () => {
    const startWorkflow = vi.spyOn(documentApi, 'startLongformWorkflow').mockResolvedValue({} as never);
    await render();
    await click('开始翻译');
    expect(startWorkflow).toHaveBeenCalledWith('old-post-project', 'four-step', undefined, undefined, expect.anything());
    expect(host.textContent).toContain('项目页');
  });

  it('stays on the list when starting translation fails', async () => {
    vi.spyOn(documentApi, 'startLongformWorkflow').mockRejectedValue(new ApiErrorWrapper('已有翻译在进行', 409));
    const { toast } = await import('sonner');
    await render();
    await click('开始翻译');
    expect(toast.error).toHaveBeenCalledWith('启动翻译失败：已有翻译在进行', expect.anything());
    expect(host.textContent).not.toContain('项目页');
  });

  it('shows translation progress and sends 等你确认术语 to the project', async () => {
    listWith([
      article({ project_id: 'p1', status: 'awaiting_terms', progress: 0 }),
      article({ slug: 'b', project_id: 'p2', status: 'translating', progress: 40 }),
      article({ slug: 'c', project_id: 'p3', status: 'translated', progress: 100 }),
      article({ slug: 'd', project_id: 'p4', status: 'partial', progress: 25 }),
    ]);
    await render();
    const text = host.textContent ?? '';
    expect(text).toContain('翻译中 40%');
    expect(text).toContain('已译完');
    expect(text).toContain('已翻 25%，没翻完');
    expect(button('继续翻译')).toBeDefined();
    await click('等你确认术语');
    expect(host.textContent).toContain('项目页');
  });

  it('asks for the cookie on a paywall error and retries after saving', async () => {
    const importArticle = vi.spyOn(substackApi, 'importArticle')
      .mockRejectedValueOnce(
        new ApiErrorWrapper('订阅 cookie 已失效，请重新复制一份填进来', 400, { error_code: 'COOKIE_EXPIRED' })
      )
      .mockResolvedValueOnce({ project, already_imported: false });
    const saveCookie = vi.spyOn(substackApi, 'saveCookie').mockResolvedValue({ configured: true, domain: 'x' });
    await render();
    await click('导入');
    expect(host.textContent).toContain('订阅 cookie 已失效');

    const textarea = host.querySelector('textarea[aria-label="订阅 cookie"]') as HTMLTextAreaElement;
    expect(textarea).not.toBeNull();
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!;
      setter.call(textarea, 'connect.sid=s%3Anew');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await click('保存');

    expect(saveCookie).toHaveBeenCalledWith('connect.sid=s%3Anew');
    expect(importArticle).toHaveBeenCalledTimes(2);
    expect(host.querySelector('textarea[aria-label="订阅 cookie"]')).toBeNull();
  });

  it('shows other import errors without opening the cookie form', async () => {
    vi.spyOn(substackApi, 'importArticle').mockRejectedValue(
      new ApiErrorWrapper('下载失败', 502, { error_code: 'UPSTREAM_ERROR' })
    );
    const { toast } = await import('sonner');
    await render();
    await click('导入');
    expect(toast.error).toHaveBeenCalledWith('下载失败');
    expect(host.querySelector('textarea')).toBeNull();
    expect(button('导入')).toBeDefined();
  });
});
