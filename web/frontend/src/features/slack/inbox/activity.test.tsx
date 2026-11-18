// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import type { SlackActivityItem, SlackMessage, SlackStatus } from './types';

const items: SlackActivityItem[] = [];
vi.mock('./hooks', () => ({
  useSlackActivity: () => ({ data: items, isLoading: false, isError: false }),
  useRefreshSlack: () => ({ mutate: vi.fn(), isPending: false }),
}));
vi.mock('../agent/agentRuns', () => ({ useSlackAgentRuns: () => new Map() }));

const { ActivityList } = await import('./ActivityList');

const message = (over: Partial<SlackMessage>): SlackMessage => ({
  ts: '1794963980.687079', time: '', user_id: 'U1', user_name: 'Daksh Malik', is_me: false, mentions_me: false,
  subtype: null, segments: [], text: '', thread_ts: null, reply_count: 0, latest_reply: null, edited: false,
  files: [], attachments: [], reactions: [], permalink: '', ...over,
} as SlackMessage);

const status = { ok: true, configured: true, user: 'felix', team: 'SemiAnalysis' } as SlackStatus;

let host: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  host = document.createElement('div');
  root = createRoot(host);
  items.splice(0, items.length,
    {
      type: 'thread', channel_id: 'C1', channel_name: 'social-media-posts-and-media', thread_ts: '1794610284.466519',
      root: message({ text: '*Elon post* :fire:\nsecond line', user_name: 'Reyk Knuhtsen' }), reply_count: 17,
      participants: ['Reyk Knuhtsen', 'Daksh Malik', 'Computer'], last: message({ text: '@Felix Zhou' }),
      latest_ts: '1794963980.687079', latest_time: '', has_unreads: true, mentions_me: true,
    },
    {
      type: 'dm', channel_id: 'D1', channel_name: 'Michelle Shen', kind: 'im', thread_ts: null,
      last: message({ text: 'I want to include into a presentation', user_name: 'Michelle Shen' }),
      latest_ts: '1794590000.000000', latest_time: '', has_unreads: false, mentions_me: false,
    },
  );
});
afterEach(async () => {
  await act(async () => root.unmount());
  vi.unstubAllGlobals();
});

const rows = () => Array.from(host.querySelectorAll<HTMLButtonElement>('[aria-label="Slack 动态"] > button'));

it('shows one row per thread / DM with the original first line and who is talking', async () => {
  const onOpen = vi.fn();
  await act(async () => root.render(
    <ActivityList status={status} selection={null} view={null} onOpen={onOpen} onSelectView={vi.fn()} onSearch={vi.fn()} />));
  const [thread, dm] = rows();
  expect(thread.textContent).toContain('Elon post 🔥');           // 根消息第一行原文，不翻译
  expect(thread.textContent).not.toContain('second line');
  expect(thread.textContent).toContain('Reyk Knuhtsen 发起 · 17 条回复 · 3 人参与');
  expect(thread.textContent).toContain('Daksh Malik：@Felix Zhou');
  expect(thread.textContent).toContain('@我');
  expect(dm.textContent).toContain('Michelle Shen');
  expect(dm.textContent).toContain('私信');

  await act(async () => thread.click());
  expect(onOpen).toHaveBeenCalledWith(items[0]);
});

it('filters to @me and to DMs', async () => {
  await act(async () => root.render(
    <ActivityList status={status} selection={null} view={null} onOpen={vi.fn()} onSelectView={vi.fn()} onSearch={vi.fn()} />));
  const tab = (label: RegExp) => Array.from(host.querySelectorAll<HTMLButtonElement>('[role="tab"]')).find(b => label.test(b.textContent ?? ''))!;
  await act(async () => tab(/^@我/).click());
  expect(rows()).toHaveLength(1);
  expect(rows()[0].textContent).toContain('Elon post');
  await act(async () => tab(/^私信/).click());
  expect(rows()).toHaveLength(1);
  expect(rows()[0].textContent).toContain('Michelle Shen');
});
