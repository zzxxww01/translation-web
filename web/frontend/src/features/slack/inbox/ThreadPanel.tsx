import { useEffect, useMemo, useRef, useState } from 'react';
import { ExternalLink, Loader2, Sparkles, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SlackAgentPanel } from '../agent/SlackAgentPanel';
import { useMessageZh, useShowZh, useThreadSummary } from './ai';
import { MessageItem } from './MessageItem';
import { ZhToggle } from './ZhToggle';
import { useMarkThreadRead, usePageVisible, useSlackReplies } from './hooks';
import { buildStream, emojify, newestTs } from './lib';

interface ThreadPanelProps {
  channelId: string;
  channelName: string;
  threadTs: string;
  onClose: () => void;
  onOpenChannel: () => void;
  /** 打开就生成中文摘要（「动态」页）；否则点按钮才生成 */
  autoSummary?: boolean;
}

/** 右栏 thread：根消息 + 全部回复；看到就记为已读（只记在 momo 本地）。 */
export function ThreadPanel({ channelId, channelName, threadTs, onClose, onOpenChannel, autoSummary = false }: ThreadPanelProps) {
  // 默认先看消息；切到「AI 翻译」才加载 AI（点「开始」才真正启动）
  const [tab, setTab] = useState<'ai' | 'messages'>('messages');
  const [aiOpened, setAiOpened] = useState(false);
  const openTab = (id: 'ai' | 'messages') => {
    setTab(id);
    if (id === 'ai') setAiOpened(true);
  };
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
  const showZh = useShowZh(state => state.showZh);
  const zh = useMessageZh(data?.messages ?? [], showZh && tab === 'messages');
  // 摘要：「动态」页打开就生成，其余点了才生成（后端按最新回复缓存，同一版本的 thread 只花一次）
  const [wantSummary, setWantSummary] = useState(autoSummary);
  const summary = useThreadSummary(channelId, threadTs, newest, wantSummary);
  const { mutate: mark } = markThread;
  const markedTs = useRef<string | null>(null);
  useEffect(() => {
    // momo 本地记已读，没参与的 thread 也记，下次打开才有「新回复」线
    if (!pageVisible || !newest || !data) return;
    if (markedTs.current === newest || (data.last_read && parseFloat(newest) <= parseFloat(data.last_read))) return;
    markedTs.current = newest;
    mark({ channelId, threadTs, ts: newest });
  }, [pageVisible, newest, data, channelId, threadTs, mark]);

  return (
    <>
      <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2.5">
        <div className="min-w-0 flex-1">
          <div className="truncate text-[15px] font-bold text-text-primary" title={root?.text}>
            {root ? emojify((root.text || '').split('\n').map(line => line.trim()).find(Boolean) || 'Thread') : 'Thread'}
          </div>
          <div className="truncate text-xs text-text-muted">
            {root ? `${root.user_name} 发起 · ` : ''}
            <button type="button" onClick={onOpenChannel} className="hover:text-primary-700 hover:underline" title="在整个频道里看">
              {channelName}
            </button>
          </div>
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
      <div className="flex shrink-0 gap-1 border-b border-border-subtle px-3" role="tablist" aria-label="thread 视图">
        {([['messages', `消息${rest.length ? ` · ${rest.length + 1}` : ''}`], ['ai', 'AI 翻译']] as const).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            onClick={() => openTab(id)}
            className={cn(
              'relative inline-flex items-center gap-1 px-2.5 py-2 text-[13px] after:absolute after:inset-x-2 after:-bottom-px after:h-0.5 after:rounded-full',
              tab === id ? 'font-medium text-text-primary after:bg-primary-500' : 'text-text-muted hover:text-text-primary'
            )}
          >
            {id === 'ai' && <Sparkles className="h-3.5 w-3.5 text-primary-500" />}
            {label}
          </button>
        ))}
        {tab === 'messages' && <div className="ml-auto flex items-center"><ZhToggle loading={zh.loading} failed={zh.failed} /></div>}
      </div>
      {/* 打开过 AI 页之后一直挂着（切回消息页也在后台跑），只是隐藏 */}
      {aiOpened && <div className={cn('min-h-0 flex-1', tab === 'ai' ? 'flex flex-col' : 'hidden')}>
        <SlackAgentPanel
          key={`${channelId}-${threadTs}`}
          channelId={channelId}
          threadTs={threadTs}
          latestTs={newest}
          slackLink={root?.permalink ?? null}
        />
      </div>}
      <div className={cn('min-h-0 flex-1 overflow-auto pb-4 pt-2', tab !== 'messages' && 'hidden')}>
        {replies.isLoading && <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}
        {replies.isError && (
          <div className="p-4 text-sm text-error">
            thread 没加载出来：{replies.error.message}
            <button type="button" onClick={() => void replies.refetch()} className="ml-2 text-primary-700 hover:underline">重试</button>
          </div>
        )}
        {!wantSummary && rest.length >= 3 && (
          <div className="mx-4 mb-2">
            <button
              type="button"
              onClick={() => setWantSummary(true)}
              className="inline-flex items-center gap-1 rounded-md border border-primary-100 bg-primary-50/50 px-2 py-1 text-xs text-primary-700 hover:bg-primary-50"
            >
              <Sparkles className="h-3.5 w-3.5" /> 用中文总结这个 thread
            </button>
          </div>
        )}
        {summary.isError && <div className="mx-4 mb-2 text-xs text-error">总结失败：{summary.error.message}</div>}
        {(summary.data || summary.isLoading) && (
          <div className="mx-4 mb-2 rounded-lg border border-primary-100 bg-primary-50/50 px-3 py-2 text-[13px] leading-relaxed text-text-primary">
            <div className="mb-0.5 flex items-center gap-1 text-xs font-semibold text-primary-700">
              <Sparkles className="h-3.5 w-3.5" /> {summary.data?.title || '在聊什么'}
              {summary.isLoading && <Loader2 className="h-3 w-3 animate-spin" />}
            </div>
            {summary.data?.summary}
            {summary.data?.todo_for_me && (
              <div className="mt-1 rounded bg-amber-50 px-2 py-1 text-amber-900">要你做：{summary.data.todo_for_me}</div>
            )}
          </div>
        )}
        {root && (
          <>
            <MessageItem message={root} zh={showZh ? zh.zh.get(root.ts) : null} />
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
                <MessageItem message={item.message} compact={item.compact} zh={showZh ? zh.zh.get(item.message.ts) : null} />
              </div>
            ))}
          </>
        )}
      </div>
    </>
  );
}
