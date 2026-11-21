import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { RunMeta } from '@/features/skills/types';
import { agentState, type AgentState } from './agentRuns';

const LABEL: Record<AgentState, string> = {
  running: 'AI 处理中',
  awaiting: 'AI 等你确认',
  error: 'AI 出错',
  done: 'AI 已处理',
};

const TONE: Record<AgentState, string> = {
  running: 'bg-info-light text-info',
  awaiting: 'bg-warning-light text-warning',
  error: 'bg-error/10 text-error',
  done: 'bg-primary-50 text-primary-700',
};

/** 侧栏行里的 AI 状态：直接写字（之前是转圈 / 橙点 / ! / ✨ 几个图标，看不懂）。 */
export function AgentBadge({ run }: { run: RunMeta | undefined }) {
  if (!run) return null;
  const state = agentState(run);
  return (
    <span className={cn('inline-flex shrink-0 items-center gap-0.5 rounded px-1 text-[10px] leading-4', TONE[state])}>
      {state === 'running' && <Loader2 className="h-2.5 w-2.5 animate-spin" />}
      {LABEL[state]}
    </span>
  );
}
