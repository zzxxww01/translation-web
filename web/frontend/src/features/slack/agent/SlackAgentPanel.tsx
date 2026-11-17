import { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Loader2, RefreshCw, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { findAgent, normalizeCatalog } from '@/features/skills/agents';
import { AssistantText, NoticeLine, ToolGroup, TurnDivider, UserBubble } from '@/features/skills/components/ChatItems';
import { Composer } from '@/features/skills/components/Composer';
import { LoginPanel } from '@/features/skills/components/LoginPanel';
import { QuestionCard } from '@/features/skills/components/QuestionCard';
import { StatusPill } from '@/features/skills/components/StatusPill';
import { useCatalog, useRunEvents } from '@/features/skills/hooks';
import { displayStatus, foldEvents } from '@/features/skills/state';
import type { RunMeta } from '@/features/skills/types';
import { ResultCards } from './ResultCards';
import { useAgentResult } from './result';
import { readSeen, useSlackAgent } from './useSlackAgent';

function AgentRun({ run, skill, maxUploadMb, slackLink, hasNewMessages, onRefresh }: {
  run: RunMeta; skill: string; maxUploadMb: number; slackLink: string | null; hasNewMessages: boolean; onRefresh: () => Promise<void>;
}) {
  const catalog = useCatalog(true);
  const agent = findAgent(normalizeCatalog(catalog.data), skill);
  const { events } = useRunEvents(run.id);
  const view = useMemo(() => foldEvents(events), [events]);
  const status = view.status ?? run.status;
  const shown = displayStatus(status, view.awaiting || (status === 'idle' && run.awaiting_reply));
  const pending = new Set(view.pendingQids);
  const result = useAgentResult(run.id, status);
  const [refreshing, setRefreshing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [view.items.length]);

  // 过程只保留文字、提问和出错；工具调用折叠成一行，免得右栏太长
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2 text-xs text-text-muted">
        <Sparkles className="h-3.5 w-3.5 text-primary-500" />
        <span className="min-w-0 flex-1 truncate">{agent.title}</span>
        <StatusPill status={shown} />
      </div>
      {hasNewMessages && status !== 'running' && (
        <div className="flex items-center gap-2 border-b border-warning/30 bg-warning-light px-4 py-2 text-xs text-text-primary">
          <span className="flex-1">有新消息，AI 还没看到</span>
          <Button
            size="sm"
            variant="outline"
            className="h-7"
            disabled={refreshing}
            onClick={async () => {
              setRefreshing(true);
              try {
                await onRefresh();
              } catch (error) {
                toast.error(error instanceof Error ? error.message : '没发出去');
              } finally {
                setRefreshing(false);
              }
            }}
          >
            <RefreshCw className={refreshing ? 'animate-spin' : ''} /> 让 AI 重新看
          </Button>
        </div>
      )}
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 py-3">
        {result.data && <ResultCards result={result.data} slackLink={slackLink} />}
        <details className="group" open={!result.data}>
          <summary className="cursor-pointer select-none text-xs text-text-muted">{result.data ? '查看 AI 的处理过程' : '处理过程'}</summary>
          <div className="mt-2 space-y-3">
            {view.items.map(item => {
              switch (item.kind) {
                case 'user':
                  return <UserBubble key={item.key} text={item.text} files={item.files} />;
                case 'text':
                  return <AssistantText key={item.key} text={item.text} />;
                case 'tools':
                  return <ToolGroup key={item.key} tools={item.tools} active={status === 'running'} />;
                case 'question':
                  // 有结果时，挂着的提问单独显示在过程外面
                  if (result.data && pending.has(item.qid)) return null;
                  return (
                    <QuestionCard key={item.key} runId={run.id} qid={item.qid} questions={item.questions}
                      answer={item.answer} pending={pending.has(item.qid)} />
                  );
                case 'notice':
                  return <NoticeLine key={item.key} level={item.level} text={item.text} />;
                case 'turn':
                  return <TurnDivider key={item.key} durationMs={item.durationMs} isError={item.isError} errors={item.errors} />;
              }
            })}
          </div>
        </details>
        {/* 提问挂着时，即使过程收起来也要看得到 */}
        {result.data && view.items.filter(i => i.kind === 'question' && pending.has(i.qid)).map(item => item.kind === 'question' && (
          <QuestionCard key={`p-${item.key}`} runId={run.id} qid={item.qid} questions={item.questions} answer={item.answer} pending />
        ))}
        {status === 'running' && (
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-info" /> {agent.title}正在处理…
          </div>
        )}
      </div>
      <Composer runId={run.id} agent={agent} status={status} hasPendingQuestion={pending.size > 0} maxUploadMb={maxUploadMb} />
    </div>
  );
}

interface SlackAgentPanelProps {
  channelId: string;
  threadTs: string | null;
  /** 会话 / thread 里最新一条消息的 ts，用来判断 AI 有没有看到最新内容 */
  latestTs: string | null;
  /** 「复制并打开 Slack」跳去的位置 */
  slackLink: string | null;
}

/** 右栏的 AI：一个 thread / 私信对应一个 skill agent，打开就自动启动，结果以卡片显示。父组件按 source 加 key。 */
export function SlackAgentPanel({ channelId, threadTs, latestTs, slackLink }: SlackAgentPanelProps) {
  const agent = useSlackAgent(channelId, threadTs);

  if (agent.needsLogin) return <LoginPanel />;
  if (agent.run) {
    const seen = readSeen(agent.source);
    const hasNew = !!latestTs && !!seen && parseFloat(latestTs) > parseFloat(seen);
    return (
      <AgentRun
        run={agent.run}
        skill={agent.skill}
        maxUploadMb={agent.maxUploadMb}
        slackLink={slackLink}
        hasNewMessages={hasNew}
        onRefresh={agent.refresh}
      />
    );
  }
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-sm text-text-muted">
      {agent.phase === 'queued' ? (
        <>
          <Loader2 className="h-5 w-5 animate-spin" />
          <div>排队中：另一个 Slack AI 正在处理，轮到时自动开始</div>
        </>
      ) : agent.phase === 'error' || agent.lookupError ? (
        <>
          <div className="text-error">AI 没能启动：{agent.error ?? agent.lookupError}</div>
          <Button size="sm" onClick={() => void agent.start()}>重试</Button>
        </>
      ) : (
        <>
          <Loader2 className="h-5 w-5 animate-spin" />
          <div>{agent.authLoading ? '连接 AI…' : '正在把对话交给 AI…'}</div>
        </>
      )}
    </div>
  );
}
