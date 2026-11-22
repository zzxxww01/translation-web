import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AppWindow, CheckCircle2, ExternalLink, FileText, Languages, Loader2, RefreshCw, Sparkles, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { draftKeys, draftsApi } from '@/features/post/drafts';
import { useThreadSummary, useThreadZh } from './ai';
import { MessageItem } from './MessageItem';
import { useMarkThreadRead, usePageVisible, useSlackReplies } from './hooks';
import { buildStream, emojify, newestTs, stripLeadingMentions } from './lib';
import { stripMrkdwn } from './mrkdwn';
import { SlackMarkdown } from './SlackText';

interface ThreadPanelProps {
  channelId: string;
  channelName: string;
  threadTs: string;
  onClose: () => void;
  onOpenChannel: () => void;
  /** 进入翻译模式（三栏：原文 + 配图 | 译文 / 优化 / 标题 | 原 thread） */
  onTranslatePost: () => void;
  /** slack:// 链接：在 Slack App 里打开 thread 所在的频道（深链定位不到 thread 本身） */
  appLink?: string | null;
}

// 回复数达到这个才在打开时自动总结；少于它的点按钮才总结（2026-11-22 用户定）
const AUTO_SUMMARY_MIN_REPLIES = 3;

/** 中栏的 thread：顶部一排操作（翻译这个帖子 / 翻译全部 / 总结），下面是「在聊什么」和完整对话。 */
export function ThreadPanel({ channelId, channelName, threadTs, onClose, onOpenChannel, onTranslatePost, appLink }: ThreadPanelProps) {
  const replies = useSlackReplies(channelId, threadTs);
  const markThread = useMarkThreadRead();
  const pageVisible = usePageVisible();
  const draft = useQuery({
    queryKey: draftKeys.slack(channelId, threadTs),
    queryFn: () => draftsApi.slack(channelId, threadTs),
    select: data => data.draft,
    staleTime: 15_000,
  });

  // 「新回复」线停在第一次加载时的已读位置
  const [lastReadAtOpen, setLastReadAtOpen] = useState<string | null | undefined>(undefined);
  const data = replies.data;
  if (data && lastReadAtOpen === undefined) setLastReadAtOpen(data.last_read);

  const messages = useMemo(() => data?.messages ?? [], [data]);
  const root = messages[0];
  const rest = useMemo(() => messages.slice(1), [messages]);
  const stream = useMemo(() => buildStream(rest, lastReadAtOpen ?? null), [rest, lastReadAtOpen]);
  const newest = newestTs(messages);
  const rootText = root?.text ?? '';

  // 翻译全部：只对这个 thread、不记住；根帖作为背景
  const [translateAll, setTranslateAll] = useState(false);
  const zh = useThreadZh(messages, translateAll, rootText);

  // 摘要：回复 ≥ 3 条打开就总结一次；之后来了新回复只提示，点了才按最新内容重算
  const [summaryTs, setSummaryTs] = useState<string | null>(null);
  if (data && summaryTs === null && rest.length >= AUTO_SUMMARY_MIN_REPLIES && newest) setSummaryTs(newest);
  const summary = useThreadSummary(channelId, threadTs, summaryTs, !!summaryTs);
  const newSinceSummary = summaryTs ? messages.filter(m => parseFloat(m.ts) > parseFloat(summaryTs)).length : 0;

  const { mutate: mark } = markThread;
  const markedTs = useRef<string | null>(null);
  useEffect(() => {
    // 翻译服务本地记已读，没参与的 thread 也记，下次打开才有「新回复」线
    if (!pageVisible || !newest || !data) return;
    if (markedTs.current === newest || (data.last_read && parseFloat(newest) <= parseFloat(data.last_read))) return;
    markedTs.current = newest;
    mark({ channelId, threadTs, ts: newest });
  }, [pageVisible, newest, data, channelId, threadTs, mark]);

  const title = root
    ? emojify(stripMrkdwn(stripLeadingMentions((root.text || '').split('\n').map(line => line.trim()).find(Boolean) || 'Thread')))
    : 'Thread';
  const d = draft.data;
  const noPost = d?.extraction?.has_post === false;
  const draftLabel = !d
    ? '翻译这个帖子'
    : noPost
      ? '没有要翻的帖子 · 查看'
      : d.status === 'done'
        ? `已完成 · v${d.state.versions.length}`
        : `查看翻译 · v${d.state.versions.length}`;

  return (
    <>
      <div className="flex items-start gap-2 border-b border-border-subtle bg-white/70 px-5 pb-3 pt-3">
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-[16px] font-semibold text-text-primary" title={root?.text}>{title}</h2>
          <div className="mt-0.5 truncate text-xs text-text-muted">
            {root ? `${root.user_name} 发起 · ` : ''}
            <button type="button" onClick={onOpenChannel} className="hover:text-primary-700 hover:underline" title="在整个频道里看">
              {channelName}
            </button>
            {rest.length ? ` · ${rest.length} 条回复` : ' · 还没人回复'}
          </div>
        </div>
        {appLink && (
          <a href={appLink} className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary"
            title={`在 Slack App 里打开 ${channelName}（定位不到这个 thread，要精确到 thread 用旁边的网页链接）`} aria-label="在 Slack App 打开频道">
            <AppWindow className="h-4 w-4" />
          </a>
        )}
        {root && (
          <a href={root.permalink} target="_blank" rel="noreferrer noopener"
            className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary" title="在 Slack 里打开" aria-label="在 Slack 里打开">
            <ExternalLink className="h-4 w-4" />
          </a>
        )}
        <button type="button" onClick={onClose} className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary" aria-label="关闭 thread">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* 操作条：主操作「翻译这个帖子」最醒目，另外两个是读懂 thread 用的 */}
      <div className="flex flex-wrap items-center gap-2 border-b border-border-subtle px-5 py-2.5">
        <button
          type="button"
          onClick={onTranslatePost}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium shadow-sm transition-colors',
            d?.status === 'done'
              ? 'border border-success/30 bg-success/10 text-success hover:bg-success/15'
              : 'bg-primary-500 text-white hover:bg-primary-600'
          )}
        >
          {d?.status === 'done' ? <CheckCircle2 className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
          {draftLabel}
        </button>
        <button
          type="button"
          onClick={() => setTranslateAll(v => !v)}
          disabled={!messages.length}
          className={cn(
            'inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm transition-colors',
            translateAll ? 'border-primary-200 bg-primary-50 text-primary-700' : 'border-border-subtle bg-white text-text-secondary hover:bg-bg-hover'
          )}
          title={translateAll ? '收起中文，只看原文' : '把这个 thread 的所有消息翻成中文（只对这个 thread 有效）'}
        >
          {zh.loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Languages className="h-4 w-4" />}
          {translateAll ? (zh.loading ? '翻译中…' : '收起中文') : '翻译全部'}
        </button>
        <button
          type="button"
          onClick={() => setSummaryTs(newest)}
          disabled={!newest || summary.isFetching}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border-subtle bg-white px-3 py-1.5 text-sm text-text-secondary transition-colors hover:bg-bg-hover disabled:opacity-60"
          title="用中文总结这个 thread 在聊什么"
        >
          {summary.isFetching ? <Loader2 className="h-4 w-4 animate-spin" /> : summaryTs ? <RefreshCw className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
          {summaryTs ? '重新总结' : '总结一下'}
        </button>
        {zh.failed && <span className="text-xs text-error">有一部分没翻出来，稍后再点一次</span>}
      </div>

      <div className="min-h-0 flex-1 overflow-auto pb-6 pt-3">
        {replies.isLoading && <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}
        {replies.isError && (
          <div className="p-4 text-sm text-error">
            thread 没加载出来：{replies.error.message}
            <button type="button" onClick={() => void replies.refetch()} className="ml-2 text-primary-700 hover:underline">重试</button>
          </div>
        )}
        {summaryTs && (
          <div className="mx-5 mb-3 rounded-xl border border-primary-100 bg-gradient-to-br from-primary-50/80 to-white px-4 py-3 text-[13px] leading-relaxed text-text-primary shadow-sm">
            <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-primary-700">
              <Sparkles className="h-3.5 w-3.5" /> 在聊什么
              {summary.isFetching && <Loader2 className="h-3 w-3 animate-spin" />}
              {newSinceSummary > 0 && !summary.isFetching && (
                <button type="button" onClick={() => setSummaryTs(newest)} className="ml-auto font-normal text-primary-700 hover:underline">
                  有 {newSinceSummary} 条新回复 · 点这里更新
                </button>
              )}
            </div>
            {summary.isError && <div className="text-xs text-error">总结失败：{summary.error.message}</div>}
            {summary.data?.summary && <SlackMarkdown text={summary.data.summary} />}
            {summary.data?.todo_for_me && (
              <div className="mt-2 rounded-md bg-amber-50 px-2.5 py-1.5 text-amber-900">要你做：{summary.data.todo_for_me}</div>
            )}
          </div>
        )}
        {root && (
          <>
            <MessageItem message={root} zh={translateAll ? zh.zh : null} />
            <div className="my-2 flex items-center gap-2 px-5 text-xs text-text-muted">
              <span>{rest.length ? `${rest.length} 条回复` : '还没人回复'}</span>
              <div className="h-px flex-1 bg-border-subtle" />
            </div>
            {stream.map(item => (
              <div key={item.message.ts}>
                {item.firstUnread && (
                  <div className="my-1 flex items-center gap-2 px-5 text-[11px] font-semibold text-error">
                    <div className="h-px flex-1 bg-error/60" />新回复<div className="h-px flex-1 bg-error/60" />
                  </div>
                )}
                <MessageItem message={item.message} compact={item.compact} zh={translateAll ? zh.zh : null} context={rootText} />
              </div>
            ))}
          </>
        )}
      </div>
    </>
  );
}
