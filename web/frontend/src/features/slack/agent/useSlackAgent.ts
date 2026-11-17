import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiErrorWrapper } from '@/shared/api/client';
import { AUTO_REPLY_MINUTES, sendMessage, skillsApi, startRun } from '@/features/skills/api';
import { isUnauthorized, useSkillsAuth } from '@/features/skills/hooks';
import type { RunMeta } from '@/features/skills/types';
import { slackInboxApi } from '../inbox/api';
import type { SlackAgentContext } from '../inbox/types';

/** thread 交给帖子翻译助手，私信交给回复助手（skill 在 skill_runner/skills/ 下）。 */
export const SLACK_SKILLS = { thread: 'slack-post-translate', dm: 'slack-dm-reply' } as const;

// 排队时隔多久再试一次（服务端同一时间只跑一个 Slack agent）
const QUEUE_RETRY_MS = 15_000;

export function agentSource(channelId: string, threadTs?: string | null) {
  return threadTs ? `slack:${channelId}:${threadTs}` : `slack:${channelId}`;
}

// 记住交给 agent 的上下文截到哪条消息，之后有新消息就提示「让 AI 重新看」
const seenKey = (source: string) => `slack-agent-seen:${source}`;
export function readSeen(source: string): string | null {
  try {
    return localStorage.getItem(seenKey(source));
  } catch {
    return null;
  }
}
function writeSeen(source: string, ts: string | null) {
  try {
    if (ts) localStorage.setItem(seenKey(source), ts);
  } catch {
    // 隐私模式下写不了就算了，只是少一个提示
  }
}

function contextFiles(ctx: SlackAgentContext, isThread: boolean): File[] {
  if (isThread) return [new File([ctx.markdown], 'slack-thread.md', { type: 'text/markdown' })];
  return [
    new File([ctx.markdown], 'slack-dm.md', { type: 'text/markdown' }),
    new File([JSON.stringify(ctx.history, null, 1)], 'slack-history.json', { type: 'application/json' }),
  ];
}

const FIRST_MESSAGE = {
  thread: '请处理附件里的 Slack thread：找出要翻译的内容，走帖子翻译，给出译文和标题候选。',
  dm: '请看附件里的 Slack 私信对话：用中文说清对方要什么，推荐三版英文回复。',
};
const REFRESH_MESSAGE = '对话有新消息，附件是最新的完整内容，请按最新内容重新处理并更新 result.json。';

export type AgentPhase = 'idle' | 'starting' | 'queued' | 'error';

/**
 * 一个 Slack 会话 / thread 对应的 agent：先按 source 找已有的对话；没有就自动导出上下文、启动 skill。
 * 服务端忙（另一个 Slack agent 在跑）时返回 429，这里每 15 秒重试一次，页面上显示「排队中」。
 */
export function useSlackAgent(channelId: string, threadTs: string | null) {
  const isThread = !!threadTs;
  const source = agentSource(channelId, threadTs);
  const queryClient = useQueryClient();
  const auth = useSkillsAuth();
  const authed = auth.isSuccess;
  const lookup = useQuery({
    queryKey: ['slack-agent', source],
    queryFn: () => skillsApi.runBySource(source),
    enabled: authed,
    staleTime: 10_000,
  });
  const [phase, setPhase] = useState<AgentPhase>('idle');
  const [error, setError] = useState<string | null>(null);
  const attempted = useRef(false);

  const start = useCallback(async () => {
    setPhase('starting');
    setError(null);
    try {
      const ctx = await slackInboxApi.agentContext(channelId, threadTs ?? undefined);
      const run = await startRun({
        skill: isThread ? SLACK_SKILLS.thread : SLACK_SKILLS.dm,
        message: FIRST_MESSAGE[isThread ? 'thread' : 'dm'],
        files: contextFiles(ctx, isThread),
        autoReplyMinutes: AUTO_REPLY_MINUTES,
        title: `Slack · ${ctx.title}`,
        source,
      });
      writeSeen(source, ctx.latest_ts);
      queryClient.setQueryData<RunMeta | null>(['slack-agent', source], run);
      setPhase('idle');
    } catch (err) {
      if (err instanceof ApiErrorWrapper && err.status === 429) {
        setPhase('queued');
        return;
      }
      setPhase('error');
      setError(err instanceof Error ? err.message : '启动失败');
    }
  }, [channelId, threadTs, isThread, source, queryClient]);

  // 打开就自动启动（每个 thread / 私信只自动试一次；失败了让用户手动重试）
  const needsStart = lookup.isSuccess && lookup.data === null;
  useEffect(() => {
    if (!needsStart || attempted.current) return;
    attempted.current = true;
    const timer = setTimeout(() => void start(), 0);
    return () => clearTimeout(timer);
  }, [needsStart, start]);

  useEffect(() => {
    if (phase !== 'queued') return;
    const timer = setTimeout(() => void start(), QUEUE_RETRY_MS);
    return () => clearTimeout(timer);
  }, [phase, start]);

  /** 有新消息后，把最新上下文发给同一个 agent 重新处理。 */
  const refresh = useCallback(async () => {
    const run = lookup.data;
    if (!run) return;
    const ctx = await slackInboxApi.agentContext(channelId, threadTs ?? undefined);
    await sendMessage(run.id, { message: REFRESH_MESSAGE, files: contextFiles(ctx, isThread) });
    writeSeen(source, ctx.latest_ts);
  }, [lookup.data, channelId, threadTs, isThread, source]);

  return {
    source,
    skill: isThread ? SLACK_SKILLS.thread : SLACK_SKILLS.dm,
    needsLogin: isUnauthorized(auth.error) || isUnauthorized(lookup.error),
    authLoading: auth.isLoading || (authed && lookup.isLoading),
    maxUploadMb: auth.data?.max_upload_mb ?? 95,
    run: lookup.data ?? null,
    lookupError: lookup.error && !isUnauthorized(lookup.error) ? lookup.error.message : null,
    phase,
    error,
    start,
    refresh,
  };
}
