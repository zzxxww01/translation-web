import { Loader2, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RunMeta } from '@/features/skills/types';
import { agentState, type AgentState } from './agentRuns';

const LABEL: Record<AgentState, string> = {
  running: 'AI 正在处理',
  awaiting: 'AI 在等你确认',
  error: 'AI 出错了，打开看看',
  done: 'AI 已经处理过',
};

/** 侧栏行尾的小标记：转圈 = 在跑，橙点 = 等你确认，红 ! = 出错，✨ = 有结果。 */
export function AgentBadge({ run, active = false }: { run: RunMeta | undefined; active?: boolean }) {
  if (!run) return null;
  const state = agentState(run);
  const cls = cn('h-3.5 w-3.5 shrink-0', active ? 'text-white' : '');
  return (
    <span title={LABEL[state]} aria-label={LABEL[state]} className="inline-flex shrink-0 items-center">
      {state === 'running' && <Loader2 className={cn(cls, 'animate-spin', !active && 'text-info')} />}
      {state === 'awaiting' && <span className={cn('h-2 w-2 rounded-full', active ? 'bg-white' : 'bg-warning')} />}
      {state === 'error' && <span className={cn('text-[11px] font-bold', active ? 'text-white' : 'text-error')}>!</span>}
      {state === 'done' && <Sparkles className={cn(cls, !active && 'text-primary-500')} />}
    </span>
  );
}
