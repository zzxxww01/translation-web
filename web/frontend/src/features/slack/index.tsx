import { useSearchParams } from 'react-router-dom';
import { Loader2, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SlackAgentPanel } from './agent/SlackAgentPanel';
import { ConversationView } from './inbox/ConversationView';
import { CredentialsPanel } from './inbox/CredentialsPanel';
import { useMediaQuery, useSlackConversations, useSlackReplies, useSlackStatus } from './inbox/hooks';
import { newestTs, parseSlackView, type SlackView } from './inbox/lib';
import { ActivityList } from './inbox/ActivityList';
import { ThreadPanel } from './inbox/ThreadPanel';
import { DigestView } from './inbox/DigestView';
import { ThreadsView } from './inbox/ThreadsView';
import { Overview } from './inbox/Overview';
import type { OpenThread, SlackActivityItem } from './inbox/types';
import { ReplyWorkbench } from './ReplyWorkbench';

const TS_RE = /^\d{9,11}\.\d{1,6}$/;

/** 宽屏右栏：thread 背后的帖子翻译助手（和私信的回复助手同一个位置） */
function ThreadAgentAside({ thread }: { thread: OpenThread }) {
  const replies = useSlackReplies(thread.channelId, thread.threadTs);
  const messages = replies.data?.messages ?? [];
  const latestTs = newestTs(messages);
  const root = messages[0];
  return (
    <aside className="flex w-[420px] min-w-0 flex-none flex-col border-l border-border-subtle">
      <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2.5">
        <h2 className="min-w-0 flex-1 truncate text-[15px] font-bold text-text-primary">AI 翻译 · 帖子翻译助手</h2>
      </div>
      <SlackAgentPanel
        key={`${thread.channelId}-${thread.threadTs}`}
        channelId={thread.channelId}
        threadTs={thread.threadTs}
        latestTs={latestTs}
        slackLink={root?.permalink ?? null}
      />
    </aside>
  );
}

/**
 * Slack 页：左栏「动态」（每行一个 thread 或私信，按最近活动排序），点开在中栏只看那一个 thread / 私信。
 * 2026-11-18 用户反馈频道视图太乱，改成活动列；整个频道的消息流仍可从 thread 标题下的频道名进入。
 * URL：c=会话（私信或整个频道），view=digest|reply|threads，tc+t=打开的 thread，ai=1 窄屏上显示私信的 AI。
 * 每个 thread 背后是帖子翻译助手（thread 的「AI 翻译」页），每个私信背后是回复助手（私信打开时的右栏）。
 */
export function SlackFeature() {
  const [params, setParams] = useSearchParams();
  const view = parseSlackView(params.get('view'));
  const selectedId = view ? null : params.get('c');
  const tc = params.get('tc');
  const t = params.get('t');
  const openThread: OpenThread | null = tc && t && TS_RE.test(t) ? { channelId: tc, threadTs: t } : null;

  const status = useSlackStatus();
  // 够宽（≥1280px）时 thread 也三栏：动态 | thread | AI；再窄中栏会被挤得太窄，AI 留在 thread 的标签页里
  const wide = useMediaQuery('(min-width: 1280px)');
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
  // 速览 / 搜索结果里点一条：去对应会话，thread 的话右栏同时打开
  const openFrom = (channelId: string, threadTs: string | null) =>
    threadTs ? showThread({ channelId, threadTs }) : update({ c: channelId, view: null, q: null, ai: null, tc: null, t: null });
  // thread 一律在中栏单独打开（不带整个频道）
  const showThread = (thread: OpenThread) => update({ tc: thread.channelId, t: thread.threadTs, c: null, view: null, q: null, ai: null });
  const openActivity = (item: SlackActivityItem) => {
    if (item.type === 'thread' && item.thread_ts) showThread({ channelId: item.channel_id, threadTs: item.thread_ts });
    else selectConversation(item.channel_id);
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

  const hasMain = !!selected || !!view || !!openThread;
  const threadChannel = openThread ? conversations.find(c => c.id === openThread.channelId) : null;
  // 私信（含群聊私信）打开时，右栏是回复助手；宽屏一直显示，窄屏点「AI 回复」才切过去
  const dmAgent = !openThread && selected && (selected.kind === 'im' || selected.kind === 'mpim') ? selected : null;
  const teamUrl = status.data.url || 'https://app.slack.com';
  const selection = openThread
    ? { channelId: openThread.channelId, threadTs: openThread.threadTs }
    : selected ? { channelId: selected.id, threadTs: null } : null;

  return (
    <div className="flex h-full min-h-0">
      <aside className={cn(
        'w-full shrink-0 flex-col border-r border-border-subtle bg-bg-tertiary/40 md:flex md:w-[380px]',
        hasMain ? 'hidden' : 'flex'
      )}>
        <ActivityList
          selection={selection}
          view={view}
          onOpen={openActivity}
          onSelectView={selectView}
          onBack={hasMain ? back : undefined}
        />
      </aside>

      <section className={cn(
        'min-w-0 flex-1 flex-col',
        dmAgent && aiOpen ? 'hidden lg:flex' : hasMain ? 'flex' : 'hidden md:flex'
      )}>
        {openThread ? (
          <ThreadPanel
            key={`${openThread.channelId}-${openThread.threadTs}`}
            channelId={openThread.channelId}
            channelName={threadChannel ? `# ${threadChannel.name}` : openThread.channelId}
            threadTs={openThread.threadTs}
            onClose={closeThread}
            onOpenChannel={() => selectConversation(openThread.channelId)}
            autoSummary
            aiInSidebar={wide}
          />
        ) : view === 'reply' ? (
          <div className="min-h-0 flex-1 overflow-auto"><ReplyWorkbench /></div>
        ) : view === 'digest' ? (
          <DigestView onOpen={openFrom} onBack={back} />
        ) : view === 'threads' ? (
          <ThreadsView conversations={conversations} openThread={openThread} onOpenThread={showThread} onBack={back} />
        ) : selected ? (
          <ConversationView
            key={selected.id}
            conversation={selected}
            activeThreadTs={null}
            onOpenThread={ts => showThread({ channelId: selected.id, threadTs: ts })}
            onBack={back}
            onOpenAgent={dmAgent ? () => update({ ai: '1' }) : undefined}
          />
        ) : (
          <Overview onOpen={openActivity} onDigest={() => selectView('digest')} />
        )}
      </section>

      {openThread && wide && <ThreadAgentAside thread={openThread} />}

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

    </div>
  );
}
