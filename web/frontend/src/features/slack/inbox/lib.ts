import type { ConversationKind, SlackMessage } from './types';

// 常见的 Slack 表情简码；没收录的原样显示 :name:
const EMOJI: Record<string, string> = {
  rotating_light: '🚨', fire: '🔥', eyes: '👀', heart: '❤️', joy: '😂', rocket: '🚀',
  pray: '🙏', clap: '👏', tada: '🎉', thumbsup: '👍', '+1': '👍', '-1': '👎', point_up: '☝️',
  saluting_face: '🫡', white_check_mark: '✅', heavy_check_mark: '✔️', x: '❌', warning: '⚠️',
  100: '💯', thinking_face: '🤔', raised_hands: '🙌', muscle: '💪', sob: '😭', smile: '😄',
  slightly_smiling_face: '🙂', laughing: '😆', skull: '💀', chart_with_upwards_trend: '📈',
  chart_with_downwards_trend: '📉', memo: '📝', link: '🔗', point_down: '👇', point_right: '👉',
};

const EMOJI_RE = /:([a-z0-9_+-]+):/g;

/**
 * 直接在 Slack App（桌面 / 手机）里打开这个频道或私信。官方深链只能定位到会话，定位不到某条消息或 thread；
 * 精确到消息用 https 的 permalink。没有团队 ID 时返回 null（不显示按钮）。
 */
export function slackAppLink(teamId: string | undefined, channelId: string): string | null {
  return teamId ? `slack://channel?team=${encodeURIComponent(teamId)}&id=${encodeURIComponent(channelId)}` : null;
}

export function emojify(text: string): string {
  return text.replace(EMOJI_RE, (match, name: string) => EMOJI[name.replace(/::skin-tone-\d/, '')] ?? match);
}

export function emojiFor(name: string): string {
  return EMOJI[name.split('::')[0]] ?? `:${name}:`;
}

/** 当标题用的文字：去掉开头的「@用户组」（帖子常这样开头，标题里没信息量）；点名某人的提及保留 */
export function stripLeadingMentions(text: string): string {
  const stripped = text.replace(/^(\s*@用户组\s*)+/, '').trim();
  return stripped || text.trim();
}

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
}

export function dayLabel(ts: string, now = new Date()): string {
  const d = new Date(parseFloat(ts) * 1000);
  const diff = Math.round((startOfDay(now) - startOfDay(d)) / 86_400_000);
  if (diff === 0) return '今天';
  if (diff === 1) return '昨天';
  const label = `${d.getMonth() + 1}月${d.getDate()}日 ${WEEKDAYS[d.getDay()]}`;
  return d.getFullYear() === now.getFullYear() ? label : `${d.getFullYear()}年${label}`;
}

export function clockTime(ts: string): string {
  const d = new Date(parseFloat(ts) * 1000);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
}

export interface StreamItem {
  message: SlackMessage;
  /** 这一天的第一条：上方画日期分隔 */
  day: string | null;
  /** 第一条未读：上方画「新消息」线 */
  firstUnread: boolean;
  /** 同一个人 5 分钟内连发的后续消息不再重复头像和名字 */
  compact: boolean;
}

const GROUP_GAP_S = 5 * 60;

/** 消息按时间正序排好后，算出日期分隔、新消息线和连发合并。 */
export function buildStream(messages: SlackMessage[], lastRead: string | null, now = new Date()): StreamItem[] {
  let prev: SlackMessage | null = null;
  let prevDay = '';
  let unreadMarked = false;
  return messages.map(message => {
    const day = dayLabel(message.ts, now);
    const newDay = day !== prevDay;
    const firstUnread = !unreadMarked && !!lastRead && !message.is_me && parseFloat(message.ts) > parseFloat(lastRead);
    if (firstUnread) unreadMarked = true;
    const compact = !!prev && !newDay && !firstUnread
      && prev.user_id === message.user_id && prev.user_name === message.user_name
      && prev.reply_count === 0
      && parseFloat(message.ts) - parseFloat(prev.ts) < GROUP_GAP_S;
    prev = message;
    prevDay = day;
    return { message, day: newDay ? day : null, firstUnread, compact };
  });
}

/** 消息流里最新一条的 ts（用来推进已读位置）。 */
export function newestTs(messages: { ts: string }[]): string | null {
  let best: string | null = null;
  for (const m of messages) if (!best || parseFloat(m.ts) > parseFloat(best)) best = m.ts;
  return best;
}

/** 会话类型的中文说明，放在会话标题下面。 */
export function kindLabel(kind: ConversationKind): string {
  switch (kind) {
    case 'channel': return '频道 · 公开，所有成员都能看到';
    case 'private': return '私有频道 · 只有被邀请的人能看到';
    case 'im': return '私信 · 你和对方一对一';
    case 'mpim': return '群聊私信 · 几个人的小群';
  }
}

