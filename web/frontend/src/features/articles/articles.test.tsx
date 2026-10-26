// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { toast } from 'sonner';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EditableText } from './components/EditableText';
import { Workbench } from './components/Workbench';
import { SAVE_DELAY_MS, unsavedEdits } from './lib/edits';
import { AUTO_SYNC_GAP_MS, useAutoSyncArticles } from './hooks';
import { importAndTranslate } from './lib/importFlow';
import type { RunMeta } from '@/features/skills/types';
import type { Workbench as WorkbenchData } from './types';

const api = vi.hoisted(() => ({
  workbench: vi.fn(),
  saveText: vi.fn(),
  setReadingMark: vi.fn(),
  startWorkflow: vi.fn(),
  createModelVariant: vi.fn(),
  exportMarkdown: vi.fn(),
  setClaudeRun: vi.fn(),
  sourceHtml: vi.fn(),
  changes: vi.fn(),
}));
const substack = vi.hoisted(() => ({ importArticle: vi.fn(), syncArticles: vi.fn() }));
const claude = vi.hoisted(() => ({ startClaudeTrack: vi.fn(), importClaudeTrack: vi.fn() }));
const agentRun = vi.hoisted(() => ({ current: undefined as RunMeta | undefined }));
vi.mock('./api', () => ({ articlesApi: api, downloadText: vi.fn(), HUMAN_EDITS_URL: '/api/workbench/human-edits.jsonl' }));
vi.mock('./hooks', async importOriginal => ({
  ...(await importOriginal<object>()),
  useClaudeRun: () => ({ data: agentRun.current, error: null, refetch: vi.fn() }),
}));
vi.mock('@/features/substack/api', () => ({ substackApi: substack, isCookieError: () => false }));
vi.mock('./lib/claude', async importOriginal => ({ ...(await importOriginal<object>()), ...claude }));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() } }));

let root: Root;
let host: HTMLDivElement;

async function render(node: React.ReactNode) {
  await act(async () => {
    root.render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter>{node}</MemoryRouter>
      </QueryClientProvider>
    );
  });
}

const flush = () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  Object.values(api).forEach(fn => fn.mockReset());
  substack.importArticle.mockReset();
  claude.startClaudeTrack.mockReset();
  claude.importClaudeTrack.mockReset();
  agentRun.current = undefined;
  vi.mocked(toast.success).mockReset();
  localStorage.clear(); // 收起的栏会记在 localStorage 里
  host = document.createElement('div');
  document.body.appendChild(host);
  root = createRoot(host);
});

afterEach(() => {
  act(() => root.unmount());
  host.remove();
  vi.useRealTimers();
});

describe('EditableText', () => {
  it('saves once after the pause, then retries a failed save on demand', async () => {
    vi.useFakeTimers();
    const onSave = vi.fn().mockRejectedValueOnce(new Error('down')).mockResolvedValue(undefined);
    await render(<EditableText id="t1" value="旧" placeholder="" ariaLabel="格子" onSave={onSave} />);
    await act(async () => { (host.querySelector('[aria-label="编辑：格子"]') as HTMLElement).click(); });
    const textarea = host.querySelector('textarea')!;
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!;
      setter.call(textarea, '新译文');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    expect(unsavedEdits.any()).toBe(true);
    await act(async () => { vi.advanceTimersByTime(SAVE_DELAY_MS + 10); });
    expect(onSave).toHaveBeenCalledWith('新译文');
    const retry = Array.from(host.querySelectorAll('button')).find(b => b.textContent?.includes('重试'))!;
    await act(async () => { retry.click(); });
    expect(onSave).toHaveBeenCalledTimes(2);
    // 段落里不再显示「已保存」，状态汇总到栏头
    expect(host.textContent).not.toContain('已保存');
    expect(unsavedEdits.any()).toBe(false);
    expect(unsavedEdits.snapshot('t1')).toMatch(/^0\|0\|[1-9]/);
  });
});

