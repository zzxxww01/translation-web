import { useEffect, useRef, useState } from 'react';
import { CheckCheck, ClipboardList, Loader2 } from 'lucide-react';
import { sendTimeShort } from '@/features/post/drafts';
import { cn } from '@/lib/utils';
import { useMarkAllRead, useSlackActivity, useTodos } from './hooks';
import { clockTime, emojify, stripLeadingMentions } from './lib';
import { stripMrkdwn } from './mrkdwn';
import type { SlackActivityItem, SlackMessage } from './types';

/** 正在看的那一行：thread 用（会话, thread_ts），私信用会话 id */
export interface ActivitySelection {
  channelId: string;
  threadTs: string | null;
}

/**
 * 筛选（2026-11-22 用户要求：一行筛选自己选，「全部」按时间排）。各筛选可以重叠，比如 @我 的私信两边都有。
 * 数字是这一类里的未读条数。
 */
type Filter = 'all' | 'unread' | 'mentions' | 'dm' | 'following' | 'translated' | 'unsent';

const isTranslated = (i: SlackActivityItem) => !!i.draft && !i.draft.no_post;
const isSent = (draft: NonNullable<SlackActivityItem['draft']>) => draft.sent ?? !!draft.sent_at;

const isPost = (i: SlackActivityItem) => i.type === 'thread' && !i.reply_count && !i.root?.is_me;

// 2026-11-28 用户要求去掉「新帖」筛选；以前存的 posts 回到「全部」
const FILTERS: { id: Filter; label: string; hint: string; match: (i: SlackActivityItem) => boolean }[] = [
  { id: 'all', label: '全部', hint: '最近 7 天的 thread、新帖和私信，按时间排', match: () => true },
  { id: 'unread', label: '未读', hint: '还没看过的', match: i => i.has_unreads },
  { id: 'mentions', label: '@我', hint: '有人 @ 了你', match: i => i.mentions_me },
  { id: 'dm', label: '私信', hint: '私信和群聊私信', match: i => i.type === 'dm' },
  { id: 'following', label: '我参与的', hint: '你发起、回复过或被 @ 的 thread', match: i => i.type === 'thread' && !!i.following },
  { id: 'translated', label: '我翻译的', hint: '最近 7 天翻过的帖子；更早的和帖子翻译页的在「全部翻译记录」', match: isTranslated },
  { id: 'unsent', label: '未发送', hint: '最近 7 天翻过、还没标已发送的帖子；全部的在「全部翻译记录」里筛', match: i => isTranslated(i) && !isSent(i.draft!) },
];

const FILTER_KEY = 'slack-activity-filter';
function loadFilter(): Filter {
  const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(FILTER_KEY) : null;
  return FILTERS.some(f => f.id === saved) ? (saved as Filter) : 'all';
}

interface ActivityListProps {
  selection: ActivitySelection | null;
  onOpen: (item: SlackActivityItem) => void;
  /** 回到中间的「我的待办」 */
  onShowTodos: () => void;
  /** 中间显示全部翻译记录（不限 7 天，含帖子翻译页的） */
  onShowHistory: () => void;
  todosActive: boolean;
  /** Esc：关掉正在看的 thread / 会话 */
  onBack?: () => void;
}

/** 在输入框里打字时不响应快捷键 */
function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  return !!el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName));
}

