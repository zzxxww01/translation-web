import { useState } from 'react';
import { ExternalLink, FileDown, Languages, Loader2, MessageSquareText } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useOneZh } from './ai';
import { clockTime, emojiFor } from './lib';
import { SlackMarkdown, SlackText } from './SlackText';
import type { SlackMessage } from './types';

// 不加载 Slack 头像图：slack-edge.com 在国内常常打不开，直接用名字首字母
export function Avatar({ name, size = 'md' }: { name: string; size?: 'sm' | 'md' }) {
  return (
    <div className={cn(
      'flex shrink-0 items-center justify-center rounded-md bg-primary-100 font-medium text-primary-700',
      size === 'sm' ? 'h-5 w-5 text-[11px]' : 'h-9 w-9 text-sm'
    )}>
      {name.slice(0, 1).toUpperCase()}
    </div>
  );
}

/** 点了「译」的单条消息：现翻这一条（后端有缓存）。 */
function OnDemandZh({ text }: { text: string }) {
  const zh = useOneZh(text, true);
  if (zh.isLoading) return <div className="mt-0.5 flex items-center gap-1 pl-2 text-xs text-text-muted"><Loader2 className="h-3 w-3 animate-spin" /> 翻译中…</div>;
  if (zh.isError) return <div className="mt-0.5 pl-2 text-xs text-error">翻译失败：{zh.error.message}</div>;
  if (!zh.data) return <div className="mt-0.5 pl-2 text-xs text-text-muted">这条不需要翻译</div>;
  return <ZhLine zh={zh.data} />;
}

function ZhLine({ zh }: { zh: string }) {
  return (
    // AI 中文：紧跟在原文下面，灰色小一号，和原文一眼区分开
    <SlackMarkdown text={zh} lang="zh" className="mt-0.5 border-l-2 border-primary-100 pl-2 text-[13px] leading-relaxed text-text-secondary" />
  );
}

function MessageBody({ message, zh, askedZh }: { message: SlackMessage; zh?: string | null; askedZh: boolean }) {
  return (
    <>
      {message.segments.length > 0 && <SlackText segments={message.segments} />}
      {!zh && askedZh && <OnDemandZh text={message.text} />}
      {zh && <ZhLine zh={zh} />}
      {message.files.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {message.files.map(file =>
            file.is_image ? (
              <a key={file.id} href={file.url} target="_blank" rel="noreferrer" title={file.name} className="max-w-full sm:max-w-sm">
                <img
                  src={file.url}
                  alt={file.name}
                  loading="lazy"
                  className="max-h-72 w-auto max-w-full rounded-md border border-border-subtle bg-bg-tertiary object-contain"
                />
              </a>
            ) : (
              <a
                key={file.id}
                href={`${file.url}?download=true`}
                className="inline-flex items-center gap-1.5 rounded-md border border-border-subtle px-2.5 py-1.5 text-xs text-text-secondary hover:bg-bg-hover"
                title="下载附件（超过 25MB 的请到 Slack 原文里看）"
              >
                <FileDown className="h-3.5 w-3.5" />
                {file.name}
              </a>
            )
          )}
        </div>
      )}
      {message.attachments.filter(a => a.title || a.text).map((a, i) => (
        <div key={i} className="mt-2 border-l-2 border-border pl-3 text-[13px] text-text-secondary">
          {a.service_name && <div className="text-xs text-text-muted">{a.service_name}</div>}
          {a.title && (a.title_link ? (
            <a href={a.title_link} target="_blank" rel="noreferrer noopener" className="font-medium text-primary-700 hover:underline">{a.title}</a>
          ) : <div className="font-medium">{a.title}</div>)}
          {a.segments?.length
            ? <SlackText segments={a.segments} className="mt-0.5 line-clamp-4 text-[13px] text-text-secondary" />
            : a.text && <SlackMarkdown text={a.text} className="mt-0.5 line-clamp-4" />}
        </div>
      ))}
      {message.reactions.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {message.reactions.map(r => (
            <span key={r.name} className="rounded-full border border-border-subtle bg-bg-tertiary px-1.5 py-0.5 text-[11px] text-text-secondary" title={`:${r.name}:`}>
              {emojiFor(r.name)} {r.count}
            </span>
          ))}
        </div>
      )}
    </>
  );
}

