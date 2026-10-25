import { cn } from '@/lib/utils';
import { STATUS_LABEL, type DisplayStatus } from '../state';

const STYLE: Record<DisplayStatus, { text: string; dot?: string }> = {
  running: { text: 'text-info', dot: 'animate-pulse bg-info' },
  waiting: { text: 'text-warning', dot: 'bg-warning' },
  done: { text: 'text-text-muted' },
  error: { text: 'text-error' },
};

/** 对话状态，用字说清楚：进行中 / 等你确认 / 完成 / 已中断 */
export function StatusPill({ status, className }: { status: DisplayStatus | null; className?: string }) {
  if (!status) return null;
  const style = STYLE[status];
  return (
    <span className={cn('inline-flex shrink-0 items-center gap-1.5 text-xs font-medium', style.text, className)}>
      {style.dot && <span className={cn('h-1.5 w-1.5 rounded-full', style.dot)} />}
      {STATUS_LABEL[status]}
    </span>
  );
}
