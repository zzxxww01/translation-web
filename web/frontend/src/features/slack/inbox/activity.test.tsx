// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import type { SlackActivityItem, SlackMessage, SlackTodos } from './types';

const items: SlackActivityItem[] = [];
const markAll = vi.fn();
const saveSettings = vi.fn();
const todos: { data: SlackTodos } = { data: { items: [], fyi: [] } };
vi.mock('./hooks', () => ({
  useSlackActivity: () => ({ data: items, isLoading: false, isError: false }),
  useMarkAllRead: () => ({ mutate: markAll, isPending: false }),
  useTodos: () => ({ ...todos, isLoading: false, isError: false, isFetching: false, refetch: vi.fn() }),
  useSlackSettings: () => ({ data: { auto_translate_mentions: true } }),
  useSaveSlackSettings: () => ({ mutate: saveSettings }),
}));

const { ActivityList } = await import('./ActivityList');
const { TodoView } = await import('./TodoView');

const message = (over: Partial<SlackMessage>): SlackMessage => ({
  ts: '1794963980.687079', time: '', user_id: 'U1', user_name: 'Daksh Malik', is_me: false, mentions_me: false,
  subtype: null, segments: [], text: '', thread_ts: null, reply_count: 0, latest_reply: null, edited: false,
  files: [], attachments: [], reactions: [], permalink: '', ...over,
} as SlackMessage);

let host: HTMLDivElement;
let root: ReturnType<typeof createRoot>;
beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  localStorage.clear();
  host = document.createElement('div');
  root = createRoot(host);
  items.splice(0, items.length,
    {
      type: 'thread', channel_id: 'C1', channel_name: 'social-media-posts-and-media', thread_ts: '1794610284.466519',
      root: message({ text: '@用户组 *Elon post* :fire:\nsecond line', user_name: 'Reyk Knuhtsen' }), reply_count: 17,
      participants: ['Reyk Knuhtsen', 'Daksh Malik', 'Computer'], last: message({ text: '@Felix Zhou' }),
      latest_ts: '1794963980.687079', latest_time: '', has_unreads: true, mentions_me: true,
      draft: { id: 's_x', status: 'draft', auto: true, seen: false, versions: 1, no_post: false },
    },
    {
      type: 'dm', channel_id: 'D1', channel_name: 'Michelle Shen', kind: 'im', thread_ts: null,
      last: message({ text: 'I want to include into a presentation', user_name: 'Michelle Shen' }),
      latest_ts: '1794590000.000000', latest_time: '', has_unreads: false, mentions_me: false,
    },
  );
  todos.data = { items: [], fyi: [] };
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
  <ActivityList selection={null} onOpen={vi.fn()} onShowTodos={vi.fn()} onShowHistory={vi.fn()} todosActive={false} {...props} />));

it('lists everything by time with the original first line, who is talking and the draft state', async () => {
  const onOpen = vi.fn();
  await render({ onOpen });
  const [first, dm] = rows();
  expect(first.textContent).toContain('Elon post 🔥');           // 根消息第一行原文，不翻译
  expect(first.textContent).not.toContain('@用户组');
  expect(first.textContent).not.toContain('social-media-posts');  // 只有一个频道时不重复写频道名
  expect(first.textContent).not.toContain('second line');
  expect(first.textContent).toContain('Reyk Knuhtsen 发起 · 17 条回复');
  expect(first.textContent).toContain('@我');
  expect(first.getAttribute('title')).toContain('自动翻好');      // 后台自动翻好的帖子：只是底色变一点，没有彩色标签
  expect(first.textContent).toContain('翻译草稿');
  expect(dm.textContent).toContain('Michelle Shen');
  expect(dm.textContent).toContain('私信');
  await act(async () => first.click());
  expect(onOpen).toHaveBeenCalledWith(items[0]);
});

