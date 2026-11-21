import { useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronRight, Languages, Loader2, Sparkles } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AgentBadge } from '../agent/AgentBadge';
import { useSlackAgentRuns } from '../agent/agentRuns';
import { useShowZh } from './ai';
import { Avatar } from './MessageItem';
import { useMarkAllRead, useSlackActivity } from './hooks';
import { clockTime, emojify, groupOf, stripLeadingMentions, type GroupId, type SlackView } from './lib';
import { stripMrkdwn } from './mrkdwn';
import type { SlackActivityItem, SlackMessage } from './types';

/** 正在看的那一行：thread 用（会话, thread_ts），私信用会话 id */
export interface ActivitySelection {
  channelId: string;
  threadTs: string | null;
}

/**
 * 左栏分组（2026-11-22 用户定的顺序）：别人等你的在前，然后是要翻译的新帖，再是自己参与的讨论，最后是其他。
 * 每条只进一个组，按这个顺序先到先得。
 */

const GROUPS: { id: GroupId; title: string; hint: string }[] = [
  { id: 'mentions', title: '@我', hint: '有人 @ 了你' },
  { id: 'dms', title: '私信', hint: '私信和群聊私信' },
  { id: 'posts', title: '新帖 · 待翻译', hint: '最近 7 天还没人回复的帖子' },
  { id: 'following', title: '我参与的 thread', hint: '你发起或回复过的 thread' },
  { id: 'others', title: '其他 thread', hint: '频道里最近 7 天的其他讨论' },
];

const OTHERS_PREVIEW = 5;


interface ActivityListProps {
  selection: ActivitySelection | null;
  view: SlackView | null;
  onOpen: (item: SlackActivityItem) => void;
  onSelectView: (view: SlackView) => void;
  /** Esc：关掉正在看的 thread / 会话 */
  onBack?: () => void;
}

/** 在输入框里打字时不响应快捷键 */
function isTyping(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  return !!el && (el.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName));
}

