import { useEffect, useRef, useState } from 'react';
import { CheckCheck, FileText, Hash, Languages, Loader2, MessageSquareText, MessagesSquare, RefreshCw, Search, Sparkles, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AgentBadge } from '../agent/AgentBadge';
import { useSlackAgentRuns } from '../agent/agentRuns';
import { Avatar } from './MessageItem';
import { useShowZh } from './ai';
import { useMarkAllRead, useRefreshSlack, useSlackActivity } from './hooks';
import { clockTime, emojify, stripLeadingMentions, type SlackView } from './lib';
import { stripMrkdwn } from './mrkdwn';
import type { SlackActivityItem, SlackMessage, SlackStatus } from './types';

type Filter = 'all' | 'unread' | 'mentions' | 'dm';
const FILTERS: [Filter, string][] = [['all', '全部'], ['unread', '未读'], ['mentions', '@我'], ['dm', '私信']];

function matches(item: SlackActivityItem, filter: Filter): boolean {
  if (filter === 'unread') return item.has_unreads;
  if (filter === 'mentions') return item.mentions_me;
  if (filter === 'dm') return item.type === 'dm';
  return true;
}

// 列表顶部的其他页面入口（带文字，之前是两个不好找的小图标）
const VIEW_LINKS: [SlackView, string, typeof Sparkles, string][] = [
  ['digest', 'AI 速览', Sparkles, '所有未读整理成中文要点'],
  ['threads', '我参与的', MessageSquareText, '我参与过的 thread，有新回复的在前'],
  ['reply', '回复工作台', Languages, '老工作台：贴一段英文或写中文草稿，生成三版英文回复'],
];

/** 正在看的那一行：thread 用（会话, thread_ts），私信用会话 id */
export interface ActivitySelection {
  channelId: string;
  threadTs: string | null;
}

interface ActivityListProps {
  status: SlackStatus;
  selection: ActivitySelection | null;
  view: SlackView | null;
  onOpen: (item: SlackActivityItem) => void;
  onSelectView: (view: SlackView) => void;
  onSearch: (q: string) => void;
  /** Esc：关掉正在看的 thread / 会话 */
  onBack?: () => void;
}

/** 在输入框里打字时不响应快捷键 */
function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  return !!el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName));
}

const SHORTCUTS = '快捷键：j / k 下一条 / 上一条，/ 搜索，t 全部中文，Esc 关闭';

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
 * 「动态」：每一行是一个 thread（频道里最近 7 天的，含还没人回复的新帖）或一个私信对话，按最近有人说话的时间排序。
 * 点一行只看那一个 thread / 私信，不用进整个频道。
 */
