import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { FolderDown, Hand, PanelRightClose, PanelRightOpen, Trash2, WifiOff } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { sendMessage, skillsApi } from '../api';
import { skillKeys, useRunEvents, useRunFiles } from '../hooks';
import { harnessLabel } from '../harness';
import { CONTINUE_TEXT, displayStatus, foldEvents, runTitle } from '../state';
import type { Agent, RunMeta } from '../types';
import { AgentAvatar } from './AgentIcon';
import { AssistantText, NoticeLine, ReportCard, ToolGroup, TurnDivider, UserBubble } from './ChatItems';
import { Composer } from './Composer';
import { HeldMessages } from './HeldMessages';
import { DeleteRunDialog } from './DeleteRunDialog';
import { QuestionCard } from './QuestionCard';
import { SidePanel } from './SidePanel';
import { StatusPill } from './StatusPill';

const clock = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' });
// 右栏（结果文件、步骤）默认收起，把宽度留给对话；开关记在浏览器里
const SIDE_KEY = 'skills.sidePanelOpen';
const loadSide = () => {
  try {
    return localStorage.getItem(SIDE_KEY) === '1';
  } catch {
    return false;
  }
};

interface RunPanelProps {
  run: RunMeta;
  agent: Agent;
  maxUploadMb: number;
  onDeleted: () => void;
}