/** 消息第一行（去掉 *加粗*、`代码` 等格式记号，表情码换成 emoji）；没有文字时用附件名 */
function firstLine(message: SlackMessage | null | undefined, max = 80, asTitle = false): string {
  if (!message) return '';
  const raw = (message.text || '').split('\n').map(s => s.trim()).find(Boolean)
    || message.attachments[0]?.title || message.files[0]?.name || '（无文字）';
  const line = asTitle ? stripLeadingMentions(raw) : raw;
  const text = emojify(stripMrkdwn(line));
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

/** 今天显示时刻，昨天显示「昨天」，更早显示月/日 */
function shortTime(ts: string, now = new Date()): string {
  const d = new Date(parseFloat(ts) * 1000);
  const days = Math.round((new Date(now).setHours(0, 0, 0, 0) - new Date(d).setHours(0, 0, 0, 0)) / 86_400_000);
  if (days === 0) return clockTime(ts);
  if (days === 1) return '昨天';
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

const keyOf = (item: SlackActivityItem) => `${item.channel_id}-${item.thread_ts ?? 'dm'}`;

// 折叠了哪些组：记在浏览器里，下次打开还是这样
const COLLAPSED_KEY = 'slack-sidebar-collapsed';
function loadCollapsed(): Set<GroupId> {
  try {
    return new Set(JSON.parse(localStorage.getItem(COLLAPSED_KEY) || '[]'));
  } catch {
    return new Set();
  }
}

/**
 * 左栏：最上面两个工具入口（AI 速览、回复工作台），下面按「@我 / 私信 / 新帖 / 我参与的 / 其他」分组列出
 * 最近 7 天的 thread、新帖和私信。2026-11-22 用户觉得筛选按钮 + 小图标看不懂，改成直接摆出来的分组。
 */
export function ActivityList({ selection, view, onOpen, onSelectView, onBack }: ActivityListProps) {
  const activity = useSlackActivity(true);
  const markAll = useMarkAllRead();
  const agents = useSlackAgentRuns();
  const toggleZh = useShowZh(state => state.toggleZh);
  const [collapsed, setCollapsed] = useState<Set<GroupId>>(loadCollapsed);
  const [othersAll, setOthersAll] = useState(false);

  const all = activity.data ?? [];
  const unreadTotal = all.filter(i => i.has_unreads).length;
  const groups = GROUPS.map(g => {
    const items = all.filter(i => groupOf(i) === g.id);
    const shown = collapsed.has(g.id) ? [] : g.id === 'others' && !othersAll ? items.slice(0, OTHERS_PREVIEW) : items;
    return { ...g, items, shown, unread: items.filter(i => i.has_unreads) };
  }).filter(g => g.items.length > 0);
  const visible = groups.flatMap(g => g.shown);
  // 只有一个频道时每行都写同一个频道名没意义
  const manyChannels = new Set(all.filter(i => i.type === 'thread').map(i => i.channel_id)).size > 1;

  const toggleGroup = (id: GroupId) => setCollapsed(prev => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    localStorage.setItem(COLLAPSED_KEY, JSON.stringify([...next]));
    return next;
  });
  const markGroup = (items: SlackActivityItem[]) => markAll.mutate(items.map(i => ({
    channel_id: i.channel_id, ts: i.latest_ts, thread_ts: i.thread_ts,
  })));

  // 键盘：j / k 按分组从上往下切换并打开，t 全部中文，Esc 关闭
  const keys = useRef({ visible, selection, onOpen, onBack, toggleZh });
  useEffect(() => {
    keys.current = { visible, selection, onOpen, onBack, toggleZh };
  });
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target)) return;
      const { visible: list, selection: sel, onOpen: open, onBack: back, toggleZh: zh } = keys.current;
      if (e.key === 'j' || e.key === 'k') {
        if (list.length === 0) return;
        const at = sel ? list.findIndex(i => i.channel_id === sel.channelId && i.thread_ts === sel.threadTs) : -1;
        const next = at < 0 ? 0 : Math.min(list.length - 1, Math.max(0, at + (e.key === 'j' ? 1 : -1)));
        if (next !== at) open(list[next]);
        e.preventDefault();
      } else if (e.key === 't') {
        zh();
      } else if (e.key === 'Escape' && back) {
        back();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="min-h-0 flex-1 overflow-auto" aria-label="Slack 动态">
      {/* 工具入口：整行带说明，和 Slack 侧栏最上面的 Threads / Activity 一样 */}
      <div className="border-b border-border-subtle py-1.5">
        <ToolRow
          icon={Sparkles}
          label="AI 速览"
          hint={unreadTotal ? `${unreadTotal} 条未读整理成中文` : '未读整理成中文要点'}
          active={view === 'digest'}
          onClick={() => onSelectView('digest')}
        />
        <ToolRow
          icon={Languages}
          label="回复工作台"
          hint="贴英文 / 写中文草稿，出三版回复"
          active={view === 'reply'}
          onClick={() => onSelectView('reply')}
        />
      </div>

      {activity.isLoading && <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}
      {activity.isError && (
        <div className="p-4 text-sm text-error">
          动态没加载出来：{activity.error.message}
          <button type="button" onClick={() => void activity.refetch()} className="ml-2 text-primary-700 hover:underline">重试</button>
        </div>
      )}
      {activity.data && all.length === 0 && <div className="p-6 text-center text-sm text-text-muted">最近 7 天没有动态</div>}

      {groups.map(g => (
        <section key={g.id} aria-label={g.title}>
          <div className="group/head sticky top-0 z-10 flex items-center gap-1 bg-[#faf6f5] px-2 pb-1 pt-3">
            <button
              type="button"
              onClick={() => toggleGroup(g.id)}
              aria-expanded={!collapsed.has(g.id)}
              title={g.hint}
              className="flex min-w-0 flex-1 items-center gap-1 rounded px-1 text-left text-[13px] font-semibold text-text-secondary hover:text-text-primary"
            >
              {collapsed.has(g.id) ? <ChevronRight className="h-3.5 w-3.5 shrink-0" /> : <ChevronDown className="h-3.5 w-3.5 shrink-0" />}
              <span className="truncate">{g.title}</span>
              <span className="font-normal text-text-muted">{g.items.length}</span>
              {g.unread.length > 0 && (
                <span className="rounded-full bg-primary-500 px-1.5 text-[10px] font-semibold leading-4 text-white">{g.unread.length} 未读</span>
              )}
            </button>
            {g.unread.length > 0 && (
              <button
                type="button"
                onClick={() => markGroup(g.unread)}
                disabled={markAll.isPending}
                className="shrink-0 rounded px-1.5 py-0.5 text-[11px] text-text-muted hover:bg-bg-hover hover:text-text-primary"
                title="这一组标为已读（只记在 momo 里，Slack 的未读不变）"
              >
                全部已读
              </button>
            )}
          </div>
          {g.shown.map(item => (
            <Row
              key={keyOf(item)}
              item={item}
              group={g.id}
              active={!!selection && selection.channelId === item.channel_id && selection.threadTs === item.thread_ts}
              manyChannels={manyChannels}
              agent={agents.get(item.type === 'thread' ? `slack:${item.channel_id}:${item.thread_ts}` : `slack:${item.channel_id}`)}
              onOpen={onOpen}
            />
          ))}
          {g.id === 'others' && !collapsed.has('others') && g.items.length > OTHERS_PREVIEW && (
            <button
              type="button"
              onClick={() => setOthersAll(v => !v)}
              className="w-full px-4 py-2 text-left text-xs text-primary-700 hover:bg-bg-hover"
            >
              {othersAll ? '收起' : `展开其余 ${g.items.length - OTHERS_PREVIEW} 条`}
            </button>
          )}
        </section>
      ))}
    </div>
  );
}

