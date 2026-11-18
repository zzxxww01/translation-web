import { useState, type ReactNode } from 'react';
import { ChevronDown, ChevronRight, Hash, Languages, Loader2, Lock, MessagesSquare, RefreshCw, Search, Sparkles, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RunMeta } from '@/features/skills/types';
import { AgentBadge } from '../agent/AgentBadge';
import { useSlackAgentRuns } from '../agent/agentRuns';
import { Avatar } from './MessageItem';
import { useChannelThreads, useRefreshSlack } from './hooks';
import { clockTime, splitSidebar, threadTitle, type SlackView } from './lib';
import type { SlackConversation, SlackStatus, SlackThreadBadge } from './types';

export interface OpenThread {
  channelId: string;
  threadTs: string;
}

interface SidebarProps {
  status: SlackStatus;
  conversations: SlackConversation[];
  loading: boolean;
  error: string | null;
  threadBadge: SlackThreadBadge | undefined;
  selectedId: string | null;
  view: SlackView | null;
  openThread: OpenThread | null;
  onSelectConversation: (id: string) => void;
  onSelectView: (view: SlackView) => void;
  onOpenThread: (thread: OpenThread) => void;
  onSearch: (q: string) => void;
}

function MentionBadge({ count }: { count: number }) {
  return (
    <span className="min-w-[18px] rounded-full bg-error px-1.5 text-center text-[11px] font-semibold leading-[18px] text-white">
      {count}
    </span>
  );
}

function NavRow({
  active, unread, onClick, icon, label, badge, indent = false,
}: {
  active: boolean; unread: boolean; onClick: () => void; icon: ReactNode; label: string; badge?: ReactNode; indent?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2 rounded-md py-1 pr-2 text-left text-[14px] transition-colors',
        indent ? 'pl-7' : 'pl-2',
        active ? 'bg-primary-500 text-white' : unread ? 'font-semibold text-text-primary hover:bg-bg-hover' : 'text-text-secondary hover:bg-bg-hover'
      )}
    >
      {icon}
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {badge}
    </button>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex w-full items-center gap-1 rounded-md px-2 py-1 text-[13px] font-medium text-text-muted hover:bg-bg-hover"
      >
        {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        {title}
      </button>
      {open && <div className="mt-0.5 space-y-px">{children}</div>}
    </div>
  );
}

const THREADS_SHOWN = 8;

