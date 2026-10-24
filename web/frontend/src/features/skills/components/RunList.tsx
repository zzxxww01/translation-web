import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { runKindLabel } from '../state';
import type { RunMeta } from '../types';
import { StatusPill } from './StatusPill';

function formatTime(seconds: number): string {
  const date = new Date(seconds * 1000);
  const sameDay = date.toDateString() === new Date().toDateString();
  return sameDay
    ? date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' });
}

interface RunListProps {
  runs: RunMeta[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export function RunList({ runs, selectedId, onSelect, onNew }: RunListProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between px-4 pb-3 pt-5">
        <h2 className="text-sm font-medium text-text-secondary">运行记录</h2>
        <Button size="sm" variant={selectedId ? 'outline' : 'secondary'} onClick={onNew}>
          <Plus /> 新建
        </Button>
      </div>
      <ul className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
        {runs.length === 0 && <li className="px-3 py-6 text-center text-sm text-text-muted">还没有运行过</li>}
        {runs.map(run => (
          <li key={run.id}>
            <button
              type="button"
              onClick={() => onSelect(run.id)}
              className={cn(
                'w-full rounded-md px-3 py-2.5 text-left transition-colors',
                run.id === selectedId ? 'bg-primary-50' : 'hover:bg-bg-hover'
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm text-text-primary">{run.title}</span>
                <span className="shrink-0 text-xs text-text-muted">{formatTime(run.created_at)}</span>
              </div>
              <div className="mt-1 flex items-center justify-between gap-2">
                <span className="truncate text-xs text-text-muted">{runKindLabel(run.skill)}</span>
                <StatusPill status={run.status} />
              </div>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
