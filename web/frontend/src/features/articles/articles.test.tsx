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
import { editHistory } from './lib/history';
import { AUTO_SYNC_GAP_MS, useAutoSyncArticles } from './hooks';
import { AlignmentTooLow } from './lib/claude';
import { importAndTranslate } from './lib/importFlow';
import { skillsApi } from '@/features/skills/api';
import { ApiErrorWrapper } from '@/shared/api/client';
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
  setPrimary: vi.fn(),
}));
const substack = vi.hoisted(() => ({ importArticle: vi.fn(), syncArticles: vi.fn() }));
const claude = vi.hoisted(() => ({ startClaudeTrack: vi.fn(), importClaudeTrack: vi.fn() }));
const agentRun = vi.hoisted(() => ({ current: undefined as RunMeta | undefined }));
const stopAgent = vi.hoisted(() => vi.fn());
const models = vi.hoisted(() => vi.fn());
vi.mock('@/features/skills/api', async importOriginal => {
  const actual = await importOriginal<typeof import('@/features/skills/api')>();
  return { ...actual, skillsApi: { ...actual.skillsApi, stop: stopAgent, models } };
});
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

const inPopover = () => document.body.querySelector('[role="dialog"]') as HTMLElement;
const buttonIn = (root: ParentNode, text: string) =>
  Array.from(root.querySelectorAll('button')).find(b => b.textContent?.trim() === text) as HTMLButtonElement;

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  Object.values(api).forEach(fn => fn.mockReset());
  substack.importArticle.mockReset();
  claude.startClaudeTrack.mockReset();
  claude.importClaudeTrack.mockReset();
  agentRun.current = undefined;
  stopAgent.mockReset();
  models.mockReset();
  models.mockResolvedValue({ models: [{ id: 'gpt-5.5-codex', label: 'gpt-5.5-codex', description: '' }], default_model: 'gpt-5.5', source: 'cache', warning: null });
  api.setPrimary.mockResolvedValue({ ok: true });
  vi.mocked(toast.success).mockReset();
  vi.mocked(toast.error).mockReset();
  localStorage.clear(); // 收起的栏会记在 localStorage 里
  editHistory.clear();
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

  it('shows read-only text without an edit affordance and ignores adoption', async () => {
    const onSave = vi.fn();
    const ref = { current: null as import('./components/EditableText').EditableTextHandle | null };
    await render(<EditableText ref={ref} id="main:s/p" value="旧译文" placeholder="" ariaLabel="主译本：S" onSave={onSave} readOnly />);
    expect(host.textContent).toBe('旧译文');
    expect(host.querySelector('[role="button"]')).toBeNull();
    await act(async () => { await ref.current!.adopt('新的'); });
    expect(onSave).not.toHaveBeenCalled();
    expect(host.textContent).toBe('旧译文');
  });
});

const typeInto = (textarea: HTMLTextAreaElement, text: string) => act(async () => {
  Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!.call(textarea, text);
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
});
const press = (target: EventTarget, init: KeyboardEventInit) =>
  act(async () => { target.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, cancelable: true, ...init })); });

describe('EditableText direct editing', () => {
  it('puts the caret where the click landed, counting through the hidden link syntax', async () => {
    const raw = '见[行业模型](https://x.com/m)。后文';
    await render(<EditableText id="c1" value={raw} placeholder="" ariaLabel="格子" onSave={vi.fn()} />);
    const box = host.querySelector('[aria-label="编辑：格子"]') as HTMLElement;
    window.getSelection()!.collapse(box.lastChild!, 1); // 「。」后面
    await act(async () => { box.click(); });
    const textarea = host.querySelector('textarea')!;
    expect(document.activeElement).toBe(textarea);
    expect(textarea.selectionStart).toBe(raw.indexOf('。') + 1);
    expect(textarea.selectionEnd).toBe(raw.indexOf('。') + 1);
  });

  it('keeps a selected phrase selected in plain text, and leaves a linked paragraph alone so it can be copied', async () => {
    await render(<>
      <EditableText id="c2" value="数据中心正在爆发。" placeholder="" ariaLabel="普通" onSave={vi.fn()} />
      <EditableText id="c3" value="见[行业模型](https://x.com/m)。" placeholder="" ariaLabel="带链接" onSave={vi.fn()} />
    </>);
    const plain = host.querySelector('[aria-label="编辑：普通"]') as HTMLElement;
    window.getSelection()!.setBaseAndExtent(plain.firstChild!, 2, plain.firstChild!, 4);
    await act(async () => { plain.click(); });
    const textarea = host.querySelector('textarea')!;
    expect(textarea.value.slice(textarea.selectionStart, textarea.selectionEnd)).toBe('中心');
    await act(async () => { textarea.blur(); });

    const linked = host.querySelector('[aria-label="编辑：带链接"]') as HTMLElement;
    const link = linked.querySelector('a')!;
    window.getSelection()!.setBaseAndExtent(linked.firstChild!, 0, link.firstChild!, 2);
    await act(async () => { linked.click(); });
    expect(host.querySelector('textarea')).toBeNull();
    expect(window.getSelection()!.toString()).toBe('见行业');
  });

  it('can still undo a mistake after leaving the paragraph and coming back', async () => {
    vi.useFakeTimers();
    const onSave = vi.fn().mockResolvedValue(undefined);
    await render(<EditableText id="u1" value="原来的译文" placeholder="" ariaLabel="格子" onSave={onSave} />);
    await act(async () => { (host.querySelector('[aria-label="编辑：格子"]') as HTMLElement).click(); });
    await typeInto(host.querySelector('textarea')!, '改错了');
    await act(async () => { host.querySelector('textarea')!.blur(); });
    expect(onSave).toHaveBeenLastCalledWith('改错了');
    expect(host.querySelector('textarea')).toBeNull();

    await act(async () => { (host.querySelector('[aria-label="编辑：格子"]') as HTMLElement).click(); });
    await press(host.querySelector('textarea')!, { key: 'z', ctrlKey: true });
    expect(host.querySelector('textarea')!.value).toBe('原来的译文');
    await act(async () => { vi.advanceTimersByTime(SAVE_DELAY_MS + 10); });
    expect(onSave).toHaveBeenLastCalledWith('原来的译文');
    await press(host.querySelector('textarea')!, { key: 'y', ctrlKey: true });
    expect(host.querySelector('textarea')!.value).toBe('改错了');
  });
});