/** 消息第一行（去掉 *加粗*、`代码` 等格式记号，表情码换成 emoji）；没有文字时用附件名 */
function firstLine(message: SlackMessage | null | undefined, max = 80, asTitle = false): string {
  if (!message) return '';
  const raw = (message.text || '').split('\n').map(s => s.trim()).find(Boolean)
    || message.attachments[0]?.title || message.files[0]?.name || '（无文字）';
  const line = asTitle ? stripLeadingMentions(raw) : raw;
  const text = emojify(stripMrkdwn(line));
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

/** 今天显示时刻，昨天显示「昨天」，更早显示月/日 */
function shortTime(ts: string, now = new Date()): string {
  const d = new Date(parseFloat(ts) * 1000);
  const days = Math.round((new Date(now).setHours(0, 0, 0, 0) - new Date(d).setHours(0, 0, 0, 0)) / 86_400_000);
  if (days === 0) return clockTime(ts);
  if (days === 1) return '昨天';
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

/**
 * 左栏：最上面「AI 速览」入口，下面一行筛选（右边「⋯」里是旧版工作台和全部标为已读），再下面是列表。
 */
export function ActivityList({ selection, onOpen, onShowTodos, onShowHistory, todosActive, onBack }: ActivityListProps) {
  const activity = useSlackActivity(true);
  const markAll = useMarkAllRead();
  const todos = useTodos(true);
  const [filter, setFilterState] = useState<Filter>(loadFilter);
  const setFilter = (f: Filter) => {
    setFilterState(f);
    localStorage.setItem(FILTER_KEY, f);
  };

  const all = activity.data ?? [];
  const current = FILTERS.find(f => f.id === filter) ?? FILTERS[0];
  const items = all.filter(current.match);
  const unreadIn = (f: (typeof FILTERS)[number]) => all.filter(i => f.match(i) && i.has_unreads).length;
  const unreadTotal = all.filter(i => i.has_unreads).length;
  // 待办数直接用「我的待办」的结果，两边口径一致
  const todoCount = todos.data?.items.length ?? 0;
  // 只有一个频道时每行都写同一个频道名没意义
  const manyChannels = new Set(all.filter(i => i.type === 'thread').map(i => i.channel_id)).size > 1;

  // 键盘：j / k 在当前筛选里切换并打开，Esc 关闭
  const keys = useRef({ items, selection, onOpen, onBack });
  useEffect(() => {
    keys.current = { items, selection, onOpen, onBack };
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target)) return;
      const { items: list, selection: sel, onOpen: open, onBack: back } = keys.current;
      if (e.key === 'j' || e.key === 'k') {
        if (list.length === 0) return;
        const at = sel ? list.findIndex(i => i.channel_id === sel.channelId && i.thread_ts === sel.threadTs) : -1;
        const next = at < 0 ? 0 : Math.min(list.length - 1, Math.max(0, at + (e.key === 'j' ? 1 : -1)));
        if (next !== at) open(list[next]);
        e.preventDefault();
      } else if (e.key === 'Escape' && back) {
        back();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <>
      {/* 我的待办单独一行放最上面：挤在筛选行右边时，筛选放不下要横向滚动，滚动条被它挡住（2026-11-23 用户反馈） */}
      <button
        type="button"
        onClick={onShowTodos}
        className={cn(
          'flex items-center gap-2 border-b border-border-subtle px-4 py-2 text-left text-[13px] transition-colors',
          todosActive ? 'bg-bg-tertiary font-medium text-text-primary' : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
        )}
        title="还没读的 @我 和私信"
        aria-label="我的待办"
      >
        <ClipboardList className="h-4 w-4 shrink-0" />
        <span className="flex-1">我的待办</span>
        {todoCount > 0 && <span className="rounded-full bg-error px-1.5 text-[10px] font-semibold leading-4 text-white">{todoCount}</span>}
      </button>
      <div className="border-b border-border-subtle px-2 py-2">
        {/* 分段选择：浅灰底，选中项白底 + 深色字；不用和顶部导航同一个梅红色，免得抢眼（2026-11-22 用户反馈） */}
        <div className="flex items-center gap-px overflow-x-auto rounded-lg bg-bg-tertiary p-0.5" role="tablist" aria-label="筛选">
          {FILTERS.map(f => {
            const n = f.id === 'all' ? 0 : unreadIn(f);
            const on = filter === f.id;
            return (
              <button
                key={f.id}
                type="button"
                role="tab"
                aria-selected={on}
                title={f.hint}
                onClick={() => setFilter(f.id)}
                className={cn(
                  'flex flex-auto shrink-0 items-baseline justify-center gap-1 whitespace-nowrap rounded-md px-1 py-[3px] text-[12.5px] leading-5 transition-all',
                  on ? 'bg-white font-medium text-text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'
                )}
              >
                {f.label}
                {n > 0 && <span className="text-[11px] tabular-nums text-text-muted">{n}</span>}
              </button>
            );
          })}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto" aria-label="Slack 动态">
        {activity.isLoading && <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}
        {activity.isError && (
          <div className="p-4 text-sm text-error">
            动态没加载出来：{activity.error.message}
            <button type="button" onClick={() => void activity.refetch()} className="ml-2 text-primary-700 hover:underline">重试</button>
          </div>
        )}
        {activity.data && items.length === 0 && (
          <div className="p-6 text-center text-sm text-text-muted">
            {filter === 'unread' ? '都看完了' : filter === 'all' ? '最近 7 天没有动态' : `最近 7 天没有「${current.label}」`}
          </div>
        )}
        {(filter === 'translated' || filter === 'unsent') && (
          <button
            type="button"
            onClick={onShowHistory}
            className="flex w-full items-center justify-between border-b border-border-subtle bg-bg-tertiary/50 px-4 py-2 text-left text-xs text-text-secondary hover:bg-bg-hover"
          >
            <span>这里是最近 7 天的。更早的、帖子翻译页翻的，都在全部翻译记录里</span>
            <span className="shrink-0 font-medium text-primary-700">全部翻译记录 ›</span>
          </button>
        )}
        {filter === 'unread' && items.length > 0 && (
          <div className="flex items-center justify-between border-b border-border-subtle bg-bg-tertiary/50 px-3 py-1.5 text-xs text-text-muted">
            <span>{items.length} 条未读</span>
            <button
              type="button"
              onClick={() => markAll.mutate(undefined)}
              disabled={markAll.isPending || unreadTotal === 0}
              className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-primary-700 hover:bg-primary-50"
              title="只在这里标为已读，Slack 里的未读不变"
            >
              <CheckCheck className="h-3.5 w-3.5" /> 全部标为已读
            </button>
          </div>
        )}
        {items.map(item => (
          <Row
            key={`${item.channel_id}-${item.thread_ts ?? 'dm'}`}
            item={item}
            active={!!selection && selection.channelId === item.channel_id && selection.threadTs === item.thread_ts}
            manyChannels={manyChannels}
            onOpen={onOpen}
          />
        ))}
      </div>
    </>
  );
}

/** 翻译稿状态写在第二行末尾的小字里；后台自动翻好、还没看过的整行底色稍深一点（2026-11-22 用户：不要彩色标签） */
function draftNote(draft: SlackActivityItem['draft']): string {
  if (!draft || draft.no_post) return '';
  if (isSent(draft)) return ' · 已发送';
  const when = draft.send_time ? ` · 建议 ${sendTimeShort(draft.send_time)} 发` : '';
  return (draft.status === 'done' ? ' · 已翻译 · 未发送' : ' · 翻译草稿 · 未发送') + when;
}

function Row({ item, active, manyChannels, onOpen }: {
  item: SlackActivityItem;
  active: boolean;
  manyChannels: boolean;
  onOpen: (item: SlackActivityItem) => void;
}) {
  const isThread = item.type === 'thread';
  const who = isThread ? item.root?.user_name ?? '' : item.channel_name;
  const autoNew = !!item.draft && item.draft.auto && !item.draft.seen && !item.draft.no_post;
  // 列表只看标题（2026-11-22 用户：不要头像方块、不要第三行预览）；第二行一行小字说明是什么
  const meta = isThread
    ? [
        manyChannels ? `#${item.channel_name}` : '',
        isPost(item) ? `${who} 发帖` : `${who} 发起 · ${item.reply_count} 条回复`,
        draftNote(item.draft).replace(' · ', ''),
      ]
    : [
        item.kind === 'mpim' ? '群聊' : '私信',
        item.last ? `${item.last.is_me ? '我' : item.last.user_name}：${firstLine(item.last, 60)}` : '',
      ];
  return (
    <button
      type="button"
      onClick={() => onOpen(item)}
      aria-current={active || undefined}
      className={cn(
        'block w-full border-b border-border-subtle/70 px-4 py-2.5 text-left transition-colors',
        active ? 'bg-primary-50' : autoNew ? 'bg-primary-50/40 hover:bg-primary-50/70' : 'hover:bg-bg-hover'
      )}
      title={autoNew ? '这个帖子已经在后台自动翻好了' : undefined}
    >
      <div className="flex items-center gap-2">
        {item.has_unreads && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary-500" aria-label="有新消息" />}
        <span className={cn('min-w-0 flex-1 truncate text-[14px] leading-5', item.has_unreads ? 'font-semibold text-text-primary' : 'text-text-primary')}>
          {isThread ? firstLine(item.root, 80, true) : item.channel_name}
        </span>
        {item.mentions_me && <span className="shrink-0 text-[11px] font-medium text-error">@我</span>}
        <span className="shrink-0 text-[11px] tabular-nums text-text-muted">{shortTime(item.latest_ts)}</span>
      </div>
      <div className={cn('mt-0.5 truncate text-xs leading-4 text-text-muted', item.has_unreads && 'pl-3.5')}>
        {meta.filter(Boolean).join(' · ')}
      </div>
    </button>
  );
}
