import { useMemo } from 'react';
import { useRuns, useSkillsAuth } from '@/features/skills/hooks';
import type { RunMeta } from '@/features/skills/types';

/** Slack 页配的 agent：source -> 对话。没登录 Claude 页时为空（侧栏就不显示 AI 状态）。 */
export function useSlackAgentRuns(): Map<string, RunMeta> {
  const auth = useSkillsAuth();
  const runs = useRuns(auth.isSuccess);
  return useMemo(() => {
    const map = new Map<string, RunMeta>();
    for (const run of runs.data ?? []) {
      if (run.source?.startsWith('slack:')) map.set(run.source, run);
    }
    return map;
  }, [runs.data]);
}

export type AgentState = 'running' | 'awaiting' | 'error' | 'done';

export function agentState(run: RunMeta): AgentState {
  if (run.status === 'running' || run.status === 'waiting') return 'running';
  if (run.status === 'error') return 'error';
  if (run.awaiting_reply) return 'awaiting';
  return 'done';
}
