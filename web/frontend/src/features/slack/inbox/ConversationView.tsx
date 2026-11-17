import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, Download, Hash, Loader2, Lock, Sparkles, Users } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { slackInboxApi } from './api';
import { useMessageZh, useShowZh } from './ai';
import { MessageItem } from './MessageItem';
import { ZhToggle } from './ZhToggle';
import { useMarkRead, usePageVisible, useSlackMessages } from './hooks';
import { buildStream, newestTs } from './lib';
import type { SlackConversation } from './types';

function Divider({ label, tone }: { label: string; tone: 'day' | 'new' }) {
  return (
    <div className={cn('relative my-2 flex items-center px-5', tone === 'new' ? 'text-error' : 'text-text-muted')}>
      <div className={cn('h-px flex-1', tone === 'new' ? 'bg-error/60' : 'bg-border-subtle')} />
      <span className={cn(
        'mx-2 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold',
        tone === 'new' ? 'border-error/40 bg-white' : 'border-border-subtle bg-white'
      )}>
        {label}
      </span>
      <div className={cn('h-px flex-1', tone === 'new' ? 'bg-error/60' : 'bg-border-subtle')} />
    </div>
  );
}

interface ConversationViewProps {
  conversation: SlackConversation;
  activeThreadTs: string | null;
  onOpenThread: (threadTs: string) => void;
  onBack: () => void;
  /** 私信：窄屏上切到右栏的 AI 回复 */
  onOpenAgent?: () => void;
}

export function ConversationView({ conversation, activeThreadTs, onOpenThread, onBack, onOpenAgent }: ConversationViewProps) {
  const query = useSlackMessages(conversation.id);
  const markRead = useMarkRead();
  const pageVisible = usePageVisible();
  const scrollRef = useRef<HTMLDivElement>(null);
  const newLineRef = useRef<HTMLDivElement>(null);

  // 「新消息」线停在打开会话时的已读位置；标记已读后也不挪，直到切走（和 Slack 一样）
  const [lastReadAtOpen] = useState(conversation.last_read);

  // 接口按新→旧返回；页面按 Slack 习惯旧的在上、新的在下，「加载更早」放顶部
  const messages = useMemo(
    () => (query.data?.pages.flatMap(page => page.messages) ?? []).slice().reverse(),
    [query.data]
  );
  const stream = useMemo(() => buildStream(messages, lastReadAtOpen), [messages, lastReadAtOpen]);
  const showZh = useShowZh(state => state.showZh);
  const zh = useMessageZh(messages, showZh);

  // 打开时：有未读就停在「新消息」线，否则停在最底部；之后新消息到来时，只有本来就在底部才跟着滚
  const scrolled = useRef(false);
  const atBottom = useRef(true);
  useEffect(() => {
    const el = scrollRef.current;
    if (!el || messages.length === 0) return;
    if (!scrolled.current) {
      scrolled.current = true;
      const jump = () => {
        if (newLineRef.current) newLineRef.current.scrollIntoView({ block: 'center' });
        else el.scrollTop = el.scrollHeight;
      };
      jump();
      // 图片是懒加载的，撑开高度后再定位一次
      const timer = setTimeout(jump, 800);
      return () => clearTimeout(timer);
    }
    if (atBottom.current) el.scrollTop = el.scrollHeight;
  }, [messages]);

  // 看到了就在 Slack 里标已读
  const newest = newestTs(messages);
  const { mutate: mark } = markRead;
  // 同一条消息只发一次：Slack 那边已读位置更新有延迟，不能靠会话列表刷新来判断
  const markedTs = useRef<string | null>(null);
  useEffect(() => {
    if (!pageVisible || !newest || markedTs.current === newest) return;
    if (conversation.last_read && parseFloat(newest) <= parseFloat(conversation.last_read)) return;
    markedTs.current = newest;
    mark({ channelId: conversation.id, ts: newest });
  }, [pageVisible, newest, conversation.id, conversation.last_read, mark]);

  const KindIcon = conversation.kind === 'private' ? Lock : conversation.kind === 'mpim' ? Users : Hash;
  const isChannel = conversation.kind === 'channel' || conversation.kind === 'private';

  return (
    <>
      <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2.5">
        <Button variant="ghost" size="sm" className="h-7 px-1.5 md:hidden" onClick={onBack} aria-label="返回会话列表">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        {(isChannel || conversation.kind === 'mpim') && <KindIcon className="h-4 w-4 shrink-0 text-text-muted" />}
        <h2 className="min-w-0 flex-1 truncate text-[15px] font-bold text-text-primary">{conversation.name}</h2>
        <ZhToggle loading={zh.loading} failed={zh.failed} />
        {onOpenAgent && (
          <Button variant="outline" size="sm" className="h-7 lg:hidden" onClick={onOpenAgent}>
            <Sparkles className="h-3.5 w-3.5" /> AI 回复
          </Button>
        )}
        <a
          href={slackInboxApi.exportUrl(conversation.id, 'md')}
          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-text-secondary hover:bg-bg-hover"
          title="导出最近 200 条消息（含 thread）为 Markdown"
        >
          <Download className="h-3.5 w-3.5" /> 导出
        </a>
      </div>
      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-auto pb-4"
        onScroll={e => {
          const el = e.currentTarget;
          atBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        }}
      >
        {query.isLoading ? (
          <div className="flex h-full items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-text-muted" /></div>
        ) : query.isError ? (
          <div className="p-6 text-sm text-error">加载消息失败：{query.error.message}</div>
        ) : (
          <>
            {query.hasNextPage && (
              <div className="flex justify-center py-3">
                <Button variant="outline" size="sm" onClick={() => query.fetchNextPage()} disabled={query.isFetchingNextPage}>
                  {query.isFetchingNextPage ? '加载中…' : '加载更早的消息'}
                </Button>
              </div>
            )}
            {messages.length === 0 && <div className="px-5 py-6 text-sm text-text-muted">还没有消息</div>}
            {stream.map(item => (
              <div key={item.message.ts}>
                {item.day && <Divider label={item.day} tone="day" />}
                {item.firstUnread && <div ref={newLineRef}><Divider label="新消息" tone="new" /></div>}
                <MessageItem
                  message={item.message}
                  compact={item.compact}
                  onOpenThread={onOpenThread}
                  active={item.message.ts === activeThreadTs}
                  zh={showZh ? zh.zh.get(item.message.ts) : null}
                />
              </div>
            ))}
          </>
        )}
      </div>
    </>
  );
}
