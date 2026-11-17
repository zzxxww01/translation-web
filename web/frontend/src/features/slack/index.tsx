import { useSearchParams } from 'react-router-dom';
import { Loader2, MessagesSquare, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SlackAgentPanel } from './agent/SlackAgentPanel';
import { ConversationView } from './inbox/ConversationView';
import { CredentialsPanel } from './inbox/CredentialsPanel';
import { useSlackConversations, useSlackStatus } from './inbox/hooks';
import { parseSlackView, type SlackView } from './inbox/lib';
import { Sidebar, type OpenThread } from './inbox/Sidebar';
import { ThreadPanel } from './inbox/ThreadPanel';
import { ThreadsView } from './inbox/ThreadsView';
import { ReplyWorkbench } from './ReplyWorkbench';

const TS_RE = /^\d{9,11}\.\d{1,6}$/;

/**
 * Slack 页，布局照原生 Slack：左栏会话（频道可展开看 thread）、中栏消息流、右栏 thread。
 * URL：c=会话，view=threads|reply，tc+t=右栏打开的 thread（所在会话 + thread_ts），ai=1 窄屏上显示私信的 AI。
 * 每个 thread 背后是帖子翻译助手（在 thread 面板里），每个私信背后是回复助手（私信打开时的右栏）。
 */
export function SlackFeature() {
  const [params, setParams] = useSearchParams();
  const view = parseSlackView(params.get('view'));
  const selectedId = view ? null : params.get('c');
  const tc = params.get('tc');
  const t = params.get('t');
  const openThread: OpenThread | null = tc && t && TS_RE.test(t) ? { channelId: tc, threadTs: t } : null;

  const status = useSlackStatus();
  const ready = !!status.data?.ok;
  const list = useSlackConversations(ready);
  const conversations = list.data?.conversations ?? [];
  const selected = conversations.find(c => c.id === selectedId) ?? null;

  const update = (next: Record<string, string | null>) => {
    const p = new URLSearchParams(params);
    for (const [k, v] of Object.entries(next)) {
      if (v) p.set(k, v);
      else p.delete(k);
    }
    setParams(p, { replace: true });
  };
  const selectConversation = (id: string) => update({ c: id, view: null, tc: null, t: null, ai: null });
  const selectView = (v: SlackView) => update({ view: v, c: null, tc: null, t: null });
  const showThread = (thread: OpenThread) => {
    // 从侧栏或 Threads 页点 thread：中栏切到它所在的频道（Threads 页保持不动），右栏打开 thread
    const keepThreadsView = view === 'threads';
    update({ tc: thread.channelId, t: thread.threadTs, ...(keepThreadsView ? {} : { c: thread.channelId, view: null }) });
  };
  const closeThread = () => update({ tc: null, t: null });
  const aiOpen = params.get('ai') === '1';
  const back = () => update({ c: null, view: null, tc: null, t: null });

  if (status.isLoading) {
    return <div className="flex h-full items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-text-muted" /></div>;
  }
  if (status.isError) {
    return <div className="p-6 text-sm text-error">读取 Slack 状态失败：{status.error.message}</div>;
  }
  if (!ready || !status.data) {
    return <div className="h-full overflow-auto"><CredentialsPanel status={status.data} /></div>;
  }

  const hasMain = !!selected || !!view;
  const threadChannel = openThread ? conversations.find(c => c.id === openThread.channelId) : null;
  // 私信（含群聊私信）打开、没开 thread 时，右栏是回复助手；宽屏一直显示，窄屏点「AI 回复」才切过去
  const dmAgent = !openThread && selected && (selected.kind === 'im' || selected.kind === 'mpim') ? selected : null;
  const teamUrl = status.data.url || 'https://app.slack.com';

  return (
    <div className="flex h-full min-h-0">
      <aside className={cn(
        'w-full shrink-0 flex-col border-r border-border-subtle bg-bg-tertiary/50 md:flex md:w-64',
        hasMain || openThread ? 'hidden' : 'flex'
      )}>
        <Sidebar
          status={status.data}
          conversations={conversations}
          loading={list.isLoading}
          error={list.isError ? list.error.message : null}
          threadBadge={list.data?.threads}
          selectedId={selectedId}
          view={view}
          openThread={openThread}
          onSelectConversation={selectConversation}
          onSelectView={selectView}
          onOpenThread={showThread}
        />
      </aside>

      <section className={cn(
        'min-w-0 flex-1 flex-col',
        openThread || (dmAgent && aiOpen) ? 'hidden lg:flex' : hasMain ? 'flex' : 'hidden md:flex'
      )}>
        {view === 'reply' ? (
          <div className="min-h-0 flex-1 overflow-auto"><ReplyWorkbench /></div>
        ) : view === 'threads' ? (
          <ThreadsView conversations={conversations} openThread={openThread} onOpenThread={showThread} onBack={back} />
        ) : selected ? (
          <ConversationView
            key={selected.id}
            conversation={selected}
            activeThreadTs={openThread?.channelId === selected.id ? openThread.threadTs : null}
            onOpenThread={ts => showThread({ channelId: selected.id, threadTs: ts })}
            onBack={back}
            onOpenAgent={dmAgent ? () => update({ ai: '1' }) : undefined}
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-sm text-text-muted">
            <MessagesSquare className="h-8 w-8 opacity-40" />
            从左侧选择一个频道、私信或 thread
          </div>
        )}
      </section>

      {dmAgent && (
        <aside className={cn(
          'min-w-0 flex-1 flex-col border-l border-border-subtle lg:flex lg:w-[420px] lg:flex-none',
          aiOpen ? 'flex' : 'hidden'
        )}>
          <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2.5">
            <h2 className="min-w-0 flex-1 truncate text-[15px] font-bold text-text-primary">AI 回复 · {dmAgent.name}</h2>
            <button type="button" onClick={() => update({ ai: null })} className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover lg:hidden" aria-label="回到对话">
              <X className="h-4 w-4" />
            </button>
          </div>
          <SlackAgentPanel
            key={dmAgent.id}
            channelId={dmAgent.id}
            threadTs={null}
            latestTs={dmAgent.latest_ts}
            slackLink={`${teamUrl}/archives/${dmAgent.id}`}
          />
        </aside>
      )}

      {openThread && (
        <aside className="flex min-w-0 flex-1 flex-col border-l border-border-subtle lg:w-[420px] lg:flex-none">
          <ThreadPanel
            key={`${openThread.channelId}-${openThread.threadTs}`}
            channelId={openThread.channelId}
            channelName={threadChannel ? `# ${threadChannel.name}` : openThread.channelId}
            threadTs={openThread.threadTs}
            onClose={closeThread}
            onOpenChannel={() => selectConversation(openThread.channelId)}
          />
        </aside>
      )}
    </div>
  );
}
