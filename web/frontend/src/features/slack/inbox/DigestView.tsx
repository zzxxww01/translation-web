import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Hash, Loader2, MessageCircle, MessagesSquare, RefreshCw, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { slackInboxApi } from './api';
import { clockTime, dayLabel } from './lib';
import type { SlackDigestSection } from './types';

interface DigestViewProps {
  onOpen: (channelId: string, threadTs: string | null) => void;
  onBack: () => void;
}

function SectionIcon({ section }: { section: SlackDigestSection }) {
  const cls = 'h-4 w-4 shrink-0 text-text-muted';
  if (section.kind === 'thread') return <MessagesSquare className={cls} />;
  if (section.kind === 'im' || section.kind === 'mpim') return <MessageCircle className={cls} />;
  return <Hash className={cls} />;
}

/** 「AI 速览」：所有未读按会话 / thread 各一段中文摘要，@我和要我做事的排前面。只读，不会标已读。 */
export function DigestView({ onOpen, onBack }: DigestViewProps) {
  const digest = useQuery({
    queryKey: ['slack-inbox', 'digest'],
    queryFn: slackInboxApi.digest,
    staleTime: 5 * 60_000,
    select: data => data.sections,
  });

  return (
    <>
      <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2.5">
        <Button variant="ghost" size="sm" className="h-7 px-1.5 md:hidden" onClick={onBack} aria-label="返回会话列表">
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <Sparkles className="h-4 w-4 text-primary-500" />
        <h2 className="flex-1 text-[15px] font-bold text-text-primary">AI 速览</h2>
        <span className="hidden text-xs text-text-muted sm:inline">只看不标已读</span>
        <Button variant="outline" size="sm" className="h-7" onClick={() => void digest.refetch()} disabled={digest.isFetching}>
          <RefreshCw className={cn('h-3.5 w-3.5', digest.isFetching && 'animate-spin')} /> 重新整理
        </Button>
      </div>
      <div className="min-h-0 flex-1 space-y-3 overflow-auto bg-bg-tertiary/40 p-4">
        {digest.isLoading && (
          <div className="flex flex-col items-center gap-2 py-10 text-sm text-text-muted">
            <Loader2 className="h-5 w-5 animate-spin" /> 正在读未读消息并整理成中文…
          </div>
        )}
        {digest.isError && <div className="text-sm text-error">整理失败：{digest.error.message}</div>}
        {digest.data?.length === 0 && (
          <div className="py-10 text-center text-sm text-text-muted">没有未读消息，都看完了 🎉</div>
        )}
        {digest.data?.map(section => (
          <div
            key={`${section.conversation_id}-${section.thread_ts ?? ''}`}
            className={cn(
              'rounded-lg border bg-white p-3 shadow-sm',
              section.mentions_me || section.todo_for_me ? 'border-amber-300' : 'border-border-subtle'
            )}
          >
            <button
              type="button"
              onClick={() => onOpen(section.conversation_id, section.thread_ts)}
              className="flex w-full items-center gap-1.5 text-left"
            >
              <SectionIcon section={section} />
              <span className="min-w-0 flex-1 truncate text-sm font-semibold text-text-primary hover:text-primary-700">
                {section.kind === 'thread' ? `${section.name} 的 thread` : section.name}
              </span>
              {section.mentions_me && <span className="rounded-full bg-error px-1.5 text-[11px] font-semibold text-white">@我</span>}
              <span className="shrink-0 text-xs text-text-muted">
                {section.unread_count} 条未读 · {dayLabel(section.latest_ts)} {clockTime(section.latest_ts)}
              </span>
            </button>
            {section.error ? (
              <div className="mt-1.5 text-xs text-error">{section.error}，点标题直接去看</div>
            ) : (
              <>
                {section.summary && <div className="mt-1.5 text-sm text-text-primary">{section.summary}</div>}
                {section.todo_for_me && (
                  <div className="mt-1.5 rounded bg-amber-50 px-2 py-1 text-[13px] text-amber-900">要你做：{section.todo_for_me}</div>
                )}
                {section.items && section.items.length > 0 && (
                  <ul className="mt-1.5 space-y-1">
                    {section.items.map((item, i) => (
                      <li key={i} className="flex gap-1.5 text-[13px] text-text-secondary">
                        <span className="text-text-muted">·</span>
                        <button
                          type="button"
                          onClick={() => onOpen(section.conversation_id, section.thread_ts)}
                          className="text-left hover:text-primary-700 hover:underline"
                        >
                          {item.text}
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
