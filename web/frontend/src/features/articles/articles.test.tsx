// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { EditableText } from './components/EditableText';
import { Workbench } from './components/Workbench';
import { SAVE_DELAY_MS, unsavedEdits } from './lib/edits';
import { importAndTranslate } from './lib/importFlow';
import { SECOND_MODELS } from './lib/tracks';
import type { Workbench as WorkbenchData } from './types';

const api = vi.hoisted(() => ({
  workbench: vi.fn(),
  saveText: vi.fn(),
  startWorkflow: vi.fn(),
  createModelVariant: vi.fn(),
  exportMarkdown: vi.fn(),
  setClaudeRun: vi.fn(),
  sourceHtml: vi.fn(),
}));
const substack = vi.hoisted(() => ({ importArticle: vi.fn() }));
const claude = vi.hoisted(() => ({ startClaudeTrack: vi.fn(), importClaudeTrack: vi.fn() }));
vi.mock('./api', () => ({ articlesApi: api, downloadText: vi.fn() }));
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
    expect(host.textContent).toContain('已保存');
    expect(unsavedEdits.any()).toBe(false);
  });
});

describe('importAndTranslate', () => {
  it('imports, starts the web track, then a model second version with terms auto-accepted', async () => {
    substack.importArticle.mockResolvedValue({ project: { id: 'p1' }, already_imported: false });
    api.createModelVariant.mockResolvedValue({ variant_id: 'p1--argon' });
    api.startWorkflow.mockResolvedValue({ run_id: 'r' });

    await expect(importAndTranslate({ url: 'u' }, 'model', SECOND_MODELS[0], vi.fn())).resolves.toBe('p1');

    expect(api.startWorkflow.mock.calls).toEqual([
      ['p1'],
      ['p1--argon', { model: 'gemini-official-argon', autoAcceptTerms: true }],
    ]);
  });

  it('still opens the article when the second version cannot start', async () => {
    substack.importArticle.mockResolvedValue({ project: { id: 'p1' }, already_imported: true });
    claude.startClaudeTrack.mockRejectedValue(new Error('skill-runner 挂了'));
    const notify = vi.fn();

    await expect(importAndTranslate({ url: 'u' }, 'claude', SECOND_MODELS[0], notify)).resolves.toBe('p1');

    expect(api.startWorkflow).not.toHaveBeenCalled(); // 已导入过的不重复开翻
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
  ],
};

describe('Workbench', () => {
  it('lines up English and both translations, collapses a pane and saves into the right project', async () => {
    api.workbench.mockResolvedValue(DATA);
    api.saveText.mockResolvedValue({ ok: true });
    await render(<Workbench projectId="p1" />);
    await flush();

    expect(host.textContent).toContain('2027 数据中心');
    expect(host.textContent).toContain('Datacenters are booming.');
    const areas = Array.from(host.querySelectorAll('textarea'));
    expect(areas.map(area => area.value)).toEqual(['引言', '前言', '数据中心正在爆发。', '']);

    const collapse = host.querySelector('button[aria-label="收起英文"]') as HTMLButtonElement;
    await act(async () => { collapse.click(); });
    expect(host.querySelector('button[aria-label="展开英文"]')).not.toBeNull();
    expect(host.textContent).not.toContain('Datacenters are booming.');

    const adopt = Array.from(host.querySelectorAll('button')).find(b => b.textContent === '用argon这段')!;
    await act(async () => { adopt.click(); });
    await flush();
    expect(api.saveText).toHaveBeenCalledWith('p1', { target: 'p1', section_id: 's1', paragraph_id: null, text: '前言' });
  });
});