describe('EditableText display', () => {
  it('shows links as links until clicked, then edits the raw Markdown', async () => {
    await render(<EditableText id="t2" value="见[行业模型](https://x.com/m)。" placeholder="" ariaLabel="格子" onSave={vi.fn()} />);
    const link = host.querySelector('a')!;
    expect(link.textContent).toBe('行业模型');
    expect(host.textContent).not.toContain('https://x.com/m');
    await act(async () => { (host.querySelector('[aria-label="编辑：格子"]') as HTMLElement).click(); });
    expect(host.querySelector('textarea')!.value).toBe('见[行业模型](https://x.com/m)。');
  });

  it('renders italic captions with a link inside', async () => {
    await render(<EditableText id="t3" value="*来源：[行业模型](https://x.com/m)*" placeholder="" ariaLabel="格子" onSave={vi.fn()} />);
    expect(host.querySelector('em a')?.textContent).toBe('行业模型');
    expect(host.textContent).toBe('来源：行业模型');
  });
});

describe('useAutoSyncArticles', () => {
  function Probe({ at }: { at: string }) {
    useAutoSyncArticles(at);
    return null;
  }

  it('checks Substack on entry and whenever another article or workbench opens, at most once per gap', async () => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(10_000_000);
    substack.syncArticles.mockReset().mockResolvedValue({ added: 0, total: 1 });
    await render(<Probe at="|" />);
    expect(substack.syncArticles).toHaveBeenCalledTimes(1);

    await render(<Probe at="|some-article" />); // 刚查过，连着点不重复查
    expect(substack.syncArticles).toHaveBeenCalledTimes(1);

    vi.setSystemTime(10_000_000 + AUTO_SYNC_GAP_MS + 1);
    substack.syncArticles.mockResolvedValue({ added: 2, total: 3 });
    await render(<Probe at="project-1|" />);
    await flush();
    expect(substack.syncArticles).toHaveBeenCalledTimes(2);
    expect(toast.success).toHaveBeenCalledWith('文章库新增 2 篇');
  });
});

describe('importAndTranslate', () => {
  beforeEach(() => {
    substack.importArticle.mockResolvedValue({ project: { id: 'p1' }, already_imported: false });
    api.startWorkflow.mockResolvedValue({ run_id: 'r' });
    claude.startClaudeTrack.mockResolvedValue({ id: 'run-1' });
  });

  it.each([
    ['both', true, true],
    ['web', true, false],
    ['agent', false, true],
    ['import', false, false],
  ] as const)('plan %s: web %s, agent %s', async (plan, web, agent) => {
    await expect(importAndTranslate({ url: 'u', title: 'Demo', zh_title: '演示' }, plan, 'codex', vi.fn())).resolves.toBe('p1');
    expect(api.startWorkflow.mock.calls).toEqual(web ? [['p1']] : []);
    // 对话标题用文章的中文标题
    expect(claude.startClaudeTrack.mock.calls).toEqual(agent ? [['p1', 'codex', '演示']] : []);
  });

  it('does not start anything again for an article imported before', async () => {
    substack.importArticle.mockResolvedValue({ project: { id: 'p1' }, already_imported: true });
    await importAndTranslate({ url: 'u' }, 'both', 'claude', vi.fn());
    expect(api.startWorkflow).not.toHaveBeenCalled();
    expect(claude.startClaudeTrack).not.toHaveBeenCalled();
  });

  it('still opens the article when the agent cannot start', async () => {
    claude.startClaudeTrack.mockRejectedValue(new Error('skill-runner 挂了'));
    const notify = vi.fn();

    await expect(importAndTranslate({ url: 'u' }, 'agent', 'claude', notify)).resolves.toBe('p1');

    expect(notify).toHaveBeenCalledWith(expect.stringContaining('skill-runner 挂了'));
  });
});

