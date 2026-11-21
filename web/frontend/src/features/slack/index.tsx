import { useSearchParams } from 'react-router-dom';
import { Loader2, Sparkles, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ConversationView } from './inbox/ConversationView';
import { CredentialsPanel } from './inbox/CredentialsPanel';
import { useSlackConversations, useSlackStatus } from './inbox/hooks';
import { ActivityList } from './inbox/ActivityList';
import { ThreadPanel } from './inbox/ThreadPanel';
import { TodoView } from './inbox/TodoView';
import type { OpenThread, SlackActivityItem } from './inbox/types';
import { DmReplyPanel } from './reply/DmReplyPanel';
import { SlackTranslateMode } from './translate/SlackTranslateMode';

const TS_RE = /^\d{9,11}\.\d{1,6}$/;

/**
 * Slack 页（2026-11-22 重新分工）：看消息、自己找要翻的帖子、处理找我的事。
 * - 左栏：一行筛选 + 动态列表；右边「待办」回到中间的我的待办。
 * - 中栏：没选会话时是「我的待办」；选了 thread 是消息流（顶部：翻译这个帖子 / 翻译全部 / 总结）；选了私信是消息流。
 * - 右栏：私信时是回复面板。
 * - 翻译模式（mode=translate）：三栏 ① 原文 + 配图 | ② 译文 / 优化 / 标题 | ③ 原 thread，整页显示。
 * URL：c=会话，tc+t=打开的 thread，mode=translate，ai=1 窄屏上显示私信的回复面板。
 */
export function SlackFeature() {
  const [params, setParams] = useSearchParams();
  const selectedId = params.get('c');
  const tc = params.get('tc');
  const t = params.get('t');
  const openThread: OpenThread | null = tc && t && TS_RE.test(t) ? { channelId: tc, threadTs: t } : null;
  const translating = !!openThread && params.get('mode') === 'translate';

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
  const selectConversation = (id: string) => update({ c: id, tc: null, t: null, ai: null, mode: null });
  // thread 一律在中栏单独打开（不带整个频道）
  const showThread = (thread: OpenThread) => update({ tc: thread.channelId, t: thread.threadTs, c: null, ai: null, mode: null });
  const openFrom = (channelId: string, threadTs: string | null) =>
    threadTs ? showThread({ channelId, threadTs }) : selectConversation(channelId);
  const openActivity = (item: SlackActivityItem) => {
    if (item.type === 'thread' && item.thread_ts) showThread({ channelId: item.channel_id, threadTs: item.thread_ts });
    else selectConversation(item.channel_id);
  };
  const translate = (channelId: string, threadTs: string) =>
    update({ tc: channelId, t: threadTs, c: null, ai: null, mode: 'translate' });
  const closeThread = () => update({ tc: null, t: null, mode: null });
  const aiOpen = params.get('ai') === '1';
  const back = () => update({ c: null, tc: null, t: null, mode: null });

  if (status.isLoading) {
    return <div className="flex h-full items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-text-muted" /></div>;
  }
  if (status.isError) {
    return <div className="p-6 text-sm text-error">读取 Slack 状态失败：{status.error.message}</div>;
  }
  if (!ready || !status.data) {
    return <div className="h-full overflow-auto"><CredentialsPanel status={status.data} /></div>;
  }

  const threadChannel = openThread ? conversations.find(c => c.id === openThread.channelId) : null;
  if (translating && openThread) {
    return (
      <SlackTranslateMode
        key={`${openThread.channelId}-${openThread.threadTs}`}
        channelId={openThread.channelId}
        threadTs={openThread.threadTs}
        channelName={threadChannel?.name ?? ''}
        onExit={() => update({ mode: null })}
      />
    );
  }

  const hasMain = !!selected || !!openThread;
  // 私信（含群聊私信）打开时，右栏是回复面板；宽屏一直显示，窄屏点「AI 回复」才切过去
  const dm = !openThread && selected && (selected.kind === 'im' || selected.kind === 'mpim') ? selected : null;
  const teamUrl = status.data.url || 'https://app.slack.com';
  const selection = openThread
    ? { channelId: openThread.channelId, threadTs: openThread.threadTs }
    : selected ? { channelId: selected.id, threadTs: null } : null;

  return (
    <div className="flex h-full min-h-0">
      <aside className={cn(
        'w-full shrink-0 flex-col border-r border-border-subtle bg-[#faf6f5] md:flex md:w-[360px]',
        hasMain ? 'hidden' : 'flex'
      )}>
        <ActivityList
          selection={selection}
          onOpen={openActivity}
          onShowTodos={back}
          todosActive={!hasMain}
          onBack={hasMain ? back : undefined}
        />
      </aside>

      <section className={cn(
        'min-w-0 flex-1 flex-col',
        dm && aiOpen ? 'hidden lg:flex' : hasMain ? 'flex' : 'hidden md:flex'
      )}>
        {openThread ? (
          <ThreadPanel
            key={`${openThread.channelId}-${openThread.threadTs}`}
            channelId={openThread.channelId}
            channelName={threadChannel ? `#${threadChannel.name}` : openThread.channelId}
            threadTs={openThread.threadTs}
            onClose={closeThread}
            onOpenChannel={() => selectConversation(openThread.channelId)}
            onTranslatePost={() => translate(openThread.channelId, openThread.threadTs)}
          />
        ) : selected ? (
          <ConversationView
            key={selected.id}
            conversation={selected}
            activeThreadTs={null}
            onOpenThread={ts => showThread({ channelId: selected.id, threadTs: ts })}
            onBack={back}
            onOpenAgent={dm ? () => update({ ai: '1' }) : undefined}
          />
        ) : (
          <TodoView onOpen={openFrom} onTranslate={translate} />
        )}
      </section>

      {dm && (
        <aside className={cn(
          'min-w-0 flex-1 flex-col border-l border-border-subtle bg-[#fcfaf9] lg:flex lg:w-[420px] lg:flex-none',
          aiOpen ? 'flex' : 'hidden'
        )}>
          <div className="flex items-center gap-2 border-b border-border-subtle px-4 py-2.5">
            <Sparkles className="h-4 w-4 text-primary-500" />
            <h2 className="min-w-0 flex-1 truncate text-[14px] font-semibold text-text-primary">帮我回复 · {dm.name}</h2>
            <button type="button" onClick={() => update({ ai: null })} className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover lg:hidden" aria-label="回到对话">
              <X className="h-4 w-4" />
            </button>
          </div>
          <DmReplyPanel
            key={dm.id}
            channelId={dm.id}
            latestTs={dm.latest_ts}
            hasUnreads={dm.has_unreads}
            slackLink={`${teamUrl}/archives/${dm.id}`}
          />
        </aside>
      )}
    </div>
  );
}
