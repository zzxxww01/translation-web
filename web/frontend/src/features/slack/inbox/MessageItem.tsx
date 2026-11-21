import { useState } from 'react';
import { Check, Copy, ExternalLink, FileDown, Languages, Loader2, MessageSquareText, Plus } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { cardKey, piecesOf, useOneZh, type ZhMap } from './ai';
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

function ZhLine({ zh }: { zh: string }) {
  return (
    // AI 中文：紧贴原文下面，浅色底 + 左侧细线，和原文一眼区分开
    <SlackMarkdown
      text={zh}
      lang="zh"
      className="mt-1 rounded-r-md border-l-2 border-primary-300 bg-primary-50/50 px-2.5 py-1.5 text-[13px] leading-relaxed text-text-secondary"
    />
  );
}

/** 配图选择（Slack 翻译模式的原 thread 栏）：点图片加入 / 移出配图 */
export interface ImagePicker {
  selected: string[];
  onToggle: (fileId: string, name: string) => void;
}

function MessageBody({ message, zh, picker }: { message: SlackMessage; zh: ZhMap | null; picker?: ImagePicker }) {
  return (
    <>
      {message.segments.length > 0 && <SlackText segments={message.segments} />}
      {zh?.get(message.ts) && <ZhLine zh={zh.get(message.ts) as string} />}
      {message.files.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {message.files.map(file => {
            if (!file.is_image) {
              return (
                <a
                  key={file.id}
                  href={`${file.url}?download=true`}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border-subtle px-2.5 py-1.5 text-xs text-text-secondary hover:bg-bg-hover"
                  title="下载附件（超过 25MB 的请到 Slack 原文里看）"
                >
                  <FileDown className="h-3.5 w-3.5" />
                  {file.name}
                </a>
              );
            }
            const img = (
              <img
                src={file.url}
                alt={file.name}
                loading="lazy"
                className="max-h-72 w-auto max-w-full rounded-md border border-border-subtle bg-bg-tertiary object-contain"
              />
            );
            if (picker) {
              const order = picker.selected.indexOf(file.id);
              const chosen = order >= 0;
              return (
                <button
                  key={file.id}
                  type="button"
                  onClick={() => picker.onToggle(file.id, file.name)}
                  title={chosen ? '点一下从配图里去掉' : '点一下加入配图'}
                  className={cn(
                    'relative max-w-full rounded-lg p-0.5 transition sm:max-w-[240px]',
                    chosen ? 'ring-2 ring-primary-500' : 'opacity-80 hover:opacity-100 hover:ring-2 hover:ring-primary-200'
                  )}
                >
                  {img}
                  <span className={cn(
                    'absolute right-1.5 top-1.5 flex h-6 min-w-6 items-center justify-center rounded-full px-1 text-xs font-semibold shadow',
                    chosen ? 'bg-primary-500 text-white' : 'bg-white/90 text-text-secondary'
                  )}>
                    {chosen ? order + 1 : <Plus className="h-3.5 w-3.5" />}
                  </span>
                </button>
              );
            }
            return (
              <a key={file.id} href={file.url} target="_blank" rel="noreferrer" title={file.name} className="max-w-full sm:max-w-sm">
                {img}
              </a>
            );
          })}
        </div>
      )}
      {message.attachments.map((a, i) => (a.title || a.text) && (
        <div key={i} className="mt-2 rounded-r-md border-l-2 border-border bg-bg-tertiary/50 py-1.5 pl-3 pr-2 text-[13px] text-text-secondary">
          {a.service_name && <div className="text-xs text-text-muted">{a.service_name}</div>}
          {a.title && (a.title_link ? (
            <a href={a.title_link} target="_blank" rel="noreferrer noopener" className="font-medium text-primary-700 hover:underline">{a.title}</a>
          ) : <div className="font-medium">{a.title}</div>)}
          {a.segments?.length
            ? <SlackText segments={a.segments} className="mt-0.5 line-clamp-6 text-[13px] text-text-secondary" />
            : a.text && <SlackMarkdown text={a.text} className="mt-0.5 line-clamp-6" />}
          {zh?.get(cardKey(message.ts, i)) && <ZhLine zh={zh.get(cardKey(message.ts, i)) as string} />}
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

/** 点了「译」的单条消息：现翻这一条（正文 + 链接卡片），后端有缓存 */
function OnDemandBody({ message, context, picker }: { message: SlackMessage; context?: string | null; picker?: ImagePicker }) {
  const zh = useOneZh(message, true, context);
  return (
    <>
      <MessageBody message={message} zh={zh.zh} picker={picker} />
      {zh.loading && <div className="mt-1 flex items-center gap-1 text-xs text-text-muted"><Loader2 className="h-3 w-3 animate-spin" /> 翻译中…</div>}
      {zh.failed && <div className="mt-1 text-xs text-error">翻译失败，稍后再点一次「译」</div>}
      {zh.done && zh.zh.size === 0 && <div className="mt-1 text-xs text-text-muted">这条不需要翻译</div>}
    </>
  );
}

interface MessageItemProps {
  message: SlackMessage;
  /** 同一个人连发的后续消息：不重复头像和名字 */
  compact?: boolean;
  /** 传了就显示「在 thread 里看回复」入口 */
  onOpenThread?: (threadTs: string) => void;
  /** 高亮（当前打开的 thread 根消息 / 用来提取帖子原文的消息） */
  active?: boolean;
  /** thread「翻译全部」的结果；有它就不显示单条「译」 */
  zh?: ZhMap | null;
  /** thread 根帖：单条「译」时作为背景给模型 */
  context?: string | null;
  /** Slack 翻译模式：图片可点选为配图 */
  picker?: ImagePicker;
  /** 左侧竖线标记（翻译模式里「用来提取原文的消息」） */
  marked?: boolean;
}

export function MessageItem({ message, compact = false, onOpenThread, active = false, zh, context, picker, marked }: MessageItemProps) {
  const isThreadRoot = message.reply_count > 0 && message.thread_ts === message.ts;
  const [askedZh, setAskedZh] = useState(false);
  // 触屏没有悬停：点一下消息（不是点链接 / 按钮）切换工具条
  const [toolsOpen, setToolsOpen] = useState(false);
  const onTap = (e: React.MouseEvent) => {
    if (!window.matchMedia?.('(hover: none)').matches) return;
    if ((e.target as HTMLElement).closest('a, button')) return;
    setToolsOpen(v => !v);
  };
  const translatable = !zh && piecesOf(message).length > 0;
  return (
    <div
      onClick={onTap}
      className={cn(
        'group relative flex gap-2.5 px-5 transition-colors',
        compact ? 'py-0.5' : 'pt-2 pb-1',
        // 和 Slack 一样，@我 的消息用浅色底 + 左侧色条标出来
        message.mentions_me ? 'border-l-2 border-amber-400 bg-amber-50/70 pl-[18px] hover:bg-amber-50' : 'hover:bg-bg-hover/60',
        marked && 'border-l-[3px] border-primary-400 bg-primary-50/40 pl-[17px]',
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
        {askedZh && !zh
          ? <OnDemandBody message={message} context={context} picker={picker} />
          : <MessageBody message={message} zh={zh ?? null} picker={picker} />}
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
        {translatable && (
          <button
            type="button"
            onClick={() => setAskedZh(v => !v)}
            className={cn('rounded p-1 hover:bg-bg-hover hover:text-text-primary', askedZh ? 'text-primary-700' : 'text-text-muted')}
            title={askedZh ? '收起中文' : '翻译这条'}
            aria-label={askedZh ? '收起中文' : '翻译这条'}
          >
            {askedZh ? <Check className="h-4 w-4" /> : <Languages className="h-4 w-4" />}
          </button>
        )}
        {message.text.trim() && (
          <button
            type="button"
            onClick={() => {
              navigator.clipboard.writeText(message.text).then(
                () => toast.success('已复制原文'),
                () => toast.error('复制失败，浏览器没给剪贴板权限'),
              );
            }}
            className="rounded p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary"
            title="复制原文"
            aria-label="复制原文"
          >
            <Copy className="h-4 w-4" />
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
