import { cn } from '@/lib/utils';
import { STATUS_LABEL } from '../state';
import type { RunStatus } from '../types';

const STYLE: Record<RunStatus, string> = {
  running: 'bg-primary-50 text-primary-700',
  waiting: 'bg-amber-50 text-amber-700',
  idle: 'bg-bg-tertiary text-text-secondary',
  error: 'bg-red-50 text-red-700',
};

export function StatusPill({ status, className }: { status: RunStatus; className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium', STYLE[status], className)}>
      {(status === 'running' || status === 'waiting') && (
        <span className={cn('h-1.5 w-1.5 rounded-full', status === 'running' ? 'animate-pulse bg-primary-500' : 'bg-amber-500')} />
      )}
      {STATUS_LABEL[status]}
    </span>
  );
}
