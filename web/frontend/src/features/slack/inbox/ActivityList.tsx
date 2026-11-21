import { useEffect, useRef, useState } from 'react';
import { CheckCheck, Languages, Loader2, MoreHorizontal, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { AgentBadge } from '../agent/AgentBadge';
import { useSlackAgentRuns } from '../agent/agentRuns';
import { useShowZh } from './ai';
import { Avatar } from './MessageItem';
import { useMarkAllRead, useSlackActivity } from './hooks';
import { clockTime, emojify, stripLeadingMentions, type SlackView } from './lib';
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
  view: SlackView | null;
  onOpen: (item: SlackActivityItem) => void;
  onSelectView: (view: SlackView) => void;
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
export function ActivityList({ selection, view, onOpen, onSelectView, onBack }: ActivityListProps) {
  const activity = useSlackActivity(true);
  const markAll = useMarkAllRead();
  const agents = useSlackAgentRuns();
  const toggleZh = useShowZh(state => state.toggleZh);
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
  // 只有一个频道时每行都写同一个频道名没意义
  const manyChannels = new Set(all.filter(i => i.type === 'thread').map(i => i.channel_id)).size > 1;

  // 键盘：j / k 在当前筛选里切换并打开，t 全部中文，Esc 关闭
  const keys = useRef({ items, selection, onOpen, onBack, toggleZh });
  useEffect(() => {
    keys.current = { items, selection, onOpen, onBack, toggleZh };
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target)) return;
      const { items: list, selection: sel, onOpen: open, onBack: back, toggleZh: zh } = keys.current;
      if (e.key === 'j' || e.key === 'k') {
        if (list.length === 0) return;
        const at = sel ? list.findIndex(i => i.channel_id === sel.channelId && i.thread_ts === sel.threadTs) : -1;
        const next = at < 0 ? 0 : Math.min(list.length - 1, Math.max(0, at + (e.key === 'j' ? 1 : -1)));
        if (next !== at) open(list[next]);
        e.preventDefault();
      } else if (e.key === 't') {
        zh();
      } else if (e.key === 'Escape' && back) {
        back();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <>
      <div className="border-b border-border-subtle">
        <button
          type="button"
          onClick={() => onSelectView('digest')}
          aria-current={view === 'digest' || undefined}
          className={cn('flex w-full items-center gap-2.5 px-4 py-2 text-left', view === 'digest' ? 'bg-primary-50' : 'hover:bg-bg-hover')}
        >
          <Sparkles className="h-4 w-4 shrink-0 text-primary-500" />
          <span className={cn('text-[14px]', view === 'digest' ? 'font-semibold text-primary-700' : 'font-medium text-text-primary')}>AI 速览</span>
          <span className="min-w-0 flex-1 truncate text-right text-xs text-text-muted">
            {unreadTotal ? `把 ${unreadTotal} 处未读整理成中文要点` : '未读整理成中文要点'}
          </span>
        </button>
        <div className="flex items-center gap-1 px-2 pb-2 pt-1">
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
                    'shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-xs transition-colors',
                    filter === f.id ? 'bg-primary-500 text-white' : 'bg-bg-hover text-text-secondary hover:text-text-primary'
                  )}
                >
                  {f.label}{n > 0 ? ` ${n}` : ''}
                </button>
              );
            })}
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button type="button" aria-label="更多" title="旧版工作台、全部标为已读"
                className="shrink-0 rounded-md p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary data-[state=open]:bg-bg-hover">
                <MoreHorizontal className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" sideOffset={4} className="w-56">
              <DropdownMenuItem onSelect={() => onSelectView('reply')}>
                <Languages className="h-4 w-4" /> 旧版工作台
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => markAll.mutate(undefined)} disabled={unreadTotal === 0 || markAll.isPending}>
                <CheckCheck className="h-4 w-4" /> 全部标为已读
                <span className="ml-auto text-[10px] text-text-muted">只在 momo 里</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
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
        {items.map(item => (
          <Row
            key={`${item.channel_id}-${item.thread_ts ?? 'dm'}`}
            item={item}
            active={!!selection && selection.channelId === item.channel_id && selection.threadTs === item.thread_ts}
            manyChannels={manyChannels}
            agent={agents.get(item.type === 'thread' ? `slack:${item.channel_id}:${item.thread_ts}` : `slack:${item.channel_id}`)}
            onOpen={onOpen}
          />
        ))}
      </div>
    </>
  );
}

function Row({ item, active, manyChannels, agent, onOpen }: {
  item: SlackActivityItem;
  active: boolean;
  manyChannels: boolean;
  agent: Parameters<typeof AgentBadge>[0]['run'];
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
              <AgentBadge run={agent} />
            </div>
          )}
          {(item.last || !isThread) && (
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="min-w-0 flex-1 truncate text-[13px] text-text-secondary">
                {item.last && <><span className="font-medium">{item.last.is_me ? '我' : item.last.user_name}：</span>{firstLine(item.last, 120)}</>}
              </span>
              {!isThread && <AgentBadge run={agent} />}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}
