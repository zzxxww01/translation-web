import { useState } from 'react';
import { ChevronDown, ChevronRight, ExternalLink, FileDown, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { emojiFor, emojify } from './lib';
import { SlackText } from './SlackText';
import { useSlackReplies } from './hooks';
import type { SlackMessage } from './types';

// 不加载 Slack 头像图：slack-edge.com 在国内常常打不开，直接用名字首字母
function Avatar({ message }: { message: SlackMessage }) {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary-100 text-sm font-medium text-primary-700">
      {message.user_name.slice(0, 1).toUpperCase()}
    </div>
  );
}

function MessageBody({ message }: { message: SlackMessage }) {
  return (
    <>
      {message.segments.length > 0 && <SlackText segments={message.segments} />}
      {message.files.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {message.files.map(file =>
            file.is_image ? (
              <a key={file.id} href={file.url} target="_blank" rel="noreferrer" title={file.name}>
                <img
                  src={file.url}
                  alt={file.name}
                  loading="lazy"
                  className="max-h-72 max-w-full rounded-md border border-border-subtle bg-bg-tertiary object-contain sm:max-w-sm"
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
          {a.text && <div className="mt-0.5 line-clamp-4 whitespace-pre-wrap">{emojify(a.text)}</div>}
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

function MessageHeader({ message }: { message: SlackMessage }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-sm font-semibold text-text-primary">{message.user_name}</span>
      <span className="text-xs text-text-muted">{message.time}{message.edited ? ' · 已编辑' : ''}</span>
      <a
        href={message.permalink}
        target="_blank"
        rel="noreferrer noopener"
        className="ml-auto text-text-muted opacity-0 transition-opacity hover:text-primary-700 group-hover:opacity-100"
        title="在 Slack 里打开"
        aria-label="在 Slack 里打开"
      >
        <ExternalLink className="h-3.5 w-3.5" />
      </a>
    </div>
  );
}

export function MessageItem({ channelId, message }: { channelId: string; message: SlackMessage }) {
  const [open, setOpen] = useState(false);
  const isThreadRoot = message.reply_count > 0 && message.thread_ts === message.ts;
  const replies = useSlackReplies(channelId, message.ts, open && isThreadRoot);

  return (
    <div className="group flex gap-3 px-4 py-2.5 hover:bg-bg-hover/60">
      <Avatar message={message} />
      <div className="min-w-0 flex-1">
        <MessageHeader message={message} />
        <MessageBody message={message} />
        {isThreadRoot && (
          <button
            type="button"
            onClick={() => setOpen(v => !v)}
            className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-primary-700 hover:underline"
          >
            {open ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            {message.reply_count} 条回复
          </button>
        )}
        {open && isThreadRoot && (
          <div className={cn('mt-2 space-y-3 border-l-2 border-primary-100 pl-3')}>
            {replies.isLoading && <Loader2 className="h-4 w-4 animate-spin text-text-muted" />}
            {replies.isError && <div className="text-xs text-error">加载回复失败：{replies.error.message}</div>}
            {replies.data?.map(reply => (
              <div key={reply.ts} className="group flex gap-2.5">
                <Avatar message={reply} />
                <div className="min-w-0 flex-1">
                  <MessageHeader message={reply} />
                  <MessageBody message={reply} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
