import { memo, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, ChevronRight, Info, Loader2, Paperclip, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { renderMarkdown } from '../markdown';
import type { ToolCall } from '../state';
import { formatDuration } from '../state';

export function UserBubble({ text, files }: { text: string; files: string[] }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-xl rounded-tr-sm bg-primary-50 px-4 py-2.5 text-sm text-text-primary">
        {text && <p className="whitespace-pre-wrap break-words">{text}</p>}
        {files.length > 0 && (
          <ul className={cn('space-y-0.5 text-xs text-text-secondary', text && 'mt-2')}>
            {files.map(file => (
              <li key={file} className="flex items-center gap-1.5">
                <Paperclip className="h-3 w-3" /> {file}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export const AssistantText = memo(function AssistantText({ text }: { text: string }) {
  const html = useMemo(() => renderMarkdown(text), [text]);
  // html 已经过 DOMPurify 消毒
  return <div className="skill-md text-sm text-text-primary" dangerouslySetInnerHTML={{ __html: html }} />;
});

function ToolLine({ call, active, depth }: { call: ToolCall; active: boolean; depth: number }) {
  const [open, setOpen] = useState(false);
  const hasDetail = Boolean(call.result?.text) || call.children.length > 0;
  const icon = call.result ? (
    call.result.ok ? <CheckCircle2 className="h-3.5 w-3.5 text-success" /> : <XCircle className="h-3.5 w-3.5 text-error" />
  ) : active ? (
    <Loader2 className="h-3.5 w-3.5 animate-spin text-primary-500" />
  ) : (
    <span className="h-3.5 w-3.5 rounded-full border border-border" />
  );

  return (
    <li>
      <button
        type="button"
        onClick={() => hasDetail && setOpen(v => !v)}
        className={cn('flex w-full items-center gap-2 py-1 text-left text-xs', hasDetail ? 'cursor-pointer' : 'cursor-default')}
        style={{ paddingLeft: depth * 16 }}
      >
        <ChevronRight className={cn('h-3 w-3 shrink-0 text-text-muted transition-transform', open && 'rotate-90', !hasDetail && 'invisible')} />
        <span className="shrink-0">{icon}</span>
        <span className="shrink-0 font-medium text-text-secondary">{call.name}</span>
        <span className="truncate text-text-muted">{call.summary}</span>
        {call.children.length > 0 && <span className="shrink-0 text-text-muted">· {call.children.length} 步</span>}
      </button>
      {open && (
        <div style={{ paddingLeft: depth * 16 + 20 }}>
          {call.result?.text && (
            <pre className="my-1 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-md bg-bg-secondary p-2.5 text-[11px] leading-relaxed text-text-secondary">
              {call.result.text}
            </pre>
          )}
          {call.children.length > 0 && (
            <ul>
              {call.children.map(child => (
                <ToolLine key={child.id} call={child} active={active} depth={depth + 1} />
              ))}
            </ul>
          )}
        </div>
      )}
    </li>
  );
}

export function ToolGroup({ tools, active }: { tools: ToolCall[]; active: boolean }) {
  const [open, setOpen] = useState(false);
  const failed = tools.filter(t => t.result && !t.result.ok).length;
  const running = active && tools.some(t => !t.result);

  return (
    <div className="rounded-lg border border-border-subtle bg-white/70">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-text-secondary"
      >
        <ChevronRight className={cn('h-3.5 w-3.5 shrink-0 transition-transform', open && 'rotate-90')} />
        {running ? <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-info" /> : null}
        <span className="shrink-0">{running ? `正在做第 ${tools.length} 步操作` : `做了 ${tools.length} 步操作`}</span>
        {failed > 0 && <span className="shrink-0 text-text-muted">（{failed} 步没成功，它会自己处理）</span>}
        {!open && <span className="ml-auto shrink-0 text-text-muted">点开看细节</span>}
      </button>
      {open && (
        <ul className="border-t border-border-subtle px-3 py-1.5">
          {tools.map(call => (
            <ToolLine key={call.id} call={call} active={active} depth={0} />
          ))}
        </ul>
      )}
    </div>
  );
}

const NOTICE_STYLE = {
  info: { icon: Info, className: 'text-text-muted' },
  warn: { icon: AlertTriangle, className: 'text-amber-700' },
  error: { icon: XCircle, className: 'text-error' },
} as const;

export function NoticeLine({ level, text }: { level: 'info' | 'warn' | 'error'; text: string }) {
  const { icon: Icon, className } = NOTICE_STYLE[level];
  return (
    <div className={cn('flex items-start gap-2 text-xs leading-relaxed', className)}>
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span className="whitespace-pre-wrap break-words">{text}</span>
    </div>
  );
}

export function TurnDivider({ durationMs, isError, errors }: { durationMs: number; isError: boolean; errors: string[] }) {
  return (
    <div className="flex items-center gap-3 text-[11px] text-text-muted">
      <span className="h-px flex-1 bg-border-subtle" />
      <span className={cn(isError && 'text-error')}>
        {isError ? `这一轮出错了${errors.length ? `：${errors.join('；')}` : ''}` : `用时 ${formatDuration(durationMs)}`}
      </span>
      <span className="h-px flex-1 bg-border-subtle" />
    </div>
  );
}
