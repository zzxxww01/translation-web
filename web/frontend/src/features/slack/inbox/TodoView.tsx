import { useState } from 'react';
import { CheckCheck, ChevronDown, ChevronRight, FileText, Loader2, Mail, MessageSquareText, RefreshCw, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useMarkAllRead, useSaveSlackSettings, useSlackSettings, useTodos } from './hooks';
import { clockTime, dayLabel } from './lib';
import type { SlackTodo } from './types';

const ACTION: Record<SlackTodo['action'], { label: string; tone: string }> = {
  reply: { label: '要回复', tone: 'bg-error/10 text-error' },
  do: { label: '要处理', tone: 'bg-amber-100 text-amber-800' },
  read: { label: '看一下', tone: 'bg-bg-hover text-text-secondary' },
};

function when(ts: string) {
  return dayLabel(ts) === '今天' ? clockTime(ts) : dayLabel(ts).replace(/ .*/, '');
}

function TodoCard({ item, onOpen, onTranslate }: {
  item: SlackTodo;
  onOpen: (channelId: string, threadTs: string | null) => void;
  onTranslate: (channelId: string, threadTs: string) => void;
}) {
  const action = ACTION[item.action];
  const draft = item.draft && !item.draft.no_post ? item.draft : null;
  return (
    <div className="group flex gap-3 rounded-xl border border-border-subtle bg-white px-4 py-3 shadow-sm transition-shadow hover:shadow-md">
      <div className={cn(
        'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full',
        item.kind === 'dm' ? 'bg-sky-50 text-sky-600' : 'bg-primary-50 text-primary-600'
      )}>
        {item.kind === 'dm' ? <Mail className="h-4 w-4" /> : <MessageSquareText className="h-4 w-4" />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-start gap-2">
          <p className="min-w-0 flex-1 text-[14px] font-medium leading-snug text-text-primary">
            {item.task || item.title}
          </p>
          <span className={cn('shrink-0 rounded-full px-2 py-0.5 text-[11px] font-medium', action.tone)}>{action.label}</span>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-x-1.5 text-xs text-text-muted">
          <span>{item.kind === 'dm' ? `私信 · ${item.channel_name}` : `#${item.channel_name}`}</span>
          {item.kind === 'mention' && item.title && <span className="max-w-[16rem] truncate">· {item.title}</span>}
          <span>· {item.from.join('、')}</span>
          {item.count > 1 && <span>· {item.count} 条</span>}
          <span>· {when(item.latest_ts)}</span>
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onOpen(item.channel_id, item.thread_ts)}
            className="rounded-lg border border-border-subtle px-2.5 py-1 text-xs text-text-secondary transition-colors hover:bg-bg-hover"
          >
            {item.kind === 'dm' ? '打开私信' : '打开帖子'}
          </button>
          {item.kind === 'mention' && item.thread_ts && (
            <button
              type="button"
              onClick={() => onTranslate(item.channel_id, item.thread_ts as string)}
              className={cn(
                'inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-medium transition-colors',
                draft ? 'bg-primary-500 text-white hover:bg-primary-600' : 'border border-primary-200 text-primary-700 hover:bg-primary-50'
              )}
            >
              {draft ? <Sparkles className="h-3.5 w-3.5" /> : <FileText className="h-3.5 w-3.5" />}
              {draft ? `查看翻译 · v${draft.versions}` : '翻译这个帖子'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * 没选会话时的中栏：我的待办。只看还没读的 @我 和私信，一次模型调用告诉我每件事是谁、要我干什么。
 * 被 @用户组 / @here 群发提到的放在下面「不用处理」。
 */
export function TodoView({ onOpen, onTranslate }: {
  onOpen: (channelId: string, threadTs: string | null) => void;
  onTranslate: (channelId: string, threadTs: string) => void;
}) {
  const todos = useTodos(true);
  const settings = useSlackSettings();
  const saveSettings = useSaveSlackSettings();
  const markAll = useMarkAllRead();
  const [showFyi, setShowFyi] = useState(false);
  const items = todos.data?.items ?? [];
  const fyi = todos.data?.fyi ?? [];
  const auto = settings.data?.auto_translate_mentions ?? true;

  const doneAll = () => markAll.mutate([...items, ...fyi].map(t => ({
    channel_id: t.mark.channel_id, ts: t.mark.ts, thread_ts: t.mark.thread_ts ?? null,
  })));

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto max-w-2xl px-6 pb-12 pt-6">
        <div className="flex items-end gap-3">
          <div className="min-w-0 flex-1">
            <h2 className="text-xl font-semibold text-text-primary" style={{ fontFamily: 'var(--font-display)' }}>我的待办</h2>
            <p className="mt-0.5 text-xs text-text-muted">只看还没读的 @我 和私信，AI 帮你理出每件事是谁、要你干什么</p>
          </div>
          <button
            type="button"
            onClick={() => void todos.refetch()}
            disabled={todos.isFetching}
            className="rounded-md p-1.5 text-text-muted hover:bg-bg-hover hover:text-text-primary"
            title="重新整理"
            aria-label="重新整理"
          >
            <RefreshCw className={cn('h-4 w-4', todos.isFetching && 'animate-spin')} />
          </button>
        </div>

        <label className="mt-4 flex cursor-pointer items-center gap-3 rounded-xl border border-border-subtle bg-white/70 px-4 py-2.5">
          <Sparkles className="h-4 w-4 shrink-0 text-primary-500" />
          <span className="min-w-0 flex-1 text-sm text-text-primary">
            有人在 thread 里 @我 时，自动把那个帖子翻好
            <span className="block text-xs text-text-muted">后台自动跑提取 → 翻译 → 标题，翻好的会标「已自动翻好」</span>
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={auto}
            onClick={() => saveSettings.mutate({ auto_translate_mentions: !auto })}
            className={cn('relative h-6 w-11 shrink-0 rounded-full transition-colors', auto ? 'bg-primary-500' : 'bg-border')}
          >
            <span className={cn('absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all', auto ? 'left-[22px]' : 'left-0.5')} />
          </button>
        </label>

        <div className="mt-5 space-y-3">
          {todos.isLoading && (
            <div className="flex flex-col items-center gap-2 py-12 text-sm text-text-muted">
              <Loader2 className="h-5 w-5 animate-spin" /> 正在读未读的 @我 和私信…
            </div>
          )}
          {todos.isError && <div className="rounded-lg bg-error/5 px-4 py-3 text-sm text-error">待办没整理出来：{todos.error.message}</div>}
          {todos.data && items.length === 0 && (
            <div className="rounded-xl border border-dashed border-border px-4 py-10 text-center">
              <CheckCheck className="mx-auto h-7 w-7 text-success" />
              <p className="mt-2 text-sm text-text-primary">没有待办</p>
              <p className="mt-0.5 text-xs text-text-muted">没有未读的 @我 和私信。左边是最近 7 天的全部动态。</p>
            </div>
          )}
          {items.map(item => (
            <TodoCard key={`${item.channel_id}-${item.thread_ts ?? 'dm'}`} item={item} onOpen={onOpen} onTranslate={onTranslate} />
          ))}
        </div>

        {fyi.length > 0 && (
          <div className="mt-6">
            <button type="button" onClick={() => setShowFyi(v => !v)} className="flex items-center gap-1 text-xs font-semibold text-text-muted hover:text-text-secondary">
              {showFyi ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
              不用处理（群发 @）· {fyi.length}
            </button>
            {showFyi && (
              <ul className="mt-2 divide-y divide-border-subtle overflow-hidden rounded-xl border border-border-subtle bg-white/70">
                {fyi.map(item => (
                  <li key={`${item.channel_id}-${item.thread_ts}`}>
                    <button type="button" onClick={() => onOpen(item.channel_id, item.thread_ts)} className="flex w-full items-center gap-2 px-4 py-2 text-left text-sm hover:bg-bg-hover">
                      <span className="min-w-0 flex-1 truncate text-text-secondary">{item.from.join('、')} 在「{item.title}」里 @了大家</span>
                      <span className="shrink-0 text-xs text-text-muted">{when(item.latest_ts)}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {(items.length > 0 || fyi.length > 0) && (
          <div className="mt-6 flex justify-center">
            <button
              type="button"
              onClick={doneAll}
              disabled={markAll.isPending}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border-subtle bg-white px-4 py-2 text-sm text-text-secondary shadow-sm hover:bg-bg-hover"
              title="把这些 @ 和私信标为已读（只记在 momo 里，Slack 的未读不变）"
            >
              <CheckCheck className="h-4 w-4" /> 都处理完了
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
