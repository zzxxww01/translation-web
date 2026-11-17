import { useEffect, useMemo, useRef, type RefObject } from 'react';
import { ArrowLeft, Download, Hash, Loader2, Lock, MessageCircle, RefreshCw, Users } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { slackInboxApi } from './api';
import { CredentialsPanel } from './CredentialsPanel';
import { MessageItem } from './MessageItem';
import { useRefreshSlack, useSlackConversations, useSlackMessages, useSlackStatus } from './hooks';
import { filterConversations, type InboxScope } from './lib';
import type { ConversationKind, SlackConversation } from './types';

function KindIcon({ kind }: { kind: ConversationKind }) {
  const cls = 'h-4 w-4 shrink-0 text-text-muted';
  if (kind === 'channel') return <Hash className={cls} />;
  if (kind === 'private') return <Lock className={cls} />;
  if (kind === 'mpim') return <Users className={cls} />;
  return <MessageCircle className={cls} />;
}

function ConversationList({
  conversations, selectedId, onSelect,
}: { conversations: SlackConversation[]; selectedId: string | null; onSelect: (id: string) => void }) {
  if (conversations.length === 0) {
    return <div className="px-4 py-6 text-sm text-text-muted">没有可展示的会话</div>;
  }
  return (
    <ul className="space-y-0.5 p-2">
      {conversations.map(c => (
        <li key={c.id}>
          <button
            type="button"
            onClick={() => onSelect(c.id)}
            className={cn(
              'flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm transition-colors',
              c.id === selectedId ? 'bg-primary-50 text-primary-700' : 'text-text-secondary hover:bg-bg-hover'
            )}
          >
            <KindIcon kind={c.kind} />
            <span className={cn('min-w-0 flex-1 truncate', c.has_unreads && 'font-semibold text-text-primary')}>{c.name}</span>
            {c.mention_count > 0 && (
              <span className="rounded-full bg-primary-500 px-1.5 text-[11px] font-medium text-white">{c.mention_count}</span>
            )}
            {c.has_unreads && c.mention_count === 0 && <span className="h-2 w-2 rounded-full bg-primary-500" aria-label="有未读" />}
          </button>
          {c.latest_time && <div className="truncate px-8 pb-1 text-[11px] text-text-muted">{c.latest_time}</div>}
        </li>
      ))}
    </ul>
  );
}

function MessageStream({
  conversation, scrollRef,
}: { conversation: SlackConversation; scrollRef: RefObject<HTMLDivElement | null> }) {
  const query = useSlackMessages(conversation.id);
  // 接口按新→旧返回；页面按 Slack 习惯旧的在上、新的在下，「加载更早」放顶部
  const messages = useMemo(
    () => (query.data?.pages.flatMap(page => page.messages) ?? []).slice().reverse(),
    [query.data]
  );

  // 打开会话时停在最新消息处；之后轮询刷新、加载更早都不再动滚动位置
  const scrolled = useRef(false);
  const hasMessages = messages.length > 0;
  useEffect(() => {
    if (scrolled.current || !hasMessages) return;
    scrolled.current = true;
    const toBottom = () => {
      const el = scrollRef.current;
      if (el) el.scrollTop = el.scrollHeight;
    };
    toBottom();
    // 图片是懒加载的，撑开高度后再贴一次底
    const timer = setTimeout(toBottom, 800);
    return () => clearTimeout(timer);
  }, [hasMessages, scrollRef]);

  if (query.isLoading) {
    return <div className="flex h-full items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-text-muted" /></div>;
  }
  if (query.isError) {
    return <div className="p-6 text-sm text-error">加载消息失败：{query.error.message}</div>;
  }
  return (
    <div className="py-2">
      {query.hasNextPage && (
        <div className="flex justify-center py-2">
          <Button variant="outline" size="sm" onClick={() => query.fetchNextPage()} disabled={query.isFetchingNextPage}>
            {query.isFetchingNextPage ? '加载中…' : '加载更早的消息'}
          </Button>
        </div>
      )}
      {messages.length === 0 && <div className="px-4 py-6 text-sm text-text-muted">还没有消息</div>}
      {messages.map(m => <MessageItem key={m.ts} channelId={conversation.id} message={m} />)}
    </div>
  );
}

interface InboxViewProps {
  scope: InboxScope;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

export function InboxView({ scope, selectedId, onSelect }: InboxViewProps) {
  const status = useSlackStatus();
  const ready = !!status.data?.ok;
  const conversations = useSlackConversations(ready);
  const refresh = useRefreshSlack();
  const streamRef = useRef<HTMLDivElement>(null);

  const visible = useMemo(() => filterConversations(conversations.data ?? [], scope), [conversations.data, scope]);
  const selected = visible.find(c => c.id === selectedId) ?? null;

  if (status.isLoading) {
    return <div className="flex h-full items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-text-muted" /></div>;
  }
  if (status.isError) {
    return <div className="p-6 text-sm text-error">读取 Slack 状态失败：{status.error.message}</div>;
  }
  if (!ready) {
    return <CredentialsPanel status={status.data} />;
  }

  return (
    <div className="flex h-full min-h-0">
      <aside className={cn('w-full shrink-0 flex-col border-r border-border-subtle md:flex md:w-64', selected ? 'hidden' : 'flex')}>
        <div className="flex items-center justify-between border-b border-border-subtle px-4 py-2.5">
          <span className="truncate text-xs text-text-muted" title={status.data?.url}>
            {status.data?.user} · {status.data?.team}
          </span>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2"
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
            title="立即从 Slack 刷新"
            aria-label="刷新"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', refresh.isPending && 'animate-spin')} />
          </Button>
        </div>
        <div className="min-h-0 flex-1 overflow-auto">
          {conversations.isLoading ? (
            <div className="flex justify-center py-6"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>
          ) : conversations.isError ? (
            <div className="p-4 text-sm text-error">加载会话失败：{conversations.error.message}</div>
          ) : (
            <ConversationList conversations={visible} selectedId={selectedId} onSelect={onSelect} />
          )}
        </div>
        {scope === 'dms' && <div className="border-t border-border-subtle px-4 py-2 text-[11px] text-text-muted">只显示最近 30 天有往来的私信</div>}
      </aside>

      <section className={cn('min-w-0 flex-1 flex-col', selected ? 'flex' : 'hidden md:flex')}>
        {selected ? (
          <>
            <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2.5">
              <Button variant="ghost" size="sm" className="h-7 px-1.5 md:hidden" onClick={() => onSelect(null)} aria-label="返回会话列表">
                <ArrowLeft className="h-4 w-4" />
              </Button>
              <KindIcon kind={selected.kind} />
              <h2 className="min-w-0 flex-1 truncate text-sm font-semibold text-text-primary">{selected.name}</h2>
              <a
                href={slackInboxApi.exportUrl(selected.id, 'md')}
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-text-secondary hover:bg-bg-hover"
                title="导出最近 200 条消息（含 thread）为 Markdown"
              >
                <Download className="h-3.5 w-3.5" /> Markdown
              </a>
              <a
                href={slackInboxApi.exportUrl(selected.id, 'json')}
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-text-secondary hover:bg-bg-hover"
                title="导出最近 200 条消息（含 thread）为 JSON"
              >
                <Download className="h-3.5 w-3.5" /> JSON
              </a>
            </div>
            <div ref={streamRef} className="min-h-0 flex-1 overflow-auto">
              <MessageStream key={selected.id} conversation={selected} scrollRef={streamRef} />
            </div>
          </>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-text-muted">选择左侧的会话查看消息</div>
        )}
      </section>
    </div>
  );
}