describe('EditableText editing straight from a selection', () => {
  const clipboard = (type: 'paste' | 'cut', data = '') => {
    const event = new Event(type, { bubbles: true, cancelable: true });
    const setData = vi.fn();
    Object.defineProperty(event, 'clipboardData', { value: { getData: () => data, setData } });
    return { event, setData };
  };
  const two = async (onSave = vi.fn().mockResolvedValue(undefined)) => {
    await render(<>
      <EditableText id="s1" value="见[行业模型](https://x.com/m)。后文很长" placeholder="" ariaLabel="带链接" onSave={onSave} />
      <EditableText id="s2" value="第二段的文字。" placeholder="" ariaLabel="第二段" onSave={onSave} />
    </>);
    return {
      linked: host.querySelector('[aria-label="编辑：带链接"]') as HTMLElement,
      second: host.querySelector('[aria-label="编辑：第二段"]') as HTMLElement,
    };
  };

  it('pastes over a selection without clicking into the paragraph first', async () => {
    vi.useFakeTimers();
    const onSave = vi.fn().mockResolvedValue(undefined);
    const { linked } = await two(onSave);
    // 选中「模型」（在链接里）
    window.getSelection()!.setBaseAndExtent(linked.querySelector('a')!.firstChild!, 2, linked.querySelector('a')!.firstChild!, 4);
    const { event } = clipboard('paste', '大模型');
    await act(async () => { linked.dispatchEvent(event); });
    expect(event.defaultPrevented).toBe(true);
    const textarea = host.querySelector('textarea')!;
    expect(textarea.value).toBe('见[行业大模型](https://x.com/m)。后文很长');
    expect(document.activeElement).toBe(textarea);
    expect(textarea.selectionStart).toBe('见[行业大模型'.length);
    await act(async () => { vi.advanceTimersByTime(SAVE_DELAY_MS + 10); });
    expect(onSave).toHaveBeenLastCalledWith('见[行业大模型](https://x.com/m)。后文很长');
    await press(textarea, { key: 'z', ctrlKey: true });
    expect(textarea.value).toBe('见[行业模型](https://x.com/m)。后文很长');
  });

  it('counts a drag that spills into the next paragraph\'s start as this paragraph only', async () => {
    const { linked, second } = await two();
    window.getSelection()!.setBaseAndExtent(linked.lastChild!, 1, second.firstChild!, 0); // 「后文很长」到下一段开头
    const { event } = clipboard('paste', '。');
    await act(async () => { document.body.dispatchEvent(event); });
    expect(host.querySelector('textarea')!.value).toBe('见[行业模型](https://x.com/m)。。');
  });

  it('leaves a selection across two paragraphs alone', async () => {
    const { linked, second } = await two();
    window.getSelection()!.setBaseAndExtent(linked.lastChild!, 1, second.firstChild!, 3);
    const { event } = clipboard('paste', 'X');
    await act(async () => { document.body.dispatchEvent(event); });
    expect(event.defaultPrevented).toBe(false);
    expect(host.querySelector('textarea')).toBeNull();
  });

  it('cuts and deletes a selection, and starts editing when you type over it', async () => {
    const { second } = await two();
    window.getSelection()!.setBaseAndExtent(second.firstChild!, 0, second.firstChild!, 3);
    const { event, setData } = clipboard('cut');
    await act(async () => { second.dispatchEvent(event); });
    expect(setData).toHaveBeenCalledWith('text/plain', '第二段');
    expect(host.querySelector('textarea')!.value).toBe('的文字。');
    await act(async () => { host.querySelector('textarea')!.blur(); });

    const again = host.querySelector('[aria-label="编辑：第二段"]') as HTMLElement;
    window.getSelection()!.setBaseAndExtent(again.firstChild!, 0, again.firstChild!, 1);
    await press(again, { key: 'Backspace' });
    expect(host.querySelector('textarea')!.value).toBe('文字。');
    await act(async () => { host.querySelector('textarea')!.blur(); });

    const third = host.querySelector('[aria-label="编辑：第二段"]') as HTMLElement;
    window.getSelection()!.setBaseAndExtent(third.firstChild!, 0, third.firstChild!, 2);
    await press(third, { key: '新' });
    // 按键本身由浏览器落进编辑框（jsdom 没有这一步）：这里只看已经进入编辑、选中了同一段
    const textarea = host.querySelector('textarea')!;
    expect(document.activeElement).toBe(textarea);
    expect(textarea.value.slice(textarea.selectionStart, textarea.selectionEnd)).toBe('文字');
  });
});

describe('EditableText undo with an input method', () => {
  it('undoes one committed IME phrase at a time, never back to half-typed pinyin', async () => {
    await render(<EditableText id="ime" value="原文" placeholder="" ariaLabel="格子" onSave={vi.fn().mockResolvedValue(undefined)} />);
    await act(async () => { (host.querySelector('[aria-label="编辑：格子"]') as HTMLElement).click(); });
    const textarea = host.querySelector('textarea')!;
    const compose = async (steps: string[]) => {
      await act(async () => { textarea.dispatchEvent(new CompositionEvent('compositionstart', { bubbles: true })); });
      for (const value of steps) await typeInto(textarea, value);
      await act(async () => { textarea.dispatchEvent(new CompositionEvent('compositionend', { bubbles: true })); });
    };
    await compose(['原文z', '原文zh', '原文中']);
    await compose(['原文中w', '原文中wen', '原文中文']);
    await press(textarea, { key: 'z', ctrlKey: true });
    expect(textarea.value).toBe('原文中');
    await press(textarea, { key: 'z', ctrlKey: true });
    expect(textarea.value).toBe('原文');
  });
});

