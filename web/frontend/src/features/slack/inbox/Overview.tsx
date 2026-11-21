import { AtSign, FileText, Loader2, Mail, MessagesSquare, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useSlackActivity } from './hooks';
import { clockTime, dayLabel, emojify, stripLeadingMentions } from './lib';
import { stripMrkdwn } from './mrkdwn';
import type { SlackActivityItem } from './types';

function title(item: SlackActivityItem): string {
  if (item.type === 'dm') return item.channel_name;
  const line = (item.root?.text || '').split('\n').map(s => s.trim()).find(Boolean) || '（无文字）';
  return emojify(stripMrkdwn(stripLeadingMentions(line)));
}

function Stat({ icon: Icon, label, value, tone }: { icon: typeof Mail; label: string; value: number; tone?: 'alert' }) {
  return (
    <div className="rounded-lg border border-border-subtle bg-white px-3 py-2.5">
      <div className="flex items-center gap-1.5 text-xs text-text-muted"><Icon className="h-3.5 w-3.5" /> {label}</div>
      <div className={cn('mt-0.5 text-2xl font-semibold tabular-nums', tone === 'alert' && value > 0 ? 'text-error' : 'text-text-primary')}>
        {value}
      </div>
    </div>
  );
}

/**
 * 没选会话时中栏的「概览」：未读、@我、新帖、私信各几条，加上最需要处理的几行（@我 / 私信 / 新帖在前）。
 * 数据和左栏「动态」是同一份（react-query 共用缓存），不额外请求。
 */
export function Overview({ onOpen, onDigest }: { onOpen: (item: SlackActivityItem) => void; onDigest: () => void }) {
  const activity = useSlackActivity(true);
  const items = activity.data ?? [];
  const unread = items.filter(i => i.has_unreads);
  const mentions = items.filter(i => i.mentions_me);
  const posts = items.filter(i => i.type === 'thread' && !i.reply_count);
  const dms = unread.filter(i => i.type === 'dm');
  // 要先看的：@我 > 未读私信 > 未读新帖 > 其他未读
  const rank = (i: SlackActivityItem) =>
    i.mentions_me ? 0 : i.type === 'dm' ? 1 : !i.reply_count ? 2 : 3;
  const todo = [...new Set([...mentions, ...unread])].sort((a, b) => rank(a) - rank(b)).slice(0, 8);

  return (
    <div className="h-full overflow-auto">
      <div className="mx-auto max-w-2xl space-y-5 p-6">
        <div className="flex items-center gap-2">
          <h2 className="flex-1 text-lg font-semibold text-text-primary">概览</h2>
          <button
            type="button"
            onClick={onDigest}
            className="inline-flex items-center gap-1 rounded-md border border-primary-100 bg-primary-50/60 px-2.5 py-1 text-xs text-primary-700 hover:bg-primary-50"
          >
            <Sparkles className="h-3.5 w-3.5" /> AI 速览：未读整理成中文要点
          </button>
        </div>

        {activity.isLoading ? (
          <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat icon={MessagesSquare} label="未读" value={unread.length} />
              <Stat icon={AtSign} label="@我" value={mentions.length} tone="alert" />
              <Stat icon={Mail} label="未读私信" value={dms.length} />
              <Stat icon={FileText} label="7 天内新帖" value={posts.length} />
            </div>

            <div>
              <div className="mb-1.5 text-xs font-semibold text-text-muted">先看这些</div>
              {todo.length === 0 ? (
                <div className="rounded-lg border border-dashed border-border px-4 py-6 text-center text-sm text-text-muted">
                  都看完了。左边是最近 7 天的全部动态。
                </div>
              ) : (
                <ul className="divide-y divide-border-subtle overflow-hidden rounded-lg border border-border-subtle bg-white">
                  {todo.map(item => (
                    <li key={`${item.channel_id}-${item.thread_ts ?? 'dm'}`}>
                      <button
                        type="button"
                        onClick={() => onOpen(item)}
                        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-bg-hover"
                      >
                        {item.mentions_me
                          ? <span className="shrink-0 rounded-full bg-error px-1.5 text-[11px] font-semibold text-white">@我</span>
                          : <span className="shrink-0 rounded-full bg-bg-hover px-1.5 text-[11px] text-text-secondary">
                              {item.type === 'dm' ? '私信' : item.reply_count ? 'thread' : '新帖'}
                            </span>}
                        <span className="min-w-0 flex-1 truncate text-sm text-text-primary">{title(item)}</span>
                        <span className="shrink-0 text-[11px] text-text-muted">
                          {dayLabel(item.latest_ts) === '今天' ? clockTime(item.latest_ts) : dayLabel(item.latest_ts).replace(/ .*/, '')}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <ul className="list-disc space-y-1 pl-5 text-xs leading-relaxed text-text-muted">
              <li>点一行只看那一个 thread / 私信；thread 的 AI 翻译、私信的 AI 回复都要点「开始」才会跑。</li>
              <li>快捷键：j / k 下一条 / 上一条，t 全部中文，Esc 关闭。</li>
              <li>momo 只读：不会往 Slack 发任何东西，已读只记在 momo 里。</li>
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