const DATA: WorkbenchData = {
  project: {
    id: 'p1', title: 'Datacenters 2027', title_translation: '2027 数据中心', original_url: null, created_at: '', claude_run_id: null,
    progress: { total: 2, approved: 0 },
    status: { active: false, run_id: null, status: null, current_step: null, translated: 2, total: 2, error: null },
  },
  variants: [{
    id: 'p1--argon', kind: 'model', label: 'argon', title_translation: null, progress: { total: 2, approved: 0 }, import: null,
    status: { active: false, run_id: null, status: null, current_step: null, translated: 1, total: 2, error: null },
  }],
  rows: [
    { key: 'section:s1', kind: 'section', section_id: 's1', paragraph_id: null, source: 'Introduction', web: '引言', alt: { 'p1--argon': '前言' } },
    { key: 's1/p000', kind: 'p', section_id: 's1', paragraph_id: 'p000', source: 'Datacenters are booming.', web: '数据中心正在爆发。', alt: { 'p1--argon': null } },
    { key: 's1/p001', kind: 'image', section_id: 's1', paragraph_id: 'p001', source: 'https://cdn/x.png', image: 'https://cdn/x.png', web: null, alt: { 'p1--argon': null } },
  ],
};

describe('Workbench', () => {
  it('shows continuous English and both translations, collapses a pane and saves into the right project', async () => {
    api.workbench.mockResolvedValue(DATA);
    api.saveText.mockResolvedValue({ ok: true });
    await render(<Workbench projectId="p1" />);
    await flush();

    expect(host.textContent).toContain('2027 数据中心');
    expect(host.textContent).toContain('Datacenters are booming.');
    const cells = Array.from(host.querySelectorAll('[aria-label^="编辑："]'));
    expect(cells.map(cell => cell.textContent)).toEqual(['引言', '数据中心正在爆发。', '前言', '还没有译文，可以直接写']);

    const collapse = host.querySelector('button[aria-label="收起英文"]') as HTMLButtonElement;
    await act(async () => { collapse.click(); });
    expect(host.querySelector('button[aria-label="展开英文"]')).not.toBeNull();
    expect(host.textContent).not.toContain('Datacenters are booming.');

    const adopt = Array.from(host.querySelectorAll('button')).find(b => b.textContent === '用argon这段')!;
    await act(async () => { adopt.click(); });
    await flush();
    expect(api.saveText).toHaveBeenCalledWith('p1', { target: 'p1', section_id: 's1', paragraph_id: null, text: '前言' });
  });

  it('joins imported fragments into a natural paragraph and saves edits to the original fragment', async () => {
    api.workbench.mockResolvedValue({ ...DATA, rows: [
      { ...DATA.rows[1], block: 'b1', source: 'First sentence.', web: '第一句。' },
      { ...DATA.rows[1], key: 's1/p002', paragraph_id: 'p002', block: 'b1', source: 'Second sentence.', web: '第二句。' },
      { ...DATA.rows[1], key: 's1/p003', paragraph_id: 'p003', block: 'b2', source: 'Next paragraph.', web: '下一段。' },
    ] });
    api.saveText.mockResolvedValue({ ok: true });
    await render(<Workbench projectId="p1" />);
    await flush();
    const article = host.querySelector('[aria-label="译本 1正文"]')!;
    const blocks = article.querySelectorAll('[data-reading-block]');
    expect(blocks).toHaveLength(2);
    expect(blocks[0].textContent).toContain('第一句。第二句。');
    await act(async () => { (article.querySelector('[aria-label="编辑：译本 1：Second sentence."]') as HTMLElement).click(); });
    const textarea = host.querySelector('textarea')!;
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!.call(textarea, '第二句改了。');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true })); });
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 180)); });
    expect(api.saveText).toHaveBeenCalledWith('p1', { target: 'p1', section_id: 's1', paragraph_id: 'p002', text: '第二句改了。' });
    expect(unsavedEdits.any()).toBe(false);
  });

  it('persists a reading mark, restores it on reload, jumps to it and clears it', async () => {
    let mark: { key: string; at: string } | null = null;
    api.workbench.mockImplementation(async () => ({ ...DATA, reading_mark: mark }));
    api.setReadingMark.mockImplementation(async (_id: string, key: string | null) => {
      mark = key ? { key, at: '2026-10-27T01:00:00' } : null;
      return { ok: true, reading_mark: mark };
    });
    await render(<Workbench projectId="p1" />);
    await flush();
    const button = host.querySelector('[aria-label="译本 1：从这里继续阅读 — Datacenters are booming."]') as HTMLButtonElement;
    await act(async () => { button.click(); });
    await flush();
    expect(api.setReadingMark).toHaveBeenCalledWith('p1', 's1/p000');
    await render(<Workbench key="reloaded" projectId="p1" />);
    await flush();
    expect(host.querySelectorAll('[data-reading-mark="true"]')).toHaveLength(3);
    const scroll = vi.fn();
    host.querySelectorAll('[data-reading-mark="true"]').forEach(el => { el.scrollIntoView = scroll; });
    await act(async () => { Array.from(host.querySelectorAll('button')).find(b => b.textContent?.trim() === '继续阅读')!.click(); });
    expect(scroll).toHaveBeenCalledTimes(3);
    await act(async () => { (host.querySelector('[aria-label="清除阅读标记"]') as HTMLButtonElement).click(); });
    await flush();
    expect(api.setReadingMark).toHaveBeenLastCalledWith('p1', null);
    expect(host.querySelectorAll('[data-reading-mark="true"]')).toHaveLength(0);
  });

  it('keeps missing fragments editable and can adopt their translation from the other version', async () => {
    api.workbench.mockResolvedValue({ ...DATA, rows: [
      { ...DATA.rows[1], block: 'b1', web: '已有的译文。' },
      { ...DATA.rows[1], key: 's1/p002', paragraph_id: 'p002', block: 'b1', source: 'Missing part.', web: null, alt: { 'p1--argon': '另一版的后半段。' } },
    ] });
    api.saveText.mockResolvedValue({ ok: true });
    await render(<Workbench projectId="p1" />);
    await flush();
    const article = host.querySelector('[aria-label="译本 1正文"]')!;
    expect(article.querySelector('[aria-label="编辑：译本 1：Missing part."]')?.textContent).toBe('待补译');
    await act(async () => { Array.from(article.querySelectorAll('button')).find(b => b.textContent === '用argon这段')!.click(); });
    await flush();
    expect(api.saveText).toHaveBeenCalledWith('p1', { target: 'p1', section_id: 's1', paragraph_id: 'p002', text: '另一版的后半段。' });
  });

  it('retains a second fragment draft while the first fragment finishes saving', async () => {
    api.workbench.mockResolvedValue({ ...DATA, rows: [
      { ...DATA.rows[1], block: 'b1', source: 'First.', web: null },
      { ...DATA.rows[1], key: 's1/p002', paragraph_id: 'p002', block: 'b1', source: 'Second.', web: null },
    ] });
    let saved!: (value: { ok: boolean }) => void;
    api.saveText.mockImplementationOnce(() => new Promise(resolve => { saved = resolve; })).mockResolvedValue({ ok: true });
    await render(<Workbench projectId="p1" />);
    await flush();
    const edit = async (source: string, text: string) => {
      await act(async () => { (host.querySelector(`[aria-label="编辑：译本 1：${source}"]`) as HTMLElement).click(); });
      await act(async () => {
        const textarea = host.querySelector('textarea')!;
        Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!.call(textarea, text);
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
      });
    };
    await edit('First.', '第一段已保存。');
    await act(async () => { host.querySelector('textarea')!.blur(); });
    await edit('Second.', '第二段草稿。');
    await act(async () => { saved({ ok: true }); });
    expect(host.querySelector('textarea')?.value).toBe('第二段草稿。');
    expect(unsavedEdits.any()).toBe(true);
    await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true })); });
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 180)); });
    expect(api.saveText).toHaveBeenLastCalledWith('p1', { target: 'p1', section_id: 's1', paragraph_id: 'p002', text: '第二段草稿。' });
    expect(unsavedEdits.any()).toBe(false);
  });

  it('keeps the previous reading mark when saving fails', async () => {
    api.workbench.mockResolvedValue({ ...DATA, reading_mark: { key: 's1/p000', at: '2026-10-27' } });
    api.setReadingMark.mockRejectedValue(new Error('离线了'));
    await render(<Workbench projectId="p1" />);
    await flush();
    await act(async () => { (host.querySelector('[aria-label="清除阅读标记"]') as HTMLButtonElement).click(); });
    await flush();
    expect(host.querySelectorAll('[data-reading-mark="true"]')).toHaveLength(3);
    expect(toast.error).toHaveBeenCalledWith('阅读标记没保存上：离线了');
  });

  it('shows images in every column, not just the English one', async () => {
    api.workbench.mockResolvedValue(DATA);
    await render(<Workbench projectId="p1" />);
    await flush();
    expect(Array.from(host.querySelectorAll('img')).map(img => img.getAttribute('src'))).toEqual(['https://cdn/x.png', 'https://cdn/x.png', 'https://cdn/x.png']);
    expect(host.textContent).not.toContain('（图片）');
  });

  it('saves on demand (button or Ctrl+S) without any "final version" step, and shows what was changed', async () => {
    api.workbench.mockResolvedValue(DATA);
    api.changes.mockResolvedValue({
      total: 2, changed: 1,
      changes: [{
        key: 's1/p000', section_id: 's1', section_title: 'Introduction', paragraph_id: 'p000', kind: 'p',
        source: 'Datacenters are booming.', before: '数据中心正在繁荣。', after: '数据中心正在爆发。',
        segments: [{ op: 'equal', text: '数据中心正在' }, { op: 'delete', text: '繁荣' }, { op: 'insert', text: '爆发' }, { op: 'equal', text: '。' }],
      }],
    });
    await render(<Workbench projectId="p1" />);
    await flush();

    expect(host.textContent).not.toContain('保存全文');
    expect(host.textContent).not.toContain('定稿');
    const saveButton = Array.from(host.querySelectorAll('button')).find(b => b.textContent?.trim() === '保存')!;
    await act(async () => { saveButton.click(); });
    await flush();
    expect(toast.success).toHaveBeenCalledWith('已保存');
    await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true })); });
    await flush();
    expect(toast.success).toHaveBeenCalledTimes(2);

    await act(async () => { (host.querySelector('button[aria-label="看你改了什么"]') as HTMLButtonElement).click(); });
    await flush();
    expect(api.changes).toHaveBeenCalledWith('p1', 'p1');
    expect(document.body.querySelector('del')?.textContent).toBe('繁荣');
    expect(document.body.querySelector('ins')?.textContent).toBe('爆发');
  });

  it('treats an agent that ended its turn asking for confirmation as waiting, not as finished', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'run-1' }, variants: [] });
    agentRun.current = {
      id: 'run-1', skill: 'four-step-translate', title: 't', status: 'idle', created_at: 0, updated_at: 0,
      session_id: 's', error: null, harness: 'codex', awaiting_reply: true, auto_reply_at: Date.UTC(2026, 9, 26, 6, 30) / 1000,
    };
    await render(<Workbench projectId="p1" />);
    await flush();
    expect(host.textContent).toContain('Codex 在等你确认');
    expect(host.textContent).toContain('不回复就自动按它的建议继续');
    expect(claude.importClaudeTrack).not.toHaveBeenCalled();
  });
});
