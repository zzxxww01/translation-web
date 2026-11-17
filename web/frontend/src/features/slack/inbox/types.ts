export type ConversationKind = 'channel' | 'private' | 'im' | 'mpim';

export interface SlackStatus {
  configured: boolean;
  ok: boolean;
  user?: string;
  user_id?: string;
  team?: string;
  url?: string;
  error_code?: string;
  error?: string;
}

export interface SlackConversation {
  id: string;
  kind: ConversationKind;
  name: string;
  latest_ts: string | null;
  latest_time: string;
  /** Slack 记录的我在这个会话里读到的位置；画「新消息」线用 */
  last_read: string | null;
  has_unreads: boolean;
  mention_count: number;
  thread_unreads: number;
  thread_mentions: number;
}

export interface SlackThreadBadge {
  has_unreads: boolean;
  mention_count: number;
}

export interface SlackConversationList {
  conversations: SlackConversation[];
  threads: SlackThreadBadge;
}

export interface SlackThread {
  channel_id: string;
  thread_ts: string;
  root: SlackMessage;
  reply_count: number;
  latest_reply: string | null;
  latest_time: string;
  last_read: string | null;
  /** 我参与（订阅）了这个 thread；只有参与的 thread Slack 才记已读 */
  following: boolean;
  has_unreads: boolean;
  mentions_me: boolean;
  latest_replies: SlackMessage[];
}

export type SlackSegment =
  | { type: 'text'; text: string }
  | { type: 'mention'; text: string }
  | { type: 'link'; text: string; url: string };

export interface SlackFile {
  id: string;
  name: string;
  mimetype: string;
  is_image: boolean;
  url: string;
}

export interface SlackAttachment {
  service_name: string;
  title: string;
  title_link: string;
  text: string;
}

export interface SlackMessage {
  ts: string;
  time: string;
  user_id: string;
  user_name: string;
  is_me: boolean;
  mentions_me: boolean;
  subtype: string | null;
  segments: SlackSegment[];
  text: string;
  thread_ts: string | null;
  reply_count: number;
  latest_reply: string | null;
  edited: boolean;
  files: SlackFile[];
  attachments: SlackAttachment[];
  reactions: { name: string; count: number }[];
  permalink: string;
}

export interface SlackMessagePage {
  messages: SlackMessage[];
  next_cursor: string | null;
}

export interface SlackReplies {
  messages: SlackMessage[];
  last_read: string | null;
}

/** 交给 skill agent 的上下文（后端 agent_context）。 */
export interface SlackAgentContext {
  source: string;
  kind: 'thread' | ConversationKind;
  title: string;
  latest_ts: string | null;
  markdown: string;
  history: { role: 'me' | 'them'; content: string }[];
}