export function ActivityList({ status, selection, view, onOpen, onSelectView, onSearch, onBack }: ActivityListProps) {
  const [filter, setFilter] = useState<Filter>('all');
  const activity = useSlackActivity(true);
  const refresh = useRefreshSlack();
  const markAll = useMarkAllRead();
  const toggleZh = useShowZh(state => state.toggleZh);
  const searchRef = useRef<HTMLInputElement>(null);
  const agents = useSlackAgentRuns();
  const all = activity.data ?? [];
  const items = all.filter(item => matches(item, filter));
  // 筛选旁的数字：全部 / 私信显示其中未读的，未读 / @我 显示总数
  const counts: Record<Filter, number> = {
    all: all.filter(item => item.has_unreads).length,
    unread: all.filter(item => item.has_unreads).length,
    mentions: all.filter(item => item.mentions_me).length,
    dm: all.filter(item => item.type === 'dm' && item.has_unreads).length,
  };

  // 键盘：j / k 在当前筛选的列表里切换并打开，/ 搜索，t 全部中文，Esc 关闭
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
      } else if (e.key === '/') {
        searchRef.current?.focus();
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
  // 只有一个频道时每行都写同一个频道名没意义，省下位置给「谁发起、几条回复」
  const manyChannels = new Set((activity.data ?? []).filter(item => item.type === 'thread').map(item => item.channel_id)).size > 1;

  return (
    <>
      <div className="flex items-center gap-0.5 border-b border-border-subtle px-4 py-3">
        <div className="min-w-0 flex-1">
          <div className="truncate text-[15px] font-bold text-text-primary">动态 · {status.team}</div>
          <div className="truncate text-xs text-text-muted" title="消息存在服务器上，后台每分钟只拉新的；momo 不往 Slack 发任何东西">
            {status.user}
            {status.local?.last_sync ? ` · 同步于 ${clockTime(String(status.local.last_sync))}` : ''}
          </div>
        </div>
        <button
          type="button"
          onClick={() => markAll.mutate()}
          disabled={markAll.isPending || counts.unread === 0}
          className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary disabled:opacity-40"
          title="全部标为已读（只记在 momo 里，Slack 的未读不变）"
          aria-label="全部标为已读"
        >
          <CheckCheck className="h-4 w-4" />
        </button>
        <button
          type="button"
          onClick={() => refresh.mutate()}
          disabled={refresh.isPending}
          className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary"
          title="立即从 Slack 刷新"
          aria-label="刷新"
        >
          <RefreshCw className={cn('h-4 w-4', refresh.isPending && 'animate-spin')} />
        </button>
      </div>

      <div className="space-y-2 border-b border-border-subtle px-3 py-2">
        <form
          className="flex items-center gap-1.5 rounded-md border border-border-subtle bg-white px-2"
          onSubmit={e => {
            e.preventDefault();
            const q = new FormData(e.currentTarget).get('q');
            if (typeof q === 'string' && q.trim()) onSearch(q.trim());
          }}
        >
          <Search className="h-3.5 w-3.5 shrink-0 text-text-muted" />
          <input ref={searchRef} name="q" placeholder="搜索（中文也行）  /" aria-label="搜索 Slack" title={SHORTCUTS} className="min-w-0 flex-1 bg-transparent py-1.5 text-sm outline-none placeholder:text-text-muted" />
        </form>
        <div className="flex items-center gap-1" role="tablist" aria-label="筛选动态">
          {FILTERS.map(([id, label]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={filter === id}
              onClick={() => setFilter(id)}
              className={cn(
                'rounded-full px-2.5 py-0.5 text-xs transition-colors',
                filter === id ? 'bg-primary-500 text-white' : 'bg-bg-hover text-text-secondary hover:text-text-primary'
              )}
            >
              {label}{id !== 'all' && counts[id] > 0 ? ` ${counts[id]}` : ''}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 text-xs">
          {VIEW_LINKS.map(([id, label, Icon, title]) => (
            <button
              key={id}
              type="button"
              onClick={() => onSelectView(id)}
              title={title}
              className={cn(
                'inline-flex items-center gap-1 rounded-md px-2 py-1 transition-colors hover:bg-bg-hover',
                view === id ? 'bg-primary-50 font-medium text-primary-700' : 'text-text-secondary'
              )}
            >
              <Icon className="h-3.5 w-3.5" /> {label}
            </button>
          ))}
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
            {filter === 'unread' ? '都看完了' : filter === 'mentions' ? '最近 7 天没人 @ 你' : filter === 'dm' ? '没有私信' : '最近 7 天没有动态'}
          </div>
        )}
        {items.map(item => {
          const active = !!selection && selection.channelId === item.channel_id && selection.threadTs === item.thread_ts;
          const agentKey = item.type === 'thread' ? `slack:${item.channel_id}:${item.thread_ts}` : `slack:${item.channel_id}`;
          return (
            <button
              key={`${item.channel_id}-${item.thread_ts ?? 'dm'}`}
              type="button"
              onClick={() => onOpen(item)}
              aria-current={active || undefined}
              className={cn(
                'block w-full border-b border-border-subtle px-3 py-2.5 text-left transition-colors',
                active ? 'bg-primary-50' : 'hover:bg-bg-hover'
              )}
            >
              <div className="flex items-start gap-2.5">
                <div className="pt-0.5">
                  {item.type === 'thread'
                    ? <div className="flex h-8 w-8 items-center justify-center rounded-md bg-bg-hover text-text-muted">
                        {item.reply_count ? <MessagesSquare className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                      </div>
                    : item.kind === 'mpim'
                      ? <div className="flex h-8 w-8 items-center justify-center rounded-md bg-bg-hover text-text-muted"><Users className="h-4 w-4" /></div>
                      : <Avatar name={item.channel_name} />}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    {item.has_unreads && <span className="h-2 w-2 shrink-0 rounded-full bg-primary-500" aria-label="有新消息" />}
                    <span className={cn('min-w-0 flex-1 truncate text-[14px]', item.has_unreads ? 'font-semibold text-text-primary' : 'text-text-primary')}>
                      {item.type === 'thread' ? firstLine(item.root, 80, true) : item.channel_name}
                    </span>
                    {item.mentions_me && <span className="shrink-0 rounded-full bg-error px-1.5 text-[11px] font-semibold text-white">@我</span>}
                    <AgentBadge run={agents.get(agentKey)} active={false} />
                    <span className="shrink-0 text-[11px] text-text-muted">{shortTime(item.latest_ts)}</span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-1 truncate text-xs text-text-muted">
                    {item.type === 'thread' ? (
                      <>
                        {manyChannels && <Hash className="h-3 w-3 shrink-0" />}
                        <span className="truncate">
                          {manyChannels ? `${item.channel_name} · ` : ''}{item.root?.user_name}
                          {item.reply_count ? ` 发起 · ${item.reply_count} 条回复` : ' 发帖 · 还没人回复'}
                          {item.participants && item.participants.length > 1 ? ` · ${item.participants.length} 人参与` : ''}
                        </span>
                      </>
                    ) : (
                      <span>{item.kind === 'mpim' ? '群聊私信' : '私信'}</span>
                    )}
                  </div>
                  {item.last && (
                    <div className="mt-0.5 truncate text-[13px] text-text-secondary">
                      <span className="font-medium">{item.last.is_me ? '我' : item.last.user_name}：</span>{firstLine(item.last, 120)}
                    </div>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </>
  );
}
