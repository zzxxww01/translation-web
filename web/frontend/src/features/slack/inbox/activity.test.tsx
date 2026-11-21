// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import type { SlackActivityItem, SlackMessage } from './types';

const items: SlackActivityItem[] = [];
vi.mock('./hooks', () => ({
  useSlackActivity: () => ({ data: items, isLoading: false, isError: false }),
  useMarkAllRead: () => ({ mutate: markAll, isPending: false }),
}));
const markAll = vi.fn();
vi.mock('../agent/agentRuns', () => ({ useSlackAgentRuns: () => new Map() }));

const { ActivityList } = await import('./ActivityList');
const { Overview } = await import('./Overview');

const message = (over: Partial<SlackMessage>): SlackMessage => ({
  ts: '1794963980.687079', time: '', user_id: 'U1', user_name: 'Daksh Malik', is_me: false, mentions_me: false,
  subtype: null, segments: [], text: '', thread_ts: null, reply_count: 0, latest_reply: null, edited: false,
  files: [], attachments: [], reactions: [], permalink: '', ...over,
} as SlackMessage);


let host: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  host = document.createElement('div');
  root = createRoot(host);
  items.splice(0, items.length,
    {
      type: 'thread', channel_id: 'C1', channel_name: 'social-media-posts-and-media', thread_ts: '1794610284.466519',
      root: message({ text: '@用户组 *Elon post* :fire:\nsecond line', user_name: 'Reyk Knuhtsen' }), reply_count: 17,
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
const tab = (label: RegExp) => Array.from(host.querySelectorAll<HTMLButtonElement>('[role="tab"]')).find(b => label.test(b.textContent ?? ''))!;
const thread = (over: Partial<SlackActivityItem>, i: number): SlackActivityItem => ({
  type: 'thread', channel_id: 'C1', channel_name: 'social-media-posts-and-media', thread_ts: `17946000${i}.000001`,
  root: message({ text: `Topic ${i}`, user_name: 'Sam H' }), reply_count: 3, participants: ['Sam H'], last: null,
  latest_ts: `17946000${i}.000001`, latest_time: '', has_unreads: false, mentions_me: false, ...over,
});
const render = (props: Partial<Parameters<typeof ActivityList>[0]> = {}) => act(async () => root.render(
  <ActivityList selection={null} view={null} onOpen={vi.fn()} onSelectView={vi.fn()} {...props} />));

it('lists everything by time with the original first line and who is talking', async () => {
  localStorage.clear();
  const onOpen = vi.fn();
  await render({ onOpen });
  const [first, dm] = rows();
  expect(first.textContent).toContain('Elon post 🔥');           // 根消息第一行原文，不翻译
  expect(first.textContent).not.toContain('@用户组');
  expect(first.textContent).not.toContain('social-media-posts');  // 只有一个频道时不重复写频道名
  expect(first.textContent).not.toContain('second line');
  expect(first.textContent).toContain('Reyk Knuhtsen 发起 · 17 条回复 · 3 人参与');
  expect(first.textContent).toContain('Daksh Malik：@Felix Zhou');
  expect(first.textContent).toContain('@我');
  expect(dm.textContent).toContain('Michelle Shen');
  expect(dm.textContent).toContain('私信');
  await act(async () => first.click());
  expect(onOpen).toHaveBeenCalledWith(items[0]);
});

it('one row of filters: unread / @me / DMs / new posts / my threads, remembered', async () => {
  localStorage.clear();
  items.push(
    thread({ root: message({ text: 'Fresh post to translate', user_name: 'Doug O' }), reply_count: 0, has_unreads: true }, 10),
    thread({ root: message({ text: 'My own thread', user_name: 'felix' }), following: true }, 11),
  );
  await render();
  expect(Array.from(host.querySelectorAll('[role="tab"]')).map(t => t.textContent))
    .toEqual(['全部', '未读 2', '@我 1', '私信', '新帖 1', '我参与的']);
  await act(async () => tab(/^未读/).click());
  expect(rows().map(r => r.textContent?.includes('Elon') || r.textContent?.includes('Fresh'))).toEqual([true, true]);
  await act(async () => tab(/^私信/).click());
  expect(rows()).toHaveLength(1);
  await act(async () => tab(/^新帖/).click());
  expect(rows()[0].textContent).toContain('Doug O 发帖 · 还没人回复');
  await act(async () => tab(/^我参与的/).click());
  expect(rows()).toHaveLength(1);
  expect(rows()[0].textContent).toContain('My own thread');
  expect(localStorage.getItem('slack-activity-filter')).toBe('following');
});

it('AI digest row opens the digest', async () => {
  const onSelectView = vi.fn();
  await render({ onSelectView });
  const digest = Array.from(host.querySelectorAll('button')).find(b => b.textContent?.startsWith('AI 速览'))!;
  expect(digest.textContent).toContain('把 1 处未读整理成中文要点');
  await act(async () => digest.click());
  expect(onSelectView).toHaveBeenLastCalledWith('digest');
  expect(host.textContent).not.toContain('回复工作台');  // 旧版工作台收在「⋯」里
  expect(host.querySelector('[aria-label="更多"]')).not.toBeNull();
});

it('j / k walk the current list, Esc goes back, typing is ignored', async () => {
  localStorage.clear();
  const onOpen = vi.fn();
  const onBack = vi.fn();
  const press = (key: string) => window.dispatchEvent(new KeyboardEvent('keydown', { key }));
  await render({ onOpen, onBack });
  await act(async () => press('j'));
  expect(onOpen).toHaveBeenLastCalledWith(items[0]);
  await render({ onOpen, onBack, selection: { channelId: 'C1', threadTs: '1794610284.466519' } });
  await act(async () => press('j'));
  expect(onOpen).toHaveBeenLastCalledWith(items[1]);
  await render({ onOpen, onBack, selection: { channelId: 'D1', threadTs: null } });
  await act(async () => press('k'));
  expect(onOpen).toHaveBeenLastCalledWith(items[0]);
  await act(async () => press('Escape'));
  expect(onBack).toHaveBeenCalled();

  const input = document.createElement('input');
  host.appendChild(input);
  const calls = onOpen.mock.calls.length;
  await act(async () => input.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', bubbles: true })));
  expect(onOpen.mock.calls.length).toBe(calls);
});

it('overview counts unread / @me and lists what to read first', async () => {
  const onOpen = vi.fn();
  await act(async () => root.render(<Overview onOpen={onOpen} onDigest={vi.fn()} />));
  expect(host.textContent).toContain('未读1');
  expect(host.textContent).toContain('@我1');
  const first = host.querySelector<HTMLButtonElement>('ul button')!;
  expect(first.textContent).toContain('Elon post');
  await act(async () => first.click());
  expect(onOpen).toHaveBeenCalledWith(items[0]);
});
