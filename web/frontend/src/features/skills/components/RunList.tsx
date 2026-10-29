import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { findAgent } from '../agents';
import { displayStatus, runTitle } from '../state';
import type { Agent, RunMeta } from '../types';
import { AgentAvatar } from './AgentIcon';
import { DeleteRunDialog } from './DeleteRunDialog';
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
  catalog: Agent[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => Promise<void>;
}

/** 左栏：「新对话」按钮 + 对话记录。每条写清是哪个 Agent、什么时候、现在什么状态。 */
export function RunList({ runs, catalog, selectedId, onSelect, onNew, onDelete }: RunListProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="px-3 pb-3 pt-4">
        <Button className="w-full" variant={selectedId ? 'outline' : 'default'} onClick={onNew}>
          <Plus /> 新对话
        </Button>
      </div>
      <h2 className="px-4 pb-1.5 text-xs text-text-muted">对话记录</h2>
      <ul className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
        {runs.length === 0 && <li className="px-3 py-6 text-center text-sm text-text-muted">还没有对话</li>}
        {runs.map(run => {
          const agent = findAgent(catalog, run.skill);
          const active = run.status === 'running' || run.status === 'waiting';
          return (
            <li key={run.id} className="group relative">
              <button
                type="button"
                onClick={() => onSelect(run.id)}
                aria-current={run.id === selectedId ? 'true' : undefined}
                className={cn(
                  'flex w-full items-start gap-2.5 rounded-lg py-2.5 pl-2.5 pr-9 text-left transition-colors',
                  run.id === selectedId ? 'bg-primary-50' : 'hover:bg-bg-hover group-hover:bg-bg-hover'
                )}
              >
                <AgentAvatar icon={agent.icon} size="sm" className="mt-0.5" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm text-text-primary">{runTitle(run.title)}</span>
                  <span className="mt-0.5 flex items-center gap-2 text-xs text-text-muted">
                    <span className="truncate">{agent.title} · {formatTime(run.created_at)}</span>
                    <StatusPill status={displayStatus(run.status, run.awaiting_reply)} className="ml-auto" />
                  </span>
                </span>
              </button>
              <DeleteRunDialog onConfirm={() => onDelete(run.id)}>
                <button
                  type="button"
                  aria-label={`删除对话：${runTitle(run.title)}`}
                  title={active ? '先停止再删除' : '删除这个对话'}
                  disabled={active}
                  className="absolute right-1.5 top-2 rounded-md p-1.5 text-text-muted transition-opacity enabled:hover:bg-bg-hover enabled:hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-30 [@media(hover:hover)]:opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 focus-visible:opacity-100"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </DeleteRunDialog>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
