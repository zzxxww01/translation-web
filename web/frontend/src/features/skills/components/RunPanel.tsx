import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { FolderDown, Hand, WifiOff } from 'lucide-react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/Button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { sendMessage, skillsApi } from '../api';
import { skillKeys, useRunEvents } from '../hooks';
import { harnessLabel } from '../harness';
import { CONTINUE_TEXT, displayStatus, foldEvents, runTitle } from '../state';
import type { Agent, RunMeta } from '../types';
import { AgentAvatar } from './AgentIcon';
import { AssistantText, NoticeLine, ToolGroup, TurnDivider, UserBubble } from './ChatItems';
import { Composer } from './Composer';
import { QuestionCard } from './QuestionCard';
import { SidePanel } from './SidePanel';
import { StatusPill } from './StatusPill';

const clock = new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' });

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
  const pending = new Set(view.pendingQids);
  const scrollRef = useRef<HTMLDivElement>(null);
  const stickToBottom = useRef(true);
  const [deleting, setDeleting] = useState(false);
  const [continuing, setContinuing] = useState(false);

  // 状态变化时让列表上的状态也跟着刷新，不用等轮询
  useEffect(() => {
    queryClient.invalidateQueries({ queryKey: skillKeys.runs });
  }, [status, view.awaiting, queryClient]);

  useLayoutEffect(() => {
    const el = scrollRef.current;
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight;
  }, [view.items.length, events.length]);

  const remove = async () => {
    setDeleting(true);
    try {
      await skillsApi.remove(run.id);
      await queryClient.invalidateQueries({ queryKey: skillKeys.runs });
      onDeleted();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除失败');
      setDeleting(false);
    }
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
      <header className="flex items-center gap-3 border-b border-border-subtle px-5 py-3">
        <AgentAvatar icon={agent.icon} />
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-base text-text-primary" title={run.title}>{runTitle(run.title)}</h1>
          <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-text-muted">
            <span>{agent.title} · {harnessLabel(run.harness)}</span>
            <StatusPill status={shown} />
            {!connected && (
              <span className="inline-flex items-center gap-1" title="实时连接断开，正在重连">
                <WifiOff className="h-3.5 w-3.5" /> 重连中
              </span>
            )}
          </div>
        </div>
        {/* 窄屏没有右栏，结果文件放进抽屉 */}
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="outline" size="sm" className="lg:hidden">
              <FolderDown /> 结果文件
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
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="ghost" size="sm" disabled={active || deleting} title={active ? '先停止再删除' : '删除这个对话和它的所有文件'}>
              删除
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>删除这个对话？</AlertDialogTitle>
              <AlertDialogDescription>对话记录、上传的文件和结果文件都会从服务器上删掉，无法恢复。</AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>取消</AlertDialogCancel>
              <AlertDialogAction onClick={remove}>删除</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </header>

      <div className="flex min-h-0 flex-1">
        <div className="flex min-w-0 flex-1 flex-col">
          <div
            ref={scrollRef}
            onScroll={event => {
              const el = event.currentTarget;
              stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
            }}
            className="min-h-0 flex-1 overflow-y-auto px-5 py-5"
          >
            <div className="mx-auto max-w-3xl space-y-4">
              {view.items.map(item => {
                switch (item.kind) {
                  case 'user':
                    return <UserBubble key={item.key} text={item.text} files={item.files} />;
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
                  case 'turn':
                    return <TurnDivider key={item.key} durationMs={item.durationMs} isError={item.isError} errors={item.errors} />;
                }
              })}
              {status === 'running' && (
                <div className="flex items-center gap-2 text-xs text-text-muted">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-info" /> {agent.title}正在干活…
                </div>
              )}
            </div>
          </div>
          {awaitingText && (
            <div className="border-t border-warning/30 bg-warning-light px-4 py-2.5">
              <div className="mx-auto flex max-w-3xl flex-wrap items-center gap-2 text-sm text-text-primary">
                <Hand className="h-4 w-4 shrink-0 text-warning" />
                <span className="min-w-0 flex-1">
                  {agent.title}在等你确认上面的内容。可以直接回复要改什么
                  {autoAt ? `；${autoAt} 前不回复，就按它的建议继续` : ''}。
                </span>
                <Button size="sm" onClick={() => void continueAsSuggested()} disabled={continuing}>
                  {continuing ? '发送中…' : '按建议继续'}
                </Button>
              </div>
            </div>
          )}
          <Composer runId={run.id} agent={agent} status={status} hasPendingQuestion={pending.size > 0} maxUploadMb={maxUploadMb} />
        </div>
        <div className="hidden w-72 shrink-0 overflow-y-auto border-l border-border-subtle px-4 py-5 lg:block">
          <SidePanel runId={run.id} status={status} todos={view.todos} />
        </div>
      </div>
    </div>
  );
}
