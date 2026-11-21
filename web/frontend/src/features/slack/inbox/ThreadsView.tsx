import { ArrowLeft, Hash, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { Avatar } from './MessageItem';
import { useSlackThreads } from './hooks';
import { clockTime, dayLabel, emojify, threadTitle } from './lib';
import { stripMrkdwn } from './mrkdwn';
import type { SlackConversation } from './types';
import type { OpenThread } from './Sidebar';

interface ThreadsViewProps {
  conversations: SlackConversation[];
  openThread: OpenThread | null;
  onOpenThread: (thread: OpenThread) => void;
  onBack: () => void;
}

/** 「Threads」汇总页：我参与的 thread，有新回复的在前面，每个 thread 显示根消息和最新的回复。 */
export function ThreadsView({ conversations, openThread, onOpenThread, onBack }: ThreadsViewProps) {
  const threads = useSlackThreads(true);
  const names = new Map(conversations.map(c => [c.id, c.name]));

  return (
    <>
      <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2.5">
        <Button variant="ghost" size="sm" className="h-7 px-1.5 md:hidden" onClick={onBack} aria-label="返回会话列表">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h2 className="flex-1 text-[15px] font-bold text-text-primary">Threads</h2>
        <span className="text-xs text-text-muted">我参与的 thread</span>
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-auto bg-bg-tertiary/40 p-4">
        {threads.isLoading && <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}
        {threads.isError && <div className="text-sm text-error">加载失败：{threads.error.message}</div>}
        {threads.data?.length === 0 && <div className="text-sm text-text-muted">还没有参与过的 thread</div>}
        {threads.data?.map(t => {
          const active = openThread?.channelId === t.channel_id && openThread.threadTs === t.thread_ts;
          const shownReplies = t.latest_replies.slice(-2);
          return (
            <button
              key={`${t.channel_id}-${t.thread_ts}`}
              type="button"
              onClick={() => onOpenThread({ channelId: t.channel_id, threadTs: t.thread_ts })}
              className={cn(
                'block w-full rounded-lg border bg-white p-3 text-left shadow-sm transition-colors hover:border-primary-200',
                active ? 'border-primary-500' : 'border-border-subtle'
              )}
            >
              <div className="mb-2 flex items-center gap-1.5 text-xs text-text-muted">
                <Hash className="h-3.5 w-3.5" />
                <span className="font-medium text-text-secondary">{names.get(t.channel_id) ?? t.channel_id}</span>
                <span>·</span>
                <span className={cn('min-w-0 flex-1 truncate', t.has_unreads && 'font-semibold text-text-primary')}>{threadTitle(t, 60)}</span>
                {t.mentions_me && <span className="rounded-full bg-error px-1.5 text-[11px] font-semibold text-white">@我</span>}
                {t.has_unreads && <span className="rounded-full bg-primary-500 px-1.5 text-[11px] font-semibold text-white">新回复</span>}
              </div>
              <div className="flex gap-2.5">
                <Avatar name={t.root.user_name} />
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-bold text-text-primary">{t.root.user_name}</div>
                  {/* 卡片整体是按钮，里面不能再放链接，所以用纯文本 */}
                  <div className="line-clamp-3 whitespace-pre-wrap text-sm text-text-primary">{emojify(stripMrkdwn(t.root.text))}</div>
                </div>
              </div>
              {shownReplies.length > 0 && (
                <div className="mt-2 space-y-1.5 border-l-2 border-border-subtle pl-3">
                  {shownReplies.map(r => (
                    <div key={r.ts} className={cn('text-[13px]', r.mentions_me && 'rounded bg-amber-50')}>
                      <span className="font-semibold text-text-primary">{r.user_name}</span>
                      <span className="ml-1.5 text-text-muted">{clockTime(r.ts)}</span>
                      <div className="line-clamp-2 text-text-secondary">{emojify(stripMrkdwn(r.text))}</div>
                    </div>
                  ))}
                </div>
              )}
              <div className="mt-2 text-xs text-primary-700">
                {t.reply_count} 条回复{t.latest_reply ? ` · 最后回复 ${dayLabel(t.latest_reply)} ${clockTime(t.latest_reply)}` : ''}
              </div>
            </button>
          );
        })}
      </div>
    </>
  );
}
