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

const section = (title: string) => host.querySelector<HTMLElement>(`section[aria-label="${title}"]`);
const thread = (over: Partial<SlackActivityItem>, i: number): SlackActivityItem => ({
  type: 'thread', channel_id: 'C1', channel_name: 'social-media-posts-and-media', thread_ts: `17946000${i}.000001`,
  root: message({ text: `Topic ${i}`, user_name: 'Sam H' }), reply_count: 3, participants: ['Sam H'], last: null,
  latest_ts: `17946000${i}.000001`, latest_time: '', has_unreads: false, mentions_me: false, ...over,
});
const render = (props: Partial<Parameters<typeof ActivityList>[0]> = {}) => act(async () => root.render(
  <ActivityList selection={null} view={null} onOpen={vi.fn()} onSelectView={vi.fn()} {...props} />));

it('groups rows into @me / DMs / new posts / my threads / others, each item once', async () => {
  localStorage.clear();
  items.push(
    thread({ root: message({ text: 'Fresh post to translate', user_name: 'Doug O' }), reply_count: 0, has_unreads: true }, 10),
    thread({ root: message({ text: 'My own thread', user_name: 'felix' }), following: true }, 11),
  );
  const onOpen = vi.fn();
  await render({ onOpen });
  expect(Array.from(host.querySelectorAll('section')).map(s => s.getAttribute('aria-label')))
    .toEqual(['@我', '私信', '新帖 · 待翻译', '我参与的 thread']);  // 空的组不显示

  const mention = section('@我')!;
  expect(mention.textContent).toContain('Elon post 🔥');            // 根消息第一行原文
  expect(mention.textContent).not.toContain('@用户组');
  expect(mention.textContent).not.toContain('second line');
  expect(mention.textContent).toContain('Reyk Knuhtsen 发起 · 17 条回复 · 3 人参与');
  expect(mention.textContent).toContain('Daksh Malik：@Felix Zhou');
  expect(mention.textContent).toContain('thread');                  // @我 组里写明类型
  expect(mention.textContent).toContain('1 未读');
  expect(section('私信')!.textContent).toContain('Michelle Shen');
  expect(section('新帖 · 待翻译')!.textContent).toContain('Doug O 发帖 · 还没人回复');
  expect(section('我参与的 thread')!.textContent).toContain('My own thread');

  await act(async () => Array.from(mention.querySelectorAll('button')).find(b => b.textContent?.includes('Elon post'))!.click());
  expect(onOpen).toHaveBeenCalledWith(items[0]);
});

it('shows 5 other threads until expanded, remembers collapsed groups, marks one group read', async () => {
  localStorage.clear();
  for (let i = 0; i < 7; i++) items.push(thread({ has_unreads: i < 2 }, 20 + i));
  await render();
  const others = () => section('其他 thread')!;
  const otherRows = () => Array.from(others().querySelectorAll('button')).filter(b => b.textContent?.includes('Topic'));
  expect(otherRows()).toHaveLength(5);
  const more = Array.from(others().querySelectorAll('button')).find(b => b.textContent === '展开其余 2 条')!;
  await act(async () => more.click());
  expect(otherRows()).toHaveLength(7);

  await act(async () => Array.from(others().querySelectorAll('button')).find(b => b.textContent === '全部已读')!.click());
  expect(markAll).toHaveBeenLastCalledWith([
    { channel_id: 'C1', ts: '1794600020.000001', thread_ts: '1794600020.000001' },
    { channel_id: 'C1', ts: '1794600021.000001', thread_ts: '1794600021.000001' },
  ]);

  await act(async () => others().querySelector<HTMLButtonElement>('button[aria-expanded]')!.click());
  expect(otherRows()).toHaveLength(0);
  expect(JSON.parse(localStorage.getItem('slack-sidebar-collapsed')!)).toEqual(['others']);
});

it('tool rows open the digest and the reply workbench', async () => {
  const onSelectView = vi.fn();
  await render({ onSelectView });
  const tool = (label: string) => Array.from(host.querySelectorAll('button')).find(b => b.textContent?.startsWith(label))!;
  expect(tool('AI 速览').textContent).toContain('1 条未读整理成中文');
  await act(async () => tool('AI 速览').click());
  expect(onSelectView).toHaveBeenLastCalledWith('digest');
  await act(async () => tool('回复工作台').click());
  expect(onSelectView).toHaveBeenLastCalledWith('reply');
});

it('j / k walk the groups top to bottom, Esc goes back, typing is ignored', async () => {
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
