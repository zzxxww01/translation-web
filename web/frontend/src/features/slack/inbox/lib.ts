import type { ConversationKind, SlackConversation } from './types';

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

export function emojify(text: string): string {
  return text.replace(EMOJI_RE, (match, name: string) => EMOJI[name.replace(/::skin-tone-\d/, '')] ?? match);
}

export function emojiFor(name: string): string {
  return EMOJI[name.split('::')[0]] ?? `:${name}:`;
}

export type InboxScope = 'channels' | 'dms';

const SCOPE_KINDS: Record<InboxScope, ConversationKind[]> = {
  channels: ['channel', 'private'],
  dms: ['im', 'mpim'],
};

export function filterConversations(conversations: SlackConversation[], scope: InboxScope) {
  return conversations.filter(c => SCOPE_KINDS[scope].includes(c.kind));
}

export type SlackView = InboxScope | 'reply';

export const SLACK_VIEWS: { id: SlackView; label: string }[] = [
  { id: 'channels', label: '频道' },
  { id: 'dms', label: '私信' },
  { id: 'reply', label: '回复工作台' },
];

export function parseSlackView(value: string | null): SlackView {
  return SLACK_VIEWS.some(v => v.id === value) ? (value as SlackView) : 'channels';
}
