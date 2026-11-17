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

export interface SlackThreadSummary {
  title: string;
  summary: string;
  /** 有人要我做事或在等我回复时的一句话，否则为空 */
  todo_for_me: string;
}

/** AI 速览里的一段：一个有未读的会话，或一个有新回复的 thread。 */
export interface SlackDigestSection {
  conversation_id: string;
  name: string;
  kind: 'thread' | ConversationKind;
  thread_ts: string | null;
  unread_count: number;
  mentions_me: boolean;
  latest_ts: string;
  summary?: string;
  items?: { text: string; ts: string | null }[];
  todo_for_me?: string;
  /** 这一段没能总结（模型失败），其余段不受影响 */
  error?: string;
}

export interface SlackSearchResult {
  channel_id: string;
  channel_name: string;
  kind: ConversationKind;
  /** 在 momo 的会话列表里（能直接打开）；否则只能去 Slack 看 */
  visible: boolean;
  thread_ts: string | null;
  message: SlackMessage;
}

export interface SlackSearchResponse {
  input: string;
  /** 实际拿去搜的英文关键词 */
  query: string;
  total: number;
  results: SlackSearchResult[];
}
