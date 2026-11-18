import { useState } from 'react';
import { Hash, Languages, Loader2, MessagesSquare, RefreshCw, Search, Sparkles, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AgentBadge } from '../agent/AgentBadge';
import { useSlackAgentRuns } from '../agent/agentRuns';
import { Avatar } from './MessageItem';
import { useRefreshSlack, useSlackActivity } from './hooks';
import { clockTime, emojify, stripLeadingMentions, type SlackView } from './lib';
import type { SlackActivityItem, SlackMessage, SlackStatus } from './types';

type Filter = 'all' | 'mentions' | 'dm';
const FILTERS: [Filter, string][] = [['all', '全部'], ['mentions', '@我'], ['dm', '私信']];

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
}

/** 消息第一行（去掉 Slack 的 *加粗*，表情码换成 emoji）；没有文字时用附件名 */
function firstLine(message: SlackMessage | null | undefined, max = 80, asTitle = false): string {
  if (!message) return '';
  const raw = (message.text || '').split('\n').map(s => s.trim()).find(Boolean)
    || message.attachments[0]?.title || message.files[0]?.name || '（无文字）';
  const line = asTitle ? stripLeadingMentions(raw) : raw;
  const text = emojify(line.replace(/\*([^*\n]+)\*/g, '$1'));
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
 * 「动态」：每一行是一个 thread（频道里最近 7 天有回复的）或一个私信对话，按最近有人说话的时间排序。
 * 点一行只看那一个 thread / 私信，不用进整个频道。
 */
export function ActivityList({ status, selection, view, onOpen, onSelectView, onSearch }: ActivityListProps) {
  const [filter, setFilter] = useState<Filter>('all');
  const activity = useSlackActivity(true);
  const refresh = useRefreshSlack();
  const agents = useSlackAgentRuns();
  const items = (activity.data ?? []).filter(item =>
    filter === 'all' ? true : filter === 'dm' ? item.type === 'dm' : item.mentions_me);
  const mentionCount = (activity.data ?? []).filter(item => item.mentions_me).length;
  // 只有一个频道时每行都写同一个频道名没意义，省下位置给「谁发起、几条回复」
  const manyChannels = new Set((activity.data ?? []).filter(item => item.type === 'thread').map(item => item.channel_id)).size > 1;

  return (
    <>
      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
        <div className="min-w-0">
          <div className="truncate text-[15px] font-bold text-text-primary">动态 · {status.team}</div>
          <div className="truncate text-xs text-text-muted" title="消息存在服务器上，后台每分钟只拉新的；momo 不往 Slack 发任何东西">
            {status.user}
            {status.local?.last_sync ? ` · 同步于 ${clockTime(String(status.local.last_sync))}` : ''}
          </div>
        </div>
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
          <input name="q" placeholder="搜索（中文也行）" aria-label="搜索 Slack" className="min-w-0 flex-1 bg-transparent py-1.5 text-sm outline-none placeholder:text-text-muted" />
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
              {label}{id === 'mentions' && mentionCount > 0 ? ` ${mentionCount}` : ''}
            </button>
          ))}
          <div className="ml-auto flex items-center gap-0.5">
            <button
              type="button"
              onClick={() => onSelectView('digest')}
              className={cn('rounded-md p-1 hover:bg-bg-hover', view === 'digest' ? 'text-primary-700' : 'text-text-muted')}
              title="AI 速览：所有未读整理成中文要点"
              aria-label="AI 速览"
            >
              <Sparkles className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => onSelectView('reply')}
              className={cn('rounded-md p-1 hover:bg-bg-hover', view === 'reply' ? 'text-primary-700' : 'text-text-muted')}
              title="自由翻译（回复工作台）"
              aria-label="自由翻译"
            >
              <Languages className="h-4 w-4" />
            </button>
          </div>
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
            {filter === 'mentions' ? '最近 7 天没人 @ 你' : filter === 'dm' ? '没有私信' : '最近 7 天没有动态'}
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
                    ? <div className="flex h-8 w-8 items-center justify-center rounded-md bg-bg-hover text-text-muted"><MessagesSquare className="h-4 w-4" /></div>
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
                          {manyChannels ? `${item.channel_name} · ` : ''}{item.root?.user_name} 发起 · {item.reply_count} 条回复
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