/** 和一个 Agent 的一次对话。父组件按 run.id 加 key，换对话时整体重建。 */
export function RunPanel({ run, agent, maxUploadMb, onDeleted }: RunPanelProps) {
  const queryClient = useQueryClient();
  const { events, connected } = useRunEvents(run.id);
  const view = useMemo(() => foldEvents(events), [events]);
  const status = view.status ?? run.status;
  const shown = displayStatus(status, view.awaiting || (status === 'idle' && run.awaiting_reply));
  const active = status === 'running' || status === 'waiting';
  const queued = status === 'queued';
  const pending = new Set(view.pendingQids);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const [continuing, setContinuing] = useState(false);
  const [sideOpen, setSideOpen] = useState(loadSide);
  const { data: files = [] } = useRunFiles(run.id, status);
  const outputCount = files.filter(file => !file.path.startsWith('input/')).length;
  const held = view.held ?? run.held ?? [];
  const heldPaused = view.held ? view.heldPaused : Boolean(run.held_paused);
  const toggleSide = () => {
    setSideOpen(open => {
      try {
        localStorage.setItem(SIDE_KEY, open ? '0' : '1');
      } catch {
        // 隐私模式下存不了，只在这次有效
      }
      return !open;
    });
  };

  // 状态变化时让列表上的状态也跟着刷新，不用等轮询
  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: skillKeys.runs });
  }, [status, view.awaiting, queryClient]);

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [view.items.length, events.length]);

  const remove = async () => {
    await skillsApi.remove(run.id);
    await queryClient.invalidateQueries({ queryKey: skillKeys.runs });
    onDeleted();
  };

  const continueAsSuggested = async () => {
    setContinuing(true);
    try {
      await sendMessage(run.id, { message: CONTINUE_TEXT, files: [] });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '没发出去');
    } finally {
      setContinuing(false);
    }
  };

  // 说完在等你确认（提问挂着时由提问卡片处理）
  const awaitingText = shown === 'waiting' && pending.size === 0;
  const autoAt = run.auto_reply_at ? clock.format(run.auto_reply_at * 1000) : null;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex shrink-0 items-center gap-2.5 border-b border-border-subtle px-4 py-2">
        <AgentAvatar icon={agent.icon} size="sm" />
        <div className="flex min-w-0 flex-1 items-baseline gap-2">
          <h1 className="truncate text-sm font-medium text-text-primary" title={run.title}>{runTitle(run.title)}</h1>
          <span className="hidden min-w-0 truncate text-xs text-text-muted sm:inline">
            {agent.title} · {harnessLabel(run.harness)} · {run.actual_model || run.model || '默认模型'}
          </span>
        </div>
        <StatusPill status={shown} />
        {!connected && (
          <span className="inline-flex shrink-0 items-center gap-1 text-xs text-text-muted" title="实时连接断开，正在重连">
            <WifiOff className="h-3.5 w-3.5" /> 重连中
          </span>
        )}
        {/* 窄屏没有右栏，结果文件放进抽屉 */}
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="sm" className="lg:hidden" title="结果文件">
              <FolderDown /> {outputCount || ''}
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-80 overflow-y-auto">
            <SheetHeader>
              <SheetTitle>结果文件</SheetTitle>
            </SheetHeader>
            <div className="mt-4">
              <SidePanel runId={run.id} status={status} todos={view.todos} />
            </div>
          </SheetContent>
        </Sheet>
        <Button
          variant="ghost"
          size="sm"
          className="hidden lg:inline-flex"
          onClick={toggleSide}
          title={sideOpen ? '收起结果文件' : '展开结果文件和步骤'}
        >
          {sideOpen ? <PanelRightClose /> : <PanelRightOpen />} 文件{outputCount ? ` ${outputCount}` : ''}
        </Button>
        <DeleteRunDialog onConfirm={remove}>
          <Button variant="ghost" size="icon" disabled={active} title={active ? '先停止再删除' : '删除这个对话'} aria-label="删除这个对话">
            <Trash2 />
          </Button>
        </DeleteRunDialog>
      </header>

      <div className="flex min-h-0 flex-1">
        <div className="flex min-w-0 flex-1 flex-col">
          <div
            ref={scrollRef}
            onScroll={event => {
              const el = event.currentTarget;
              stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
            }}
            className="min-h-0 flex-1 overflow-y-auto px-3 py-4 sm:px-5"
          >
            <div className="mx-auto max-w-4xl space-y-3">
              {view.items.map(item => {
                switch (item.kind) {
                  case 'user':
                    return <UserBubble key={item.key} text={item.text} files={item.files} runId={run.id} />;
                  case 'text':
                    return <AssistantText key={item.key} text={item.text} />;
                  case 'tools':
                    return <ToolGroup key={item.key} tools={item.tools} active={active} />;
                  case 'question':
                    return (
                      <QuestionCard
                        key={item.key}
                        runId={run.id}
                        qid={item.qid}
                        questions={item.questions}
                        answer={item.answer}
                        pending={pending.has(item.qid)}
                      />
                    );
                  case 'notice':
                    return <NoticeLine key={item.key} level={item.level} text={item.text} />;
                  case 'report':
                    return <ReportCard key={item.key} title={item.title} lines={item.lines} />;
                  case 'turn':
                    return <TurnDivider key={item.key} durationMs={item.durationMs} isError={item.isError} errors={item.errors} />;
                }
              })}
              {queued && (
                <div className="flex items-center gap-2 text-xs text-text-muted">
                  <span className="h-1.5 w-1.5 rounded-full bg-text-muted" /> 在排队，前面的对话跑完一个就轮到它
                </div>
              )}
              {status === 'running' && (
                <div className="flex items-center gap-2 text-xs text-text-muted">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-info" /> {agent.title}正在干活…
                </div>
              )}
              <HeldMessages runId={run.id} items={held} paused={heldPaused && !active && !queued} />
            </div>
          </div>
          <Composer
            runId={run.id}
            agent={agent}
            status={status}
            hasPendingQuestion={pending.size > 0}
            pausedHeld={heldPaused && !active && !queued ? held.length : 0}
            maxUploadMb={maxUploadMb}
            notice={
              awaitingText ? (
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-text-secondary">
                  <Hand className="h-3.5 w-3.5 shrink-0 text-warning" />
                  <span className="min-w-0 flex-1">
                    在等你确认上面的内容，直接回复要改什么{autoAt ? `；${autoAt} 前不回就按建议继续` : ''}
                  </span>
                  <Button size="sm" variant="outline" className="h-6 px-2 text-xs" onClick={() => void continueAsSuggested()} disabled={continuing}>
                    {continuing ? '发送中…' : '按建议继续'}
                  </Button>
                </div>
              ) : null
            }
          />
        </div>
        {sideOpen && (
          <div className="hidden w-72 shrink-0 overflow-y-auto border-l border-border-subtle px-4 py-4 lg:block">
            <SidePanel runId={run.id} status={status} todos={view.todos} />
          </div>
        )}
      </div>
    </div>
  );
}