function ToolRow({ icon: Icon, label, hint, active, onClick }: {
  icon: typeof Sparkles; label: string; hint: string; active: boolean; onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-current={active || undefined}
      className={cn('flex w-full items-center gap-2.5 px-4 py-1.5 text-left', active ? 'bg-primary-50' : 'hover:bg-bg-hover')}
    >
      <Icon className={cn('h-4 w-4 shrink-0', active ? 'text-primary-700' : 'text-primary-500')} />
      <span className={cn('text-[14px]', active ? 'font-semibold text-primary-700' : 'font-medium text-text-primary')}>{label}</span>
      <span className="min-w-0 flex-1 truncate text-right text-xs text-text-muted">{hint}</span>
    </button>
  );
}

function Row({ item, group, active, manyChannels, agent, onOpen }: {
  item: SlackActivityItem;
  group: GroupId;
  active: boolean;
  manyChannels: boolean;
  agent: Parameters<typeof AgentBadge>[0]['run'];
  onOpen: (item: SlackActivityItem) => void;
}) {
  const isThread = item.type === 'thread';
  const who = isThread ? item.root?.user_name ?? '' : item.channel_name;
  // 「@我」组里各种类型混在一起，用小字说明是什么；其他组的标题已经说明了
  const tag = group === 'mentions' ? (isThread ? (item.reply_count ? 'thread' : '新帖') : '私信') : null;
  const channel = isThread && manyChannels ? `#${item.channel_name} · ` : '';
  return (
    <button
      type="button"
      onClick={() => onOpen(item)}
      aria-current={active || undefined}
      className={cn('block w-full px-3 py-2 text-left transition-colors', active ? 'bg-primary-50' : 'hover:bg-bg-hover')}
    >
      <div className="flex items-start gap-2.5">
        <Avatar name={who || '?'} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            {item.has_unreads && <span className="h-2 w-2 shrink-0 rounded-full bg-primary-500" aria-label="有新消息" />}
            <span className={cn('min-w-0 flex-1 truncate text-[14px] text-text-primary', item.has_unreads && 'font-semibold')}>
              {isThread ? firstLine(item.root, 80, true) : item.channel_name}
            </span>
            {tag && <span className="shrink-0 rounded bg-bg-hover px-1 text-[10px] leading-4 text-text-secondary">{tag}</span>}
            <span className="shrink-0 text-[11px] text-text-muted">{shortTime(item.latest_ts)}</span>
          </div>
          {isThread ? (
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="min-w-0 flex-1 truncate text-xs text-text-muted">
                {`${channel}${who}${item.reply_count ? ` 发起 · ${item.reply_count} 条回复` : ' 发帖 · 还没人回复'}`
                  + (item.participants && item.participants.length > 1 ? ` · ${item.participants.length} 人参与` : '')}
              </span>
              <AgentBadge run={agent} />
            </div>
          ) : null}
          {(item.last || !isThread) && (
            // 私信：第二行直接是最后一条消息（组标题已经说明是私信，不再重复写）
            <div className="mt-0.5 flex items-center gap-1.5">
              <span className="min-w-0 flex-1 truncate text-[13px] text-text-secondary">
                {!isThread && item.kind === 'mpim' && <span className="text-text-muted">群聊 · </span>}
                {item.last && <><span className="font-medium">{item.last.is_me ? '我' : item.last.user_name}：</span>{firstLine(item.last, 120)}</>}
              </span>
              {!isThread && <AgentBadge run={agent} />}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}
