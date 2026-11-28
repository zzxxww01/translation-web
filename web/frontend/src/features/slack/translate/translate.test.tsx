// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';

const api = vi.hoisted(() => ({ slack: vi.fn(), runSlack: vi.fn(), setSent: vi.fn(), imagesZipUrl: vi.fn() }));
const storeState = vi.hoisted(() => ({ loadSnapshot: vi.fn(), setOriginalText: vi.fn(), draftId: 'd1', draftRev: 1 }));

vi.mock('@/features/post/drafts', async importOriginal => ({
  ...(await importOriginal<object>()),
  draftsApi: api,
  useDraftSync: () => ({ flush: async () => {}, schedule: () => {}, markLoaded: () => {}, saving: false, savedAt: null }),
}));
vi.mock('@/shared/stores/postStore', () => ({
  createPostStore: () => Object.assign((select: (s: typeof storeState) => unknown) => select(storeState), { getState: () => storeState }),
}));
vi.mock('@/features/post/usePostWorkspace', () => ({
  usePostWorkspace: () => ({ originalText: 'Hello', setOriginalText: vi.fn(), versions: [{}], currentVersion: null, isLoading: false,
    generatedTitles: [], selectedTitle: '', currentContent: '', selectedModel: undefined, setSelectedModel: vi.fn() }),
}));
vi.mock('@/features/post', () => ({ WorkColumn: () => null }));
vi.mock('@/features/post/components/WorkspaceChrome', () => ({ DiscardEditDialog: () => null, PendingChip: () => null, SaveState: () => null }));
vi.mock('@/components/ModelSelector', () => ({ ModelSelector: () => null }));
vi.mock('@/components/layout/ResizablePanes', () => ({
  ResizablePanes: ({ panes }: { panes: { id: string; content: ReactNode }[] }) => <div>{panes.map(p => <div key={p.id}>{p.content}</div>)}</div>,
}));
vi.mock('../inbox/MessageItem', () => ({ MessageItem: () => null }));
vi.mock('../inbox/hooks', () => ({
  // 原帖最后一条比提取时的新：显示「原帖后来又有更新」
  useSlackReplies: () => ({ isLoading: false, data: { messages: [{ ts: '1.0', text: 'root', files: [] }, { ts: '5.0', text: 'v2', files: [] }] } }),
}));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() } }));

import { SlackTranslateMode } from './SlackTranslateMode';

const draft = (latest: string) => ({
  id: 'd1', rev: 1, images: [], status: 'draft', sent_at: null, state: {}, slack: { channel_id: 'C1', thread_ts: '1.0', title: 'Post' },
  extraction: { has_post: true, note: '', message_ts: ['1.0'], candidates: [], latest_ts: latest, instruction: '', extracted_at: 0 },
  send_time: { shanghai: '2026-11-29T23:00:00+08:00', shanghai_label: '11月29日 周日 23:00', date_only: false,
    source_local: '2026-11-29 09:00', source_label: '美中', text: 'post tmw 9am', tz_assumed: true },
});

let host: HTMLDivElement;
let root: Root;
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  host = document.createElement('div');
  document.body.appendChild(host);
  root = createRoot(host);
});
afterEach(async () => {
  await act(async () => root.unmount());
  host.remove();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

const flush = () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
const button = (text: string) => Array.from(host.querySelectorAll('button')).find(b => b.textContent?.trim() === text);

it('re-picks once however often it is clicked, and shows that it is running', async () => {
  api.slack.mockResolvedValue({ draft: draft('1.0'), running: false });
  let resolve!: (value: unknown) => void;
  api.runSlack.mockReturnValue(new Promise(r => { resolve = r; }));
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await act(async () => root.render(
    <QueryClientProvider client={client}><SlackTranslateMode channelId="C1" threadTs="1.0" channelName="x" onExit={() => {}} /></QueryClientProvider>,
  ));
  await flush();
  await flush();
  expect(host.textContent).toContain('原帖后来又有更新');
  // 建议发送时间：换成上海时间放在顶栏，悬停看原话和按什么时区算的
  const chip = Array.from(host.querySelectorAll('span')).find(el => el.textContent?.startsWith('建议发送'))!;
  expect(chip.textContent).toBe('建议发送：11月29日 周日 23:00（上海）');
  expect(chip.title).toContain('没写时区，按美中时间算');

  await act(async () => button('重新挑')!.click());
  await flush();
  // 点了马上看得到在跑；提示里的按钮收起来，没法再点
  expect(host.querySelector('[role="status"]')?.textContent).toContain('正在重新挑选和翻译');
  expect(button('重新挑')).toBeUndefined();
  await act(async () => button('挑错了？让 AI 重新挑')!.click());
  const again = Array.from(host.querySelectorAll('button')).find(b => b.textContent?.includes('正在挑'))!;
  expect(again.disabled).toBe(true);
  await act(async () => again.click());
  expect(api.runSlack).toHaveBeenCalledTimes(1);

  await act(async () => resolve(draft('5.0')));
  await flush();
  expect(host.querySelector('[role="status"]')).toBeNull();
  expect(host.textContent).not.toContain('原帖后来又有更新');
});

it('shows a run started elsewhere and does not start another', async () => {
  api.slack.mockResolvedValue({ draft: null, running: true });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await act(async () => root.render(
    <QueryClientProvider client={client}><SlackTranslateMode channelId="C1" threadTs="2.0" channelName="x" onExit={() => {}} /></QueryClientProvider>,
  ));
  await flush();
  expect(host.textContent).toContain('正在从 Slack 原帖里找出要发的帖子');
  expect(api.runSlack).not.toHaveBeenCalled();
});
