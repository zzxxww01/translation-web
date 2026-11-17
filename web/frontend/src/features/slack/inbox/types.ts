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
  has_unreads: boolean;
  mention_count: number;
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