it('one row of filters with unread counts, remembered; unread view has mark-all', async () => {
  items.push(
    thread({ root: message({ text: 'Fresh post to translate', user_name: 'Doug O' }), reply_count: 0, has_unreads: true }, 10),
    thread({ root: message({ text: 'My own thread', user_name: 'felix' }), following: true }, 11),
  );
  await render();
  expect(Array.from(host.querySelectorAll('[role="tab"]')).map(t => t.textContent))
    .toEqual(['全部', '未读2', '@我1', '私信', '新帖1', '我参与的', '我翻译的1']);
  await act(async () => tab(/^未读/).click());
  expect(rows().map(r => r.textContent?.includes('Elon') || r.textContent?.includes('Fresh'))).toEqual([true, true]);
  const markButton = Array.from(host.querySelectorAll('button')).find(b => b.textContent?.includes('全部标为已读'))!;
  await act(async () => markButton.click());
  expect(markAll).toHaveBeenCalled();
  await act(async () => tab(/^新帖/).click());
  expect(rows()[0].textContent).toContain('Doug O 发帖');
  await act(async () => tab(/^我参与的/).click());
  expect(rows().map(r => r.textContent?.includes('My own thread'))).toEqual([true]);
  expect(localStorage.getItem('slack-activity-filter')).toBe('following');
  // 我翻译的：有翻译稿的帖子，顶上有入口进全部翻译记录
  await act(async () => tab(/^我翻译的/).click());
  const postRows = rows().filter(r => !r.textContent?.includes('全部翻译记录'));
  expect(postRows.map(r => r.textContent?.includes('Elon'))).toEqual([true]);
  expect(host.textContent).toContain('全部翻译记录 ›');
});

it('the todo button shows the same count as my todos and goes back to them', async () => {
  todos.data = { items: [{ kind: 'dm', channel_id: 'D1', channel_name: 'Michelle', conversation_kind: 'im', thread_ts: null,
    title: 'Michelle', from: ['Michelle'], count: 1, latest_ts: '1.1', task: 'x', action: 'reply',
    mark: { channel_id: 'D1', ts: '1.1' }, draft: null }], fyi: [] };
  const onShowTodos = vi.fn();
  await render({ onShowTodos });
  const button = host.querySelector<HTMLButtonElement>('[aria-label="我的待办"]')!;
  expect(button.textContent?.trim()).toBe('我的待办1');
  await act(async () => button.click());
  expect(onShowTodos).toHaveBeenCalled();
  expect(host.textContent).not.toContain('AI 速览');
  expect(host.querySelector('[aria-label="更多"]')).toBeNull();
});

it('j / k walk the current list, Esc goes back, typing is ignored', async () => {
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

it('my todos: one line per task, translate button, broadcasts folded, done marks everything read', async () => {
  const base = {
    channel_name: 'social', conversation_kind: 'channel' as const, title: 'AI Racks', from: ['Daksh'], count: 1,
    latest_ts: '1794963980.687079', draft: null,
  };
  todos.data = {
    items: [
      { ...base, kind: 'dm', channel_id: 'D1', channel_name: 'Michelle', conversation_kind: 'im', thread_ts: null,
        task: 'Michelle 在等你回复', action: 'reply', mark: { channel_id: 'D1', ts: '1.1' } },
      { ...base, kind: 'mention', channel_id: 'C1', thread_ts: '2.2', task: 'Daksh 让你翻这篇', action: 'do',
        mark: { channel_id: 'C1', ts: '2.3', thread_ts: '2.2' },
        draft: { id: 's_x', status: 'draft', auto: true, seen: false, versions: 1, no_post: false } },
    ],
    fyi: [{ ...base, kind: 'mention', channel_id: 'C1', thread_ts: '3.3', task: '', action: 'read', title: 'Elon post',
      from: ['Reyk'], mark: { channel_id: 'C1', ts: '3.4', thread_ts: '3.3' } }],
  };
  const onOpen = vi.fn();
  const onTranslate = vi.fn();
  await act(async () => root.render(<TodoView onOpen={onOpen} onTranslate={onTranslate} />));
  expect(host.textContent).toContain('Michelle 在等你回复');
  expect(host.textContent).toContain('要回复');
  const translate = Array.from(host.querySelectorAll('button')).find(b => b.textContent?.includes('查看翻译'))!;
  await act(async () => translate.click());
  expect(onTranslate).toHaveBeenCalledWith('C1', '2.2');
  expect(host.textContent).toContain('不用处理（群发 @）· 1');
  expect(host.textContent).not.toContain('Elon post');  // 默认收起
  await act(async () => Array.from(host.querySelectorAll('button')).find(b => b.textContent?.includes('都处理完了'))!.click());
  expect(markAll).toHaveBeenLastCalledWith([
    { channel_id: 'D1', ts: '1.1', thread_ts: null },
    { channel_id: 'C1', ts: '2.3', thread_ts: '2.2' },
    { channel_id: 'C1', ts: '3.4', thread_ts: '3.3' },
  ]);
  await act(async () => host.querySelector<HTMLButtonElement>('[role="switch"]')!.click());
  expect(saveSettings).toHaveBeenCalledWith({ auto_translate_mentions: false });
});