describe('EditableText read-only switch', () => {
  it('flushes a pending edit and leaves edit mode when the version becomes read-only', async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const node = (readOnly: boolean, value: string) =>
      <EditableText id="ro1" value={value} placeholder="" ariaLabel="格子" onSave={onSave} readOnly={readOnly} />;
    await render(node(false, '旧'));
    await act(async () => { (host.querySelector('[aria-label="编辑：格子"]') as HTMLElement).click(); });
    const textarea = host.querySelector('textarea')!;
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!.call(textarea, '我改的');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await render(node(true, '旧'));
    await flush();
    expect(onSave).toHaveBeenCalledExactlyOnceWith('我改的');
    expect(host.querySelector('textarea')).toBeNull();
    expect(unsavedEdits.any()).toBe(false);
    await render(node(true, '重翻后的新译文'));
    expect(host.textContent).toBe('重翻后的新译文');
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

  const codex = { harness: 'codex' as const, model: 'gpt-5.5-codex' };

  it.each([
    [true, codex],
    [true, null],
    [false, codex],
    [false, null],
  ] as const)('web %s, agent %o', async (web, agent) => {
    await expect(importAndTranslate({ url: 'u', title: 'Demo', zh_title: '演示' }, { web, agent }, vi.fn())).resolves.toBe('p1');
    expect(api.startWorkflow.mock.calls).toEqual(web ? [['p1']] : []);
    // 对话标题用文章的中文标题
    expect(claude.startClaudeTrack.mock.calls).toEqual(agent ? [['p1', agent, '演示']] : []);
  });

  it('does not start anything again for an article imported before', async () => {
    substack.importArticle.mockResolvedValue({ project: { id: 'p1' }, already_imported: true });
    await importAndTranslate({ url: 'u' }, { web: true, agent: codex }, vi.fn());
    expect(api.startWorkflow).not.toHaveBeenCalled();
    expect(claude.startClaudeTrack).not.toHaveBeenCalled();
  });

  it('still opens the article when the agent cannot start', async () => {
    claude.startClaudeTrack.mockRejectedValue(new Error('skill-runner 挂了'));
    const notify = vi.fn();
    await expect(importAndTranslate({ url: 'u' }, { web: false, agent: { harness: 'claude', model: '' } }, notify)).resolves.toBe('p1');
    expect(notify).toHaveBeenCalledWith(expect.stringContaining('skill-runner 挂了'));
  });
});

const DATA: WorkbenchData = {
  project: {
    id: 'p1', title: 'Datacenters 2027', title_translation: '2027 数据中心', original_url: null, created_at: '', claude_run_id: null,
    progress: { total: 2, approved: 0 }, primary: 'p1', primary_target: null,
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

const WITH_CODEX: WorkbenchData = {
  ...DATA,
  variants: [...DATA.variants, {
    id: 'p1--codex', kind: 'claude', label: 'Codex', title_translation: null, progress: { total: 2, approved: 0 },
    status: { active: false, run_id: null, status: null, current_step: null, translated: 2, total: 2, error: null },
    import: { run_id: 'r0', agent: 'codex', model: 'gpt-5.5', aligned: 2, unaligned: 0, merged_blocks: 0, imported_at: '2026-10-28T10:00:00' },
  }],
  rows: DATA.rows.map(row => ({ ...row, alt: { ...row.alt, 'p1--codex': row.kind === 'image' ? null : `码·${row.source}` } })),
};

describe('Workbench', () => {
  const runningAgent: RunMeta = {
    id: 'old-run', skill: 'four-step-translate', title: 't', status: 'running', created_at: 0, updated_at: 0,
    session_id: 'old-thread', error: null, harness: 'codex',
  };

  it('adds a new agent from ＋ and waits for the old run to stop before starting it', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'old-run' } });
    agentRun.current = runningAgent;
    let finishStop!: () => void;
    stopAgent.mockImplementation(() => new Promise<RunMeta>(resolve => {
      finishStop = () => resolve({ ...runningAgent, status: 'error', error: '任务已停止' });
    }));
    claude.startClaudeTrack.mockResolvedValue({ ...runningAgent, id: 'new-run', harness: 'antigravity' });
    await render(<Workbench projectId="p1" />);
    await flush();
    await act(async () => { (host.querySelector('button[aria-label="用 Agent 再翻一版"]') as HTMLButtonElement).click(); });
    await flush();
    const popover = inPopover();
    const gemini = Array.from(popover.querySelectorAll('[role="radiogroup"][aria-label="Agent"] [role="radio"]'))
      .find(el => el.textContent?.includes('Gemini')) as HTMLButtonElement;
    await act(async () => { gemini.click(); });
    expect(popover.textContent).toContain('会先停掉正在跑的 Codex');
    expect(claude.startClaudeTrack).not.toHaveBeenCalled();
    const start = buttonIn(popover, '开始翻译');
    await act(async () => { start.click(); start.click(); });
    expect(skillsApi.stop).toHaveBeenCalledExactlyOnceWith('old-run');
    expect(claude.startClaudeTrack).not.toHaveBeenCalled();
    await act(async () => { finishStop(); });
    expect(claude.startClaudeTrack).toHaveBeenCalledExactlyOnceWith('p1', { harness: 'antigravity', model: '' }, '2027 数据中心');
    expect(claude.importClaudeTrack).not.toHaveBeenCalled();
  });

  it('treats a deleted old agent conversation (stop 404) as already stopped and still starts the new run', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'old-run' } });
    agentRun.current = runningAgent;
    stopAgent.mockRejectedValue(new ApiErrorWrapper('运行不存在', 404));
    claude.startClaudeTrack.mockResolvedValue({ ...runningAgent, id: 'new-run', harness: 'antigravity' });
    await render(<Workbench projectId="p1" />);
    await flush();
    await act(async () => { (host.querySelector('button[aria-label="用 Agent 再翻一版"]') as HTMLButtonElement).click(); });
    await flush();
    await act(async () => { buttonIn(inPopover(), '开始翻译').click(); });
    expect(claude.startClaudeTrack).toHaveBeenCalledTimes(1);
    expect(inPopover()?.textContent ?? '').not.toContain('运行不存在');
  });

  it('does not launch a replacement when stopping the old run fails', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'old-run' } });
    agentRun.current = runningAgent;
    stopAgent.mockRejectedValue(new Error('旧任务未停止'));
    await render(<Workbench projectId="p1" />);
    await flush();
    await act(async () => { (host.querySelector('button[aria-label="用 Agent 再翻一版"]') as HTMLButtonElement).click(); });
    await flush();
    await act(async () => { buttonIn(inPopover(), '开始翻译').click(); });
    expect(claude.startClaudeTrack).not.toHaveBeenCalled();
    // 失败写在还开着的弹框里，不弹 toast
    expect(inPopover().textContent).toContain('旧任务未停止');
    expect(toast.error).not.toHaveBeenCalled();
  });

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

    const adopt = Array.from(host.querySelectorAll('button')).find(b => b.textContent === '采用 argon 整段')!;
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
    const article = host.querySelector('[aria-label="主译本正文"]')!;
    const blocks = article.querySelectorAll('[data-reading-block]');
    expect(blocks).toHaveLength(2);
    expect(blocks[0].textContent).toContain('第一句。第二句。');
    await act(async () => { (article.querySelector('[aria-label="编辑：主译本：Second sentence."]') as HTMLElement).click(); });
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
    const button = host.querySelector('[aria-label="主译本：从这里继续阅读 — Datacenters are booming."]') as HTMLButtonElement;
    await act(async () => { button.click(); });
    await flush();
    expect(api.setReadingMark).toHaveBeenCalledWith('p1', 's1/p000');
    await render(<Workbench key="reloaded" projectId="p1" />);
    await flush();
    expect(host.querySelectorAll('[data-reading-mark="true"]')).toHaveLength(3);
    const scroll = vi.fn();
    host.querySelectorAll('[data-reading-mark="true"]').forEach(el => { el.scrollIntoView = scroll; });
    await act(async () => { (host.querySelector('button[aria-label="阅读标记"]') as HTMLButtonElement).click(); });
    await act(async () => { buttonIn(inPopover(), '继续阅读').click(); });
    expect(scroll).toHaveBeenCalledTimes(3);
    const markedButton = host.querySelector('[aria-label="主译本：从这里继续阅读 — Datacenters are booming."]') as HTMLButtonElement;
    expect(markedButton.getAttribute('aria-pressed')).toBe('true');
    expect(markedButton.title).toBe('取消“看到这里”');
    expect(markedButton.closest('[data-reading-actions]')).not.toBeNull();
    await act(async () => { markedButton.click(); });
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
    const article = host.querySelector('[aria-label="主译本正文"]')!;
    expect(article.querySelector('[aria-label="编辑：主译本：Missing part."]')?.textContent).toBe('待补译');
    await act(async () => { Array.from(article.querySelectorAll('button')).find(b => b.textContent === '用 argon 补齐本段')!.click(); });
    await flush();
    expect(api.saveText).toHaveBeenCalledTimes(1);
    expect(api.saveText).toHaveBeenCalledWith('p1', { target: 'p1', section_id: 's1', paragraph_id: 'p002', text: '另一版的后半段。' });
  });

  it('adopts one whole original paragraph with a single edge control', async () => {
    api.workbench.mockResolvedValue({ ...DATA, rows: [
      { ...DATA.rows[1], block: 'b1', source: 'First.', web: '原来的第一句。', alt: { 'p1--argon': '新版第一句。' } },
      { ...DATA.rows[1], key: 's1/p002', paragraph_id: 'p002', block: 'b1', source: 'Second.', web: '原来的第二句。', alt: { 'p1--argon': '新版第二句。' } },
    ] });
    api.saveText.mockResolvedValue({ ok: true });
    await render(<Workbench projectId="p1" />);
    await flush();
    const article = host.querySelector('[aria-label="主译本正文"]')!;
    const actions = article.querySelector('[data-reading-actions]')!;
    expect(actions).not.toBeNull();
    const adopts = Array.from(article.querySelectorAll('button')).filter(button => button.textContent?.includes('采用 argon'));
    expect(adopts).toHaveLength(1);
    expect(actions.contains(adopts[0])).toBe(true);
    expect(article.textContent).not.toContain('这段');
    await act(async () => { adopts[0].click(); });
    await flush();
    expect(api.saveText.mock.calls.map(call => call[1])).toEqual([
      { target: 'p1', section_id: 's1', paragraph_id: 'p000', text: '新版第一句。' },
      { target: 'p1', section_id: 's1', paragraph_id: 'p002', text: '新版第二句。' },
    ]);
    expect(article.textContent).toContain('新版第一句。新版第二句。');
  });

  it('explains why an incomplete comparison cannot replace a whole paragraph', async () => {
    api.workbench.mockResolvedValue({ ...DATA, rows: [
      { ...DATA.rows[1], block: 'b1', web: '已有的第一句。', alt: { 'p1--argon': '另一版的第一句。' } },
      { ...DATA.rows[1], key: 's1/p002', paragraph_id: 'p002', block: 'b1', source: 'Second.', web: '已有的第二句。' },
    ] });
    await render(<Workbench projectId="p1" />);
    await flush();
    const article = host.querySelector('[aria-label="主译本正文"]')!;
    const adopt = Array.from(article.querySelectorAll('button')).find(button => button.textContent === '采用 argon 整段')!;
    expect(adopt.disabled).toBe(true);
    expect(adopt.title).toContain('对照译文尚未完整');
    await act(async () => { adopt.click(); });
    expect(api.saveText).not.toHaveBeenCalled();
  });

  it('undoes a whole-paragraph adoption with Ctrl+Z even after clicking away', async () => {
    api.workbench.mockResolvedValue({ ...DATA, rows: [
      { ...DATA.rows[1], block: 'b1', source: 'First.', web: '原来的第一句。', alt: { 'p1--argon': '新版第一句。' } },
      { ...DATA.rows[1], key: 's1/p002', paragraph_id: 'p002', block: 'b1', source: 'Second.', web: '原来的第二句。', alt: { 'p1--argon': '新版第二句。' } },
    ] });
    api.saveText.mockResolvedValue({ ok: true });
    await render(<Workbench projectId="p1" />);
    await flush();
    const article = host.querySelector('[aria-label="主译本正文"]')!;
    await act(async () => { buttonIn(article, '采用 argon 整段').click(); });
    await flush();
    expect(article.textContent).toContain('新版第一句。新版第二句。');
    api.saveText.mockClear();

    await press(document.body, { key: 'z', ctrlKey: true });
    await act(async () => { (document.activeElement as HTMLElement | null)?.blur(); });
    await flush();
    expect(article.textContent).toContain('原来的第一句。原来的第二句。');
    expect(api.saveText.mock.calls.map(call => call[1].text).sort()).toEqual(['原来的第一句。', '原来的第二句。'].sort());

    // 再按一次重做回来
    await press(document.body, { key: 'y', ctrlKey: true });
    await act(async () => { (document.activeElement as HTMLElement | null)?.blur(); });
    await flush();
    expect(article.textContent).toContain('新版第一句。新版第二句。');
  });

  it('protects an active fragment draft from whole paragraph adoption', async () => {
    api.workbench.mockResolvedValue({ ...DATA, rows: [
      { ...DATA.rows[1], block: 'b1', source: 'First.', web: '第一句。', alt: { 'p1--argon': '对照第一句。' } },
      { ...DATA.rows[1], key: 's1/p002', paragraph_id: 'p002', block: 'b1', source: 'Second.', web: '第二句。', alt: { 'p1--argon': '对照第二句。' } },
    ] });
    api.saveText.mockResolvedValue({ ok: true });
    await render(<Workbench projectId="p1" />);
    await flush();
    const article = host.querySelector('[aria-label="主译本正文"]')!;
    await act(async () => { (article.querySelector('[aria-label="编辑：主译本：Second."]') as HTMLElement).click(); });
    await act(async () => {
      const textarea = host.querySelector('textarea')!;
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!.call(textarea, '还在编辑的草稿。');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    const adopt = Array.from(article.querySelectorAll('button')).find(button => button.textContent === '采用 argon 整段')!;
    expect(adopt.disabled).toBe(true);
    expect(adopt.title).toContain('请先完成本段编辑');
    await act(async () => { adopt.click(); });
    expect(host.querySelector('textarea')!.value).toBe('还在编辑的草稿。');
    expect(api.saveText).not.toHaveBeenCalled();
  });

  it('clears a legacy fragment bookmark by clicking its paragraph bookmark', async () => {
    api.workbench.mockResolvedValue({ ...DATA, reading_mark: { key: 's1/p002', at: '2026-10-27' }, rows: [
      { ...DATA.rows[1], block: 'b1', source: 'First.' },
      { ...DATA.rows[1], key: 's1/p002', paragraph_id: 'p002', block: 'b1', source: 'Second.' },
    ] });
    api.setReadingMark.mockResolvedValue({ ok: true, reading_mark: null });
    await render(<Workbench projectId="p1" />);
    await flush();
    const button = host.querySelector('[aria-label="主译本：从这里继续阅读 — First."]') as HTMLButtonElement;
    expect(button.getAttribute('aria-pressed')).toBe('true');
    await act(async () => { button.click(); });
    expect(api.setReadingMark).toHaveBeenCalledWith('p1', null);
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
      await act(async () => { (host.querySelector(`[aria-label="编辑：主译本：${source}"]`) as HTMLElement).click(); });
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

  it('reads the save status to screen readers, and announces paragraphs that did not save', async () => {
    api.workbench.mockResolvedValue(DATA);
    api.saveText.mockRejectedValue(new Error('离线了'));
    await render(<Workbench projectId="p1" />);
    await flush();
    const saveButton = host.querySelector('button[aria-label="保存"]') as HTMLButtonElement;
    expect(host.querySelector('[role="status"]')?.textContent).toBe(''); // 没有失败时不播报
    await act(async () => { (host.querySelector('[aria-label="编辑：主译本：Datacenters are booming."]') as HTMLElement).click(); });
    await act(async () => {
      const textarea = host.querySelector('textarea')!;
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')!.set!.call(textarea, '数据中心在爆发。');
      textarea.dispatchEvent(new Event('input', { bubbles: true }));
    });
    await act(async () => { host.querySelector('textarea')!.blur(); });
    await flush();
    const description = document.getElementById(saveButton.getAttribute('aria-describedby')!);
    expect(description?.textContent).toBe('1 段没保存上');
    expect(host.querySelector('[role="status"]')?.textContent).toBe('1 段没保存上');
  });

  it('enters an immersive mode with only the three panes, and leaves it with the corner button or Esc', async () => {
    api.workbench.mockResolvedValue(DATA);
    await render(<Workbench projectId="p1" />);
    await flush();
    expect(host.querySelector('h1')?.textContent).toBe('2027 数据中心');
    await act(async () => { (host.querySelector('button[aria-label="沉浸模式"]') as HTMLButtonElement).click(); });
    expect(host.querySelector('h1')).toBeNull();
    expect(host.querySelector('button[aria-label="保存"]')).toBeNull();
    expect(host.querySelectorAll('[data-pane-body]')).toHaveLength(3);
    // 退出按钮只在最右边那一栏
    const exit = host.querySelectorAll('button[aria-label="退出沉浸模式"]');
    expect(exit).toHaveLength(1);
    expect(host.querySelector('[data-pane="compare"]')!.contains(exit[0])).toBe(true);
    await act(async () => { (exit[0] as HTMLButtonElement).click(); });
    expect(host.querySelector('h1')).not.toBeNull();

    await act(async () => { (host.querySelector('button[aria-label="沉浸模式"]') as HTMLButtonElement).click(); });
    // 正在编辑时 Esc 只是退出编辑
    await act(async () => { (host.querySelector('[aria-label="编辑：主译本：Datacenters are booming."]') as HTMLElement).click(); });
    await press(host.querySelector('textarea')!, { key: 'Escape' });
    expect(host.querySelector('textarea')).toBeNull();
    expect(host.querySelector('h1')).toBeNull();
    await press(document.body, { key: 'Escape' });
    expect(host.querySelector('h1')).not.toBeNull();
  });

  it('says how many paragraphs an Agent version is missing instead of an import count', async () => {
    api.workbench.mockResolvedValue({ ...WITH_CODEX, rows: WITH_CODEX.rows.map(row => row.key === 's1/p000' ? { ...row, alt: { ...row.alt, 'p1--codex': null } } : row) });
    await render(<Workbench projectId="p1" />);
    await flush();
    expect(host.textContent).toContain('缺 1 段');
    expect(host.textContent).not.toContain('已导入');
    expect(buttonIn(host, '定位')).toBeTruthy();
  });

  it('copies the whole primary translation and says so on the export button', async () => {
    api.workbench.mockResolvedValue(DATA);
    api.exportMarkdown.mockResolvedValue({ filename: 'x.md', content: '# 2027 数据中心\n\n数据中心正在爆发。' });
    const write = vi.fn().mockResolvedValue(undefined);
    vi.stubGlobal('ClipboardItem', class { constructor(public items: Record<string, Promise<Blob>>) {} });
    Object.defineProperty(navigator, 'clipboard', { value: { write }, configurable: true });
    await render(<Workbench projectId="p1" />);
    await flush();
    const trigger = host.querySelector('button[aria-label="更多导出方式"]') as HTMLButtonElement;
    await act(async () => {
      trigger.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, button: 0 }));
    });
    const menu = document.body.querySelector('[role="menu"]') as HTMLElement;
    expect(menu.textContent).toContain('导出 PDF');
    expect(menu.textContent).toContain('复制为公众号格式');
    const copy = Array.from(menu.querySelectorAll('[role="menuitem"]')).find(item => item.textContent?.includes('复制全文')) as HTMLElement;
    await act(async () => { copy.click(); });
    await flush();
    expect(api.exportMarkdown).toHaveBeenCalledWith('p1', 'zh');
    const item = write.mock.calls[0][0][0] as { items: Record<string, Promise<Blob>> };
    expect(await (await item.items['text/plain']).text()).toBe('# 2027 数据中心\n\n数据中心正在爆发。');
    expect(await (await item.items['text/html']).text()).toContain('<h1>2027 数据中心</h1>');
    expect(host.textContent).toContain('已复制全文');
    vi.unstubAllGlobals();
  });

  it('keeps the previous reading mark when saving fails', async () => {
    api.workbench.mockResolvedValue({ ...DATA, reading_mark: { key: 's1/p000', at: '2026-10-27' } });
    api.setReadingMark.mockRejectedValue(new Error('离线了'));
    await render(<Workbench projectId="p1" />);
    await flush();
    await act(async () => { (host.querySelector('button[aria-label="阅读标记"]') as HTMLButtonElement).click(); });
    await act(async () => { (inPopover().querySelector('[aria-label="清除阅读标记"]') as HTMLButtonElement).click(); });
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
    const saveButton = host.querySelector('button[aria-label="保存"]') as HTMLButtonElement;
    await act(async () => { saveButton.click(); });
    await flush();
    await act(async () => { window.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true })); });
    await flush();
    // 保存状态只写在顶栏，不弹 toast
    expect(toast.success).not.toHaveBeenCalled();

    await act(async () => { (host.querySelector('button[aria-label="主译本的更多操作"]') as HTMLButtonElement).click(); });
    await act(async () => { buttonIn(inPopover(), '看我改了什么').click(); });
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
    expect(host.textContent).toContain('等你确认');
    expect(host.textContent).toContain('前不回复就按它的建议继续');
    expect(host.textContent).toContain('去确认');
    expect(claude.importClaudeTrack).not.toHaveBeenCalled();
  });

  it('keeps the primary version in the middle and swaps it with 设为主译本', async () => {
    api.workbench.mockResolvedValue(WITH_CODEX);
    await render(<Workbench projectId="p1" />);
    await flush();
    const main = () => host.querySelector('[aria-label="主译本正文"]')!;
    const compare = () => host.querySelector('[aria-label="对照正文"]')!;
    expect(main().textContent).toContain('数据中心正在爆发。');
    expect(compare().textContent).toContain('码·Datacenters are booming.'); // 对照默认是最近导入的 Codex 版
    expect(host.textContent).toContain('已完成 · gpt-5.5');
    await act(async () => { buttonIn(host, '设为主译本').click(); });
    await flush();
    expect(api.setPrimary).toHaveBeenCalledWith('p1', 'p1--codex');
    expect(main().textContent).toContain('码·Datacenters are booming.');
    expect(compare().textContent).toContain('数据中心正在爆发。');
  });

  it('locks the primary agent version while it is being re-translated', async () => {
    api.workbench.mockResolvedValue({ ...WITH_CODEX, project: { ...WITH_CODEX.project, primary: 'p1--codex', claude_run_id: 'run-2' } });
    agentRun.current = { ...runningAgent, id: 'run-2', model: 'gpt-5.5-codex' };
    await render(<Workbench projectId="p1" />);
    await flush();
    const main = host.querySelector('[aria-label="主译本正文"]')!;
    expect(main.querySelectorAll('[aria-label^="编辑："]')).toHaveLength(0);
    expect(host.textContent).toContain('重翻中 · gpt-5.5-codex · 翻完前只读');
    expect(main.textContent).not.toContain('采用');
  });

  it('retranslates an agent version with another model and warns about edits that will be replaced', async () => {
    api.workbench.mockResolvedValue(WITH_CODEX);
    api.changes.mockResolvedValue({ total: 2, changed: 2, changes: [] });
    claude.startClaudeTrack.mockResolvedValue({ ...runningAgent, id: 'new-run' });
    await render(<Workbench projectId="p1" />);
    await flush();
    await act(async () => { (host.querySelector('button[aria-label="重新翻译"]') as HTMLButtonElement).click(); });
    await flush();
    const popover = inPopover();
    expect(popover.textContent).toContain('你改过的 2 段也会被替换');
    const option = Array.from(popover.querySelectorAll('[role="radiogroup"][aria-label="模型"] [role="radio"]'))
      .find(el => el.textContent?.includes('gpt-5.5-codex')) as HTMLButtonElement;
    await act(async () => { option.click(); });
    await act(async () => { buttonIn(popover, '重新翻译').click(); });
    await flush();
    expect(claude.startClaudeTrack).toHaveBeenCalledWith('p1', { harness: 'codex', model: 'gpt-5.5-codex' }, '2027 数据中心');
  });

  it('offers 继续翻译 only for an unfinished web version, never 重新翻译', async () => {
    const partial = { ...DATA, rows: DATA.rows.map(row => row.key === 's1/p000' ? { ...row, web: null } : row) };
    api.workbench.mockResolvedValue(partial);
    api.startWorkflow.mockResolvedValue({ run_id: 'r' });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    await render(<Workbench projectId="p1" />);
    await flush();
    expect(host.querySelector('[aria-label="重新翻译"]')).toBeNull();
    expect(host.textContent).toContain('缺 1 段');
    await act(async () => { buttonIn(host, '继续翻译').click(); });
    await flush();
    expect(api.startWorkflow).toHaveBeenCalledWith('p1', { model: undefined, autoAcceptTerms: true, sectionIds: ['s1'] });
  });

  it('does not import a draft that does not match the download until asked to', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'run-3' } });
    agentRun.current = { ...runningAgent, id: 'run-3', status: 'idle' };
    claude.importClaudeTrack
      .mockRejectedValueOnce(new AlignmentTooLow('Agent 的英文稿只对上 1/3 段，可能不是这篇下载的原文'))
      .mockResolvedValueOnce({ variant_id: 'p1--codex', aligned: 3, unaligned: 0 });
    await render(<Workbench projectId="p1" />);
    await flush();
    expect(host.textContent).toContain('没导入：Agent 的英文稿只对上 1/3 段');
    await act(async () => { buttonIn(host, '仍然导入').click(); });
    await flush();
    expect(claude.importClaudeTrack).toHaveBeenLastCalledWith('p1', agentRun.current, true);
  });

  it('offers an agent right in the compare column when there is nothing to compare', async () => {
    api.workbench.mockResolvedValue({ ...DATA, variants: [] });
    await render(<Workbench projectId="p1" />);
    await flush();
    const compare = host.querySelector('[aria-label="对照正文"]')!;
    expect(compare.textContent).toContain('选一个 Agent 翻这篇');
    expect(buttonIn(compare, '开始翻译')).toBeDefined();
  });

  it('cross-fades the two columns when the primary is swapped, but not when switching compare tabs', async () => {
    const animate = vi.fn();
    // jsdom 没有 Web Animations
    Object.defineProperty(HTMLElement.prototype, 'animate', { value: animate, configurable: true });
    try {
      api.workbench.mockResolvedValue(WITH_CODEX);
      await render(<Workbench projectId="p1" />);
      await flush();
      expect(animate).not.toHaveBeenCalled();
      const tabs = Array.from(host.querySelectorAll('[role="tablist"][aria-label="对照版本"] [role="tab"]'));
      expect(tabs.map(tab => tab.textContent)).toEqual(['Codex', 'argon']);
      expect(host.querySelector('[role="tablist"] button[aria-label="用 Agent 再翻一版"]')).toBeNull(); // ＋ 不是标签
      await act(async () => { (tabs[1] as HTMLElement).click(); });
      await flush();
      expect(host.querySelector('[aria-label="对照正文"]')!.textContent).toContain('前言');
      expect(animate).not.toHaveBeenCalled();
      await act(async () => { buttonIn(host, '设为主译本').click(); });
      await flush();
      expect(animate).toHaveBeenCalledTimes(2);
    } finally {
      delete (HTMLElement.prototype as { animate?: unknown }).animate;
    }
  });

  it('rolls back and reports when saving the primary fails, and exports the new primary after a swap', async () => {
    api.workbench.mockResolvedValue(WITH_CODEX);
    api.setPrimary.mockRejectedValueOnce(new Error('存不上'));
    api.exportMarkdown.mockResolvedValue({ filename: 'x.md', content: 'c' });
    await render(<Workbench projectId="p1" />);
    await flush();
    const main = () => host.querySelector('[aria-label="主译本正文"]')!;
    await act(async () => { buttonIn(host, '设为主译本').click(); });
    await flush();
    expect(toast.error).toHaveBeenCalledWith('存不上');
    expect(main().textContent).toContain('数据中心正在爆发。');
    await act(async () => { buttonIn(host, '设为主译本').click(); });
    await flush();
    expect(main().textContent).toContain('码·Datacenters are booming.');
    await act(async () => { buttonIn(host, '导出主译本').click(); });
    await flush();
    expect(api.exportMarkdown).toHaveBeenCalledWith('p1--codex', 'zh');
  });

  it('hides ＋ once all three agents have a version', async () => {
    const mk = (id: string, label: string, agent: 'claude' | 'codex' | 'antigravity') => ({
      id, kind: 'claude' as const, label, title_translation: null, progress: { total: 2, approved: 0 },
      status: { active: false, run_id: null, status: null, current_step: null, translated: 2, total: 2, error: null },
      import: { run_id: `r-${agent}`, agent, model: null, aligned: 2, unaligned: 0, merged_blocks: 0, imported_at: '2026-10-28T10:00:00' },
    });
    api.workbench.mockResolvedValue({ ...DATA, variants: [mk('p1--claude', 'Claude', 'claude'), mk('p1--codex', 'Codex', 'codex'), mk('p1--antigravity', 'Gemini', 'antigravity')] });
    await render(<Workbench projectId="p1" />);
    await flush();
    expect(host.querySelector('button[aria-label="用 Agent 再翻一版"]')).toBeNull();
  });

  it('auto-imports an idle agent run exactly once, without force, across refetches', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'run-5' } });
    agentRun.current = { ...runningAgent, id: 'run-5', status: 'idle' };
    claude.importClaudeTrack.mockResolvedValue({ variant_id: 'p1--codex', aligned: 3, unaligned: 0 });
    await render(<Workbench projectId="p1" />);
    await flush();
    await flush();
    expect(claude.importClaudeTrack).toHaveBeenCalledExactlyOnceWith('p1', agentRun.current, false);
    expect(toast.success).not.toHaveBeenCalled();
  });

  it('imports again when the same run works some more and goes idle again', async () => {
    const withImport = { ...WITH_CODEX, project: { ...WITH_CODEX.project, claude_run_id: 'run-6' },
      variants: WITH_CODEX.variants.map(v => v.id === 'p1--codex' ? { ...v, import: { ...v.import!, run_id: 'run-6' } } : v) };
    api.workbench.mockResolvedValue(withImport);
    claude.importClaudeTrack.mockResolvedValue({ variant_id: 'p1--codex', aligned: 3, unaligned: 0 });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const again = () => act(async () => {
      root.render(<QueryClientProvider client={client}><MemoryRouter><Workbench projectId="p1" /></MemoryRouter></QueryClientProvider>);
    });
    agentRun.current = { ...runningAgent, id: 'run-6', status: 'idle' };
    await again(); await flush();
    expect(claude.importClaudeTrack).not.toHaveBeenCalled(); // 这一轮已经导入过
    agentRun.current = { ...runningAgent, id: 'run-6', status: 'running' };
    await again(); await flush();
    agentRun.current = { ...runningAgent, id: 'run-6', status: 'idle' };
    await again(); await flush();
    await again(); await flush();
    expect(claude.importClaudeTrack).toHaveBeenCalledExactlyOnceWith('p1', agentRun.current, false);
  });

  it('clears a stale import problem once the agent runs again', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'run-7' } });
    claude.importClaudeTrack.mockRejectedValueOnce(new Error('没找到同一目录下的 zh.md 和 en.md')).mockResolvedValue({ variant_id: 'p1--codex', aligned: 3, unaligned: 0 });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const again = () => act(async () => {
      root.render(<QueryClientProvider client={client}><MemoryRouter><Workbench projectId="p1" /></MemoryRouter></QueryClientProvider>);
    });
    agentRun.current = { ...runningAgent, id: 'run-7', status: 'idle' };
    await again(); await flush();
    expect(host.textContent).toContain('没导入：没找到同一目录下的 zh.md');
    agentRun.current = { ...runningAgent, id: 'run-7', status: 'running' };
    await again(); await flush();
    expect(host.textContent).not.toContain('没导入');
    agentRun.current = { ...runningAgent, id: 'run-7', status: 'idle' };
    await again(); await flush();
    expect(claude.importClaudeTrack).toHaveBeenCalledTimes(2);
  });

  it('forces the import only once on a double click', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'run-8' } });
    agentRun.current = { ...runningAgent, id: 'run-8', status: 'idle' };
    let finish!: () => void;
    claude.importClaudeTrack
      .mockRejectedValueOnce(new AlignmentTooLow('只对上 1/3 段'))
      .mockImplementationOnce(() => new Promise(resolve => { finish = () => resolve({ variant_id: 'p1--codex', aligned: 3, unaligned: 0 }); }));
    await render(<Workbench projectId="p1" />);
    await flush();
    const force = buttonIn(host, '仍然导入');
    await act(async () => { force.click(); force.click(); });
    expect(claude.importClaudeTrack).toHaveBeenCalledTimes(2);
    expect(host.textContent).toContain('正在导入');
    await act(async () => { finish(); });
  });

  it('shows one message for a column whose agent version has no text yet', async () => {
    api.workbench.mockResolvedValue({ ...DATA, project: { ...DATA.project, claude_run_id: 'run-9' }, variants: [] });
    agentRun.current = { ...runningAgent, id: 'run-9', status: 'running' };
    await render(<Workbench projectId="p1" />);
    await flush();
    const compare = host.querySelector('[aria-label="对照正文"]')!;
    expect(compare.querySelectorAll('[aria-label^="编辑："]')).toHaveLength(0);
    expect(compare.textContent).toContain('译文还没出来');
  });

  it('shows no mark text for a stale reading-mark key', async () => {
    api.workbench.mockResolvedValue({ ...DATA, reading_mark: { key: 'gone/p9', at: '2026-10-27' } });
    await render(<Workbench projectId="p1" />);
    await flush();
    expect(host.querySelector('button[aria-label="阅读标记"]')).toBeNull();
  });
});
