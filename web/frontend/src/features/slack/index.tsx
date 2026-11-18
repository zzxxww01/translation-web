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
import { DigestView } from './inbox/DigestView';
import { SearchView } from './inbox/SearchView';
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
  const selectView = (v: SlackView) => update({ view: v, c: null, tc: null, t: null, q: null });
  const search = (q: string) => update({ view: 'search', q, c: null, tc: null, t: null });
  const searchQuery = params.get('q') ?? '';
  // 速览 / 搜索结果里点一条：去对应会话，thread 的话右栏同时打开
  const openFrom = (channelId: string, threadTs: string | null) =>
    update({ c: channelId, view: null, q: null, ai: null, tc: threadTs ? channelId : null, t: threadTs });
  const showThread = (thread: OpenThread) => {
    // 从侧栏或 Threads 页点 thread：中栏切到它所在的频道（Threads 页保持不动），右栏打开 thread
    const keepThreadsView = view === 'threads';
    update({ tc: thread.channelId, t: thread.threadTs, ...(keepThreadsView ? {} : { c: thread.channelId, view: null }) });
  };
  const closeThread = () => update({ tc: null, t: null });
  const aiOpen = params.get('ai') === '1';
  const back = () => update({ c: null, view: null, tc: null, t: null, q: null });

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
          onSearch={search}
        />
      </aside>

      <section className={cn(
        'min-w-0 flex-1 flex-col',
        openThread || (dmAgent && aiOpen) ? 'hidden lg:flex' : hasMain ? 'flex' : 'hidden md:flex'
      )}>
        {view === 'reply' ? (
          <div className="min-h-0 flex-1 overflow-auto"><ReplyWorkbench /></div>
        ) : view === 'digest' ? (
          <DigestView onOpen={openFrom} onBack={back} />
        ) : view === 'search' ? (
          <SearchView key={searchQuery} query={searchQuery} onSearch={search} onOpen={openFrom} onBack={back} />
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
          <div className="flex h-full items-center justify-center p-6">
            <div className="max-w-md space-y-3 text-sm text-text-secondary">
              <div className="flex items-center gap-2 text-text-primary">
                <MessagesSquare className="h-5 w-5 text-primary-500" />
                <span className="font-semibold">这里是你的 Slack（只读）</span>
              </div>
              <ul className="list-disc space-y-1.5 pl-5">
                <li><b>频道</b>：你加入的公开 / 私有频道。点频道名看消息；下面缩进的是这个频道最近有回复的 <b>thread</b>（某条消息下面的回复串），标题是根消息的第一行原文。</li>
                <li><b>私信</b>：一对一的对话，和几个人的小群（群聊私信）。</li>
                <li><b>AI 速览</b>：把所有未读整理成中文要点。<b>我参与的 thread</b>：你回复过或被 @ 过的回复串。</li>
                <li>默认显示英文原文。鼠标移到消息上点「译」翻这一条，或在顶栏打开「全部中文」。</li>
                <li>右栏的 AI（翻译帖子、建议回复）要点「开始」才会跑；momo 不会往 Slack 发任何东西，也不改 Slack 的已读。</li>
              </ul>
            </div>
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
