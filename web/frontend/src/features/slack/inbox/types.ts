export type ConversationKind = 'channel' | 'private' | 'im' | 'mpim';

export interface SlackStatus {
  configured: boolean;
  ok: boolean;
  user?: string;
  user_id?: string;
  team?: string;
  /** 团队 ID（T 开头），拼 slack:// 链接用 */
  team_id?: string;
  url?: string;
  error_code?: string;
  error?: string;
  /** 服务器上的本地副本：已存消息数、库大小、上次后台同步时间（epoch 秒） */
  local?: { messages: number; conversations: number; db_bytes: number; last_sync: number | null };
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
  /** 卡片正文拆好的片段（旧缓存里可能没有） */
  segments?: SlackSegment[];
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

/** 「动态」列表的一行：一个频道 thread，或一个私信对话。 */
export interface SlackActivityItem {
  type: 'thread' | 'dm';
  channel_id: string;
  channel_name: string;
  /** 私信才有：im 一对一 / mpim 小群 */
  kind?: ConversationKind;
  thread_ts: string | null;
  /** thread 才有：根消息 */
  root?: SlackMessage;
  reply_count?: number;
  /** thread 里说过话的人（根消息作者在前） */
  participants?: string[];
  /** 最后一条回复 / 私信最后一条消息 */
  last: SlackMessage | null;
  latest_ts: string;
  latest_time: string;
  has_unreads: boolean;
  mentions_me: boolean;
  /** thread：我发起 / 回复过（订阅了）的，进「我参与的」筛选 */
  following?: boolean;
  /** thread 的翻译稿状态 */
  draft?: SlackDraftBadge | null;
}

export interface SlackThreadSummary {
  summary: string;
  /** 有人要我做事或在等我回复时的一句话，否则为空 */
  todo_for_me: string;
}

/** thread 的翻译稿状态（后端 slack_index），列表行和 thread 顶部显示「草稿 / 已完成」 */
export interface SlackDraftBadge {
  id: string;
  status: 'draft' | 'done';
  auto: boolean;
  seen: boolean;
  versions: number;
  no_post: boolean;
}

/** 我的待办里的一件事 */
export interface SlackTodo {
  kind: 'mention' | 'dm';
  channel_id: string;
  channel_name: string;
  conversation_kind: ConversationKind;
  thread_ts: string | null;
  title: string;
  from: string[];
  count: number;
  latest_ts: string;
  task: string;
  action: 'reply' | 'do' | 'read';
  mark: { channel_id: string; ts: string; thread_ts?: string };
  draft: SlackDraftBadge | null;
}

export interface SlackTodos {
  items: SlackTodo[];
  /** 只被 @用户组 / @here 群发提到的：不用处理 */
  fyi: SlackTodo[];
}

export interface SlackSettings {
  /** 有人在 thread 里直接 @我 时自动把帖子翻好 */
  auto_translate_mentions: boolean;
}

/** 私信回复面板：每次生成 / 调整记一组 */
export interface DmReplyVariant {
  version: string;
  english: string;
  chinese: string;
}

export interface DmReplyGroup {
  created_at: number;
  /** generate：按对方消息生成；compose：按「我想说」；adjust：一键调整；edit：改了某一版的意思 */
  kind: 'generate' | 'compose' | 'adjust' | 'edit';
  instruction?: string;
  understanding?: string;
  pending: boolean;
  replies: DmReplyVariant[];
  /** 生成时对方最新一条消息的 ts，用来判断有没有新消息 */
  based_on_ts: string | null;
}

export interface DmReplyState {
  groups: DmReplyGroup[];
  current: number;
}

/** 中栏单独打开的 thread（频道 + 根消息 ts） */
export interface OpenThread {
  channelId: string;
  threadTs: string;
}
