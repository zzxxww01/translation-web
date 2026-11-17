import { useState, type ReactNode } from 'react';
import { Check, Copy, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import type { SlackAgentResult } from './result';

function CopyButton({ text, label = '复制', onCopied, className }: {
  text: string; label?: string; onCopied?: () => void; className?: string;
}) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1500);
          onCopied?.();
        } catch {
          toast.error('复制失败，请手动选中复制');
        }
      }}
      className={cn(
        'inline-flex shrink-0 items-center gap-1 rounded-md border border-border-subtle bg-white px-2 py-1 text-xs text-text-secondary hover:bg-bg-hover',
        className
      )}
    >
      {done ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
      {done ? '已复制' : label}
    </button>
  );
}

function Card({ title, actions, children }: { title: string; actions?: ReactNode; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-border-subtle bg-white p-3 shadow-sm">
      <div className="mb-1.5 flex items-center gap-2">
        <span className="flex-1 text-xs font-semibold text-text-muted">{title}</span>
        {actions}
      </div>
      {children}
    </div>
  );
}

export function ResultCards({ result, slackLink }: { result: SlackAgentResult; slackLink: string | null }) {
  if (result.type === 'post_translation') {
    return (
      <div className="space-y-2">
        {result.summary && <div className="text-sm text-text-secondary">{result.summary}</div>}
        {result.translation ? (
          <Card title="中文译文" actions={<CopyButton text={result.translation} />}>
            <div className="whitespace-pre-wrap text-sm leading-relaxed text-text-primary">{result.translation}</div>
          </Card>
        ) : null}
        {result.titles && result.titles.length > 0 && (
          <Card title="标题候选">
            <ul className="space-y-1">
              {result.titles.map(t => (
                <li key={t} className="flex items-center gap-2 text-sm text-text-primary">
                  <span className="min-w-0 flex-1">{t}</span>
                  <span className="text-[11px] text-text-muted">{[...t].length} 字</span>
                  <CopyButton text={t} className="px-1.5" label="" />
                </li>
              ))}
            </ul>
          </Card>
        )}
        {result.source_text && (
          <details className="rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm">
            <summary className="cursor-pointer text-xs font-semibold text-text-muted">原文（送去翻译的内容）</summary>
            <div className="mt-1.5 whitespace-pre-wrap text-text-secondary">{result.source_text}</div>
          </details>
        )}
      </div>
    );
  }

  const openSlack = () => {
    if (slackLink) window.open(slackLink, '_blank', 'noopener');
  };
  return (
    <div className="space-y-2">
      {result.understanding && (
        <Card title={result.pending === false ? '最近在聊' : '对方要什么'}>
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-text-primary">{result.understanding}</div>
        </Card>
      )}
      {result.pending === false && (!result.replies || result.replies.length === 0) && (
        <div className="text-xs text-text-muted">目前不需要回复；想主动发什么，直接在下面用中文说。</div>
      )}
      {result.replies?.map(r => (
        <Card
          key={r.version}
          title={`${r.version}${r.label ? ` · ${r.label}` : ''}`}
          actions={
            <CopyButton
              text={r.english}
              label={slackLink ? '复制并打开 Slack' : '复制'}
              onCopied={openSlack}
            />
          }
        >
          <div className="whitespace-pre-wrap text-sm leading-relaxed text-text-primary">{r.english}</div>
          {r.chinese && <div className="mt-1 text-xs text-text-muted">{r.chinese}</div>}
        </Card>
      ))}
      {slackLink && result.replies && result.replies.length > 0 && (
        <a href={slackLink} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-xs text-primary-700 hover:underline">
          <ExternalLink className="h-3.5 w-3.5" /> 在 Slack 里打开这个对话
        </a>
      )}
    </div>
  );
}
