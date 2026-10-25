import { useState, type ReactNode } from 'react';
import { Plus } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { findAgent } from '../agents';
import type { Agent, RunMeta } from '../types';
import { AgentIcon } from './AgentIcon';
import { StatusPill } from './StatusPill';

function formatTime(seconds: number): string {
  const date = new Date(seconds * 1000);
  const sameDay = date.toDateString() === new Date().toDateString();
  return sameDay
    ? date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' });
}

function FilterButton({ active, label, onClick, children }: { active: boolean; label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      aria-label={label}
      title={label}
      onClick={onClick}
      className={cn(
        'inline-flex h-7 min-w-7 items-center justify-center rounded-md px-2 text-xs transition-colors',
        active ? 'bg-primary-50 font-medium text-primary-700' : 'text-text-muted hover:bg-bg-hover hover:text-text-primary'
      )}
    >
      {children}
    </button>
  );
}

interface RunListProps {
  runs: RunMeta[];
  catalog: Agent[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export function RunList({ runs, catalog, selectedId, onSelect, onNew }: RunListProps) {
  // null = 全部；'' = Claude 聊天
  const [filter, setFilter] = useState<string | null>(null);
  const shown = filter === null ? runs : runs.filter(run => run.skill === filter);

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-center justify-between px-4 pb-2 pt-5">
        <h2 className="text-sm font-medium text-text-secondary">任务</h2>
        <Button size="sm" variant={selectedId ? 'outline' : 'secondary'} onClick={onNew}>
          <Plus /> 新任务
        </Button>
      </div>
      <div className="flex flex-wrap gap-1 px-3 pb-2" role="group" aria-label="按 agent 筛选">
        <FilterButton active={filter === null} label="全部" onClick={() => setFilter(null)}>
          全部
        </FilterButton>
        {catalog.map(agent => (
          <FilterButton
            key={agent.name || 'chat'}
            active={filter === agent.name}
            label={agent.title}
            onClick={() => setFilter(agent.name)}
          >
            <AgentIcon icon={agent.icon} className="h-3.5 w-3.5" />
          </FilterButton>
        ))}
      </div>
      <ul className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
        {shown.length === 0 && (
          <li className="px-3 py-6 text-center text-sm text-text-muted">
            {runs.length === 0 ? '还没有任务' : '这个 agent 还没有任务'}
          </li>
        )}
        {shown.map(run => {
          const agent = findAgent(catalog, run.skill);
          return (
            <li key={run.id}>
              <button
                type="button"
                onClick={() => onSelect(run.id)}
                className={cn(
                  'flex w-full items-start gap-2.5 rounded-md px-3 py-2.5 text-left transition-colors',
                  run.id === selectedId ? 'bg-primary-50' : 'hover:bg-bg-hover'
                )}
              >
                <span
                  className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border-subtle bg-white text-text-secondary"
                  title={agent.title}
                >
                  <AgentIcon icon={agent.icon} className="h-3.5 w-3.5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm text-text-primary">{run.title}</span>
                    <span className="shrink-0 text-xs text-text-muted">{formatTime(run.created_at)}</span>
                  </span>
                  <span className="mt-1 flex items-center justify-between gap-2">
                    <span className="truncate text-xs text-text-muted">{agent.title}</span>
                    <StatusPill status={run.status} />
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
