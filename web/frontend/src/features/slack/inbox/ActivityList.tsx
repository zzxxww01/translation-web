import { useEffect, useRef, useState } from 'react';
import { CheckCheck, ClipboardList, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Avatar } from './MessageItem';
import { useMarkAllRead, useSlackActivity } from './hooks';
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
type Filter = 'all' | 'unread' | 'mentions' | 'dm' | 'posts' | 'following';

const isPost = (i: SlackActivityItem) => i.type === 'thread' && !i.reply_count && !i.root?.is_me;

const FILTERS: { id: Filter; label: string; hint: string; match: (i: SlackActivityItem) => boolean }[] = [
  { id: 'all', label: '全部', hint: '最近 7 天的 thread、新帖和私信，按时间排', match: () => true },
  { id: 'unread', label: '未读', hint: '还没看过的', match: i => i.has_unreads },
  { id: 'mentions', label: '@我', hint: '有人 @ 了你', match: i => i.mentions_me },
  { id: 'dm', label: '私信', hint: '私信和群聊私信', match: i => i.type === 'dm' },
  { id: 'posts', label: '新帖', hint: '最近 7 天还没人回复的帖子（待翻译）', match: isPost },
  { id: 'following', label: '我参与的', hint: '你发起、回复过或被 @ 的 thread', match: i => i.type === 'thread' && !!i.following },
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
export function ActivityList({ selection, onOpen, onShowTodos, todosActive, onBack }: ActivityListProps) {
  const activity = useSlackActivity(true);
  const markAll = useMarkAllRead();
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
  // 待办数：未读的 @我 和私信（和中间「我的待办」同一口径）
  const todoCount = all.filter(i => i.has_unreads && (i.mentions_me || i.type === 'dm')).length;
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
      <div className="flex items-center gap-1 border-b border-border-subtle px-2 py-2">
        <div className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto" role="tablist" aria-label="筛选">
          {FILTERS.map(f => {
            const n = f.id === 'all' ? 0 : unreadIn(f);
            return (
              <button
                key={f.id}
                type="button"
                role="tab"
                aria-selected={filter === f.id}
                title={f.hint}
                onClick={() => setFilter(f.id)}
                className={cn(
                  'shrink-0 whitespace-nowrap rounded-full px-2.5 py-1 text-xs transition-colors',
                  filter === f.id ? 'bg-primary-500 font-medium text-white shadow-sm' : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary'
                )}
              >
                {f.label}{n > 0 ? <span className={cn('ml-1 tabular-nums', filter === f.id ? 'text-white/80' : 'text-primary-600')}>{n}</span> : null}
              </button>
            );
          })}
        </div>
        <button
          type="button"
          onClick={onShowTodos}
          className={cn(
            'inline-flex shrink-0 items-center gap-1 rounded-lg px-2 py-1 text-xs transition-colors',
            todosActive ? 'bg-primary-50 font-medium text-primary-700' : 'text-text-secondary hover:bg-bg-hover'
          )}
          title="我的待办：还没读的 @我 和私信"
        >
          <ClipboardList className="h-3.5 w-3.5" /> 待办{todoCount > 0 && <span className="rounded-full bg-error px-1.5 text-[10px] font-semibold leading-4 text-white">{todoCount}</span>}
        </button>
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
        {filter === 'unread' && items.length > 0 && (
          <div className="flex items-center justify-between border-b border-border-subtle bg-bg-tertiary/50 px-3 py-1.5 text-xs text-text-muted">
            <span>{items.length} 条未读</span>
            <button
              type="button"
              onClick={() => markAll.mutate(undefined)}
              disabled={markAll.isPending || unreadTotal === 0}
              className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-primary-700 hover:bg-primary-50"
              title="只记在 momo 里，Slack 的未读不变"
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

/** 翻译稿状态：草稿 / 已完成 / 自动翻好（没要翻的帖子不显示） */
function DraftBadge({ draft }: { draft: SlackActivityItem['draft'] }) {
  if (!draft || draft.no_post) return null;
  if (draft.status === 'done') return <span className="shrink-0 rounded bg-success/10 px-1 text-[10px] font-medium leading-4 text-success">✓ 已翻</span>;
  if (draft.auto && !draft.seen) return <span className="shrink-0 rounded bg-primary-500 px-1 text-[10px] font-medium leading-4 text-white">自动翻好</span>;
  return <span className="shrink-0 rounded bg-amber-100 px-1 text-[10px] font-medium leading-4 text-amber-800">草稿 v{draft.versions}</span>;
}

function Row({ item, active, manyChannels, onOpen }: {
  item: SlackActivityItem;
  active: boolean;
  manyChannels: boolean;
  onOpen: (item: SlackActivityItem) => void;
}) {
  const isThread = item.type === 'thread';
  const who = isThread ? item.root?.user_name ?? '' : item.channel_name;
  // 列表里各种类型混在一起：私信 / 新帖用小字写明，普通 thread 不写（第二行已经说明了）
  const tag = !isThread ? (item.kind === 'mpim' ? '群聊' : '私信') : isPost(item) ? '新帖' : null;
  const channel = isThread && manyChannels ? `#${item.channel_name} · ` : '';
  return (
    <button
      type="button"
      onClick={() => onOpen(item)}
      aria-current={active || undefined}
      className={cn('block w-full border-b border-border-subtle px-3 py-2 text-left transition-colors', active ? 'bg-primary-50' : 'hover:bg-bg-hover')}
    >
      <div className="flex items-start gap-2.5">
        <Avatar name={who || '?'} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            {item.has_unreads && <span className="h-2 w-2 shrink-0 rounded-full bg-primary-500" aria-label="有新消息" />}
            <span className={cn('min-w-0 flex-1 truncate text-[14px] text-text-primary', item.has_unreads && 'font-semibold')}>
              {isThread ? firstLine(item.root, 80, true) : item.channel_name}
            </span>
            {item.mentions_me && <span className="shrink-0 rounded-full bg-error px-1.5 text-[10px] font-semibold leading-4 text-white">@我</span>}
            {tag && <span className="shrink-0 rounded bg-bg-hover px-1 text-[10px] leading-4 text-text-secondary">{tag}</span>}
            <span className="shrink-0 text-[11px] text-text-muted">{shortTime(item.latest_ts)}</span>
          </div>
          {isThread && (
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="min-w-0 flex-1 truncate text-xs text-text-muted">
                {`${channel}${who}${item.reply_count ? ` 发起 · ${item.reply_count} 条回复` : ' 发帖 · 还没人回复'}`
                  + (item.participants && item.participants.length > 1 ? ` · ${item.participants.length} 人参与` : '')}
              </span>
              <DraftBadge draft={item.draft} />
            </div>
          )}
          {(item.last || !isThread) && (
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="min-w-0 flex-1 truncate text-[13px] text-text-secondary">
                {item.last && <><span className="font-medium">{item.last.is_me ? '我' : item.last.user_name}：</span>{firstLine(item.last, 120)}</>}
              </span>
            </div>
          )}
        </div>
      </div>
    </button>
  );
}