/** 频道展开后的 thread 列表：最近 7 天有回复的，未读加粗，@我 标红。 */
function ChannelThreads({ channelId, openThread, onOpenThread, agents }: {
  channelId: string; openThread: OpenThread | null; onOpenThread: (t: OpenThread) => void; agents: Map<string, RunMeta>;
}) {
  const threads = useChannelThreads(channelId, true);
  const [showAll, setShowAll] = useState(false);
  if (threads.isLoading) return <div className="py-1 pl-8"><Loader2 className="h-3.5 w-3.5 animate-spin text-text-muted" /></div>;
  if (threads.isError) {
    return (
      <div className="py-1 pl-8 text-xs text-error">
        thread 列表没加载出来：{threads.error.message}
        <button type="button" onClick={() => void threads.refetch()} className="ml-1 text-primary-700 hover:underline">重试</button>
      </div>
    );
  }
  const list = threads.data ?? [];
  if (list.length === 0) return <div className="py-1 pl-8 text-xs text-text-muted">最近 7 天没有 thread</div>;
  const shown = showAll ? list : list.slice(0, THREADS_SHOWN);
  return (
    <div className="space-y-px">
      <div className="pl-8 pt-0.5 text-[11px] text-text-muted" title="thread = 某条消息下面的回复串。这里列出这个频道最近 7 天有回复的，标题是根消息的第一行原文">
        最近有回复的 thread（回复串）
      </div>
      {shown.map(t => {
        const active = openThread?.channelId === channelId && openThread.threadTs === t.thread_ts;
        return (
          <button
            key={t.thread_ts}
            type="button"
            onClick={() => onOpenThread({ channelId, threadTs: t.thread_ts })}
            title={`${t.root.user_name}：${t.root.text.slice(0, 200)}\n${t.reply_count} 条回复 · ${t.latest_time}`}
            className={cn(
              'flex w-full items-center gap-1.5 rounded-md py-0.5 pl-8 pr-2 text-left text-[13px] transition-colors',
              active ? 'bg-primary-500 text-white' : t.has_unreads ? 'font-semibold text-text-primary hover:bg-bg-hover' : 'text-text-muted hover:bg-bg-hover'
            )}
          >
            <span className="min-w-0 flex-1 truncate">{threadTitle(t)}</span>
            {t.mentions_me && <span className={cn('text-[11px] font-bold', active ? 'text-white' : 'text-error')}>@</span>}
            {t.has_unreads && !t.mentions_me && <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-primary-500" aria-label="有新回复" />}
            <AgentBadge run={agents.get(`slack:${channelId}:${t.thread_ts}`)} active={active} />
            <span className={cn('shrink-0 text-[11px]', active ? 'text-white/80' : 'text-text-muted')}>{t.reply_count}</span>
          </button>
        );
      })}
      {list.length > THREADS_SHOWN && (
        <button type="button" onClick={() => setShowAll(v => !v)} className="py-0.5 pl-8 text-xs text-primary-700 hover:underline">
          {showAll ? '收起' : `还有 ${list.length - THREADS_SHOWN} 个 thread`}
        </button>
      )}
    </div>
  );
}

function ChannelIcon({ kind }: { kind: SlackConversation['kind'] }) {
  const cls = 'h-4 w-4 shrink-0 opacity-70';
  if (kind === 'private') return <Lock className={cls} />;
  if (kind === 'mpim') return <Users className={cls} />;
  return <Hash className={cls} />;
}

export function Sidebar(props: SidebarProps) {
  const { status, conversations, selectedId, view, openThread, threadBadge } = props;
  const refresh = useRefreshSlack();
  const agents = useSlackAgentRuns();
  const { channels, dms } = splitSidebar(conversations);
  // 频道默认展开，直接看到它的 thread；折叠状态只在当前页面里有效
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const toggle = (id: string) => setCollapsed(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });

  return (
    <>
      <div className="flex items-center justify-between border-b border-border-subtle px-4 py-3">
        <div className="min-w-0">
          <div className="truncate text-[15px] font-bold text-text-primary">{status.team}</div>
          <div className="truncate text-xs text-text-muted" title="消息存在服务器上，后台每分钟只拉新的">
            {status.user}
            {status.local ? ` · 本地 ${status.local.messages} 条` : ''}
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
      <form
        className="mx-2 mt-2 flex items-center gap-1.5 rounded-md border border-border-subtle bg-white px-2"
        onSubmit={e => {
          e.preventDefault();
          const q = new FormData(e.currentTarget).get('q');
          if (typeof q === 'string' && q.trim()) props.onSearch(q.trim());
        }}
      >
        <Search className="h-3.5 w-3.5 shrink-0 text-text-muted" />
        <input name="q" placeholder="搜索（中文也行）" aria-label="搜索 Slack" className="min-w-0 flex-1 bg-transparent py-1.5 text-sm outline-none placeholder:text-text-muted" />
      </form>
      <nav className="min-h-0 flex-1 overflow-auto px-2 py-2" aria-label="Slack 会话">
        <NavRow
          active={view === 'digest'}
          unread={false}
          onClick={() => props.onSelectView('digest')}
          icon={<Sparkles className="h-4 w-4 shrink-0 text-primary-500" />}
          label="AI 速览（未读汇总）"
        />
        <NavRow
          active={view === 'threads'}
          unread={!!threadBadge?.has_unreads}
          onClick={() => props.onSelectView('threads')}
          icon={<MessagesSquare className="h-4 w-4 shrink-0 opacity-70" />}
          label="我参与的 thread"
          badge={threadBadge?.mention_count ? <MentionBadge count={threadBadge.mention_count} /> : undefined}
        />

        {props.loading && <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}
        {props.error && <div className="p-2 text-sm text-error">加载会话失败：{props.error}</div>}

        {channels.length > 0 && (
          <Section title="频道（你加入的）">
            {channels.map(c => {
              const expanded = !collapsed.has(c.id);
              const mentions = c.mention_count + c.thread_mentions;
              return (
                <div key={c.id}>
                  <div className="flex items-center">
                    <button
                      type="button"
                      onClick={() => toggle(c.id)}
                      className="rounded p-0.5 text-text-muted hover:bg-bg-hover"
                      aria-label={expanded ? '收起 thread' : '展开 thread'}
                      title={expanded ? '收起 thread' : '展开这个频道的 thread'}
                    >
                      {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
                    </button>
                    <div className="min-w-0 flex-1">
                      <NavRow
                        active={c.id === selectedId && !view}
                        unread={c.has_unreads || c.thread_unreads > 0}
                        onClick={() => props.onSelectConversation(c.id)}
                        icon={<ChannelIcon kind={c.kind} />}
                        label={c.name}
                        badge={mentions > 0 ? <MentionBadge count={mentions} /> : undefined}
                      />
                    </div>
                  </div>
                  {expanded && <ChannelThreads channelId={c.id} openThread={openThread} onOpenThread={props.onOpenThread} agents={agents} />}
                </div>
              );
            })}
          </Section>
        )}

        {dms.length > 0 && (
          <Section title="私信（一对一和小群）">
            {dms.map(c => (
              <NavRow
                key={c.id}
                active={c.id === selectedId && !view}
                unread={c.has_unreads}
                onClick={() => props.onSelectConversation(c.id)}
                icon={c.kind === 'mpim' ? <ChannelIcon kind="mpim" /> : <Avatar name={c.name} size="sm" />}
                label={c.name}
                badge={
                  <>
                    <AgentBadge run={agents.get(`slack:${c.id}`)} active={c.id === selectedId && !view} />
                    {c.mention_count > 0 && <MentionBadge count={c.mention_count} />}
                  </>
                }
              />
            ))}
          </Section>
        )}
      </nav>
      <div className="border-t border-border-subtle p-2">
        <NavRow
          active={view === 'reply'}
          unread={false}
          onClick={() => props.onSelectView('reply')}
          icon={<Languages className="h-4 w-4 shrink-0 opacity-70" />}
          label="自由翻译（回复工作台）"
        />
      </div>
    </>
  );
}
