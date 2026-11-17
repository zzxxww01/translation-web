import { useEffect, useMemo, useRef, useState } from 'react';
import { ExternalLink, Loader2, X } from 'lucide-react';
import { MessageItem } from './MessageItem';
import { useMarkThreadRead, usePageVisible, useSlackReplies } from './hooks';
import { buildStream, newestTs } from './lib';

interface ThreadPanelProps {
  channelId: string;
  channelName: string;
  threadTs: string;
  onClose: () => void;
  onOpenChannel: () => void;
}

/** 右栏 thread：根消息 + 全部回复；看到就在 Slack 里把这个 thread 标为已读。 */
export function ThreadPanel({ channelId, channelName, threadTs, onClose, onOpenChannel }: ThreadPanelProps) {
  const replies = useSlackReplies(channelId, threadTs);
  const markThread = useMarkThreadRead();
  const pageVisible = usePageVisible();

  // 「新回复」线停在第一次加载时的已读位置
  const [lastReadAtOpen, setLastReadAtOpen] = useState<string | null | undefined>(undefined);
  const data = replies.data;
  if (data && lastReadAtOpen === undefined) setLastReadAtOpen(data.last_read);

  const root = data?.messages[0];
  const rest = useMemo(() => data?.messages.slice(1) ?? [], [data]);
  const stream = useMemo(() => buildStream(rest, lastReadAtOpen ?? null), [rest, lastReadAtOpen]);

  const newest = newestTs(data?.messages ?? []);
  const { mutate: mark } = markThread;
  const markedTs = useRef<string | null>(null);
  useEffect(() => {
    if (!pageVisible || !newest || !data?.last_read) return; // 没参与的 thread Slack 不记已读
    if (markedTs.current === newest || parseFloat(newest) <= parseFloat(data.last_read)) return;
    markedTs.current = newest;
    mark({ channelId, threadTs, ts: newest });
  }, [pageVisible, newest, data?.last_read, channelId, threadTs, mark]);

  return (
    <>
      <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2.5">
        <div className="min-w-0 flex-1">
          <div className="text-[15px] font-bold text-text-primary">Thread</div>
          <button type="button" onClick={onOpenChannel} className="truncate text-xs text-text-muted hover:text-primary-700 hover:underline">
            {channelName}
          </button>
        </div>
        {root && (
          <a
            href={root.permalink}
            target="_blank"
            rel="noreferrer noopener"
            className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary"
            title="在 Slack 里打开"
            aria-label="在 Slack 里打开"
          >
            <ExternalLink className="h-4 w-4" />
          </a>
        )}
        <button type="button" onClick={onClose} className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary" aria-label="关闭 thread">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-auto pb-4 pt-2">
        {replies.isLoading && <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}
        {replies.isError && <div className="p-4 text-sm text-error">加载 thread 失败：{replies.error.message}</div>}
        {root && (
          <>
            <MessageItem message={root} />
            <div className="my-2 flex items-center gap-2 px-5 text-xs text-text-muted">
              <span>{rest.length} 条回复</span>
              <div className="h-px flex-1 bg-border-subtle" />
            </div>
            {stream.map(item => (
              <div key={item.message.ts}>
                {item.firstUnread && (
                  <div className="my-1 flex items-center gap-2 px-5 text-[11px] font-semibold text-error">
                    <div className="h-px flex-1 bg-error/60" />新回复<div className="h-px flex-1 bg-error/60" />
                  </div>
                )}
                <MessageItem message={item.message} compact={item.compact} />
              </div>
            ))}
          </>
        )}
      </div>
    </>
  );
}