interface MessageItemProps {
  message: SlackMessage;
  /** 同一个人连发的后续消息：不重复头像和名字 */
  compact?: boolean;
  /** 传了就显示「在 thread 里看回复」入口 */
  onOpenThread?: (threadTs: string) => void;
  /** 当前在右栏打开的 thread，高亮它的根消息 */
  active?: boolean;
  /** AI 翻的中文（开了「显示中文」且需要翻时才有） */
  zh?: string | null;
}

export function MessageItem({ message, compact = false, onOpenThread, active = false, zh }: MessageItemProps) {
  const isThreadRoot = message.reply_count > 0 && message.thread_ts === message.ts;
  // 没开「全部中文」时，单条点「译」才翻
  const [askedZh, setAskedZh] = useState(false);
  // 触屏没有悬停：点一下消息（不是点链接 / 按钮）切换工具条
  const [toolsOpen, setToolsOpen] = useState(false);
  const onTap = (e: React.MouseEvent) => {
    if (!window.matchMedia?.('(hover: none)').matches) return;
    if ((e.target as HTMLElement).closest('a, button')) return;
    setToolsOpen(v => !v);
  };
  return (
    <div
      onClick={onTap}
      className={cn(
        'group relative flex gap-2.5 px-5 transition-colors',
        compact ? 'py-0.5' : 'pt-2 pb-1',
        // 和 Slack 一样，@我 的消息用浅色底 + 左侧色条标出来
        message.mentions_me ? 'border-l-2 border-amber-400 bg-amber-50/70 pl-[18px] hover:bg-amber-50' : 'hover:bg-bg-hover/60',
        active && 'bg-primary-50/70'
      )}
    >
      {compact ? (
        <div className="w-9 shrink-0 pt-0.5 text-right text-[10px] leading-5 text-text-muted opacity-0 group-hover:opacity-100">
          {clockTime(message.ts)}
        </div>
      ) : (
        <Avatar name={message.user_name} />
      )}
      <div className="min-w-0 flex-1">
        {!compact && (
          <div className="flex items-baseline gap-2">
            <span className="text-[15px] font-bold text-text-primary">{message.user_name}</span>
            <span className="text-xs text-text-muted" title={message.time}>{clockTime(message.ts)}{message.edited ? ' · 已编辑' : ''}</span>
          </div>
        )}
        <MessageBody message={message} zh={zh} askedZh={askedZh} />
        {isThreadRoot && onOpenThread && (
          <button
            type="button"
            onClick={() => onOpenThread(message.ts)}
            className="mt-1 inline-flex items-center gap-1.5 rounded-md border border-transparent px-1 py-0.5 text-xs hover:border-border-subtle hover:bg-white"
          >
            <span className="font-semibold text-primary-700">{message.reply_count} 条回复</span>
            {message.latest_reply && <span className="text-text-muted">最后回复 {clockTime(message.latest_reply)}</span>}
          </button>
        )}
      </div>
      {/* 悬停工具条，和 Slack 一样浮在消息右上角 */}
      <div className={cn(
        'absolute -top-3 right-4 items-center gap-0.5 rounded-md border border-border-subtle bg-white p-0.5 shadow-sm group-hover:flex',
        toolsOpen ? 'flex' : 'hidden'
      )}>
        {!zh && message.text.trim() && (
          <button
            type="button"
            onClick={() => setAskedZh(v => !v)}
            className={cn('rounded p-1 hover:bg-bg-hover hover:text-text-primary', askedZh ? 'text-primary-700' : 'text-text-muted')}
            title={askedZh ? '收起中文' : '翻译这条'}
            aria-label={askedZh ? '收起中文' : '翻译这条'}
          >
            <Languages className="h-4 w-4" />
          </button>
        )}
        {onOpenThread && (
          <button
            type="button"
            onClick={() => onOpenThread(message.thread_ts || message.ts)}
            className="rounded p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary"
            title="在 thread 里查看"
            aria-label="在 thread 里查看"
          >
            <MessageSquareText className="h-4 w-4" />
          </button>
        )}
        <a
          href={message.permalink}
          target="_blank"
          rel="noreferrer noopener"
          className="rounded p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary"
          title="在 Slack 里打开"
          aria-label="在 Slack 里打开"
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      </div>
    </div>
  );
}
