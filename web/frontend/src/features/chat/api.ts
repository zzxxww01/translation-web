import { apiClient } from '@/shared/api/client';

export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatSource {
  title: string;
  url: string;
}

export interface ChatMessage extends ChatTurn {
  id: string;
  created_at?: number;
  /** 助手消息：用的模型别名 */
  model?: string;
  /** 助手消息：联网时引用的网页 */
  sources?: ChatSource[];
  /** 助手消息：如「这个模型不能联网，回答没有用搜索」 */
  note?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: number;
  updated_at: number;
  messages: ChatMessage[];
}

export interface ChatSessionSummary {
  id: string;
  title: string;
  count: number;
  updated_at: number;
}

export interface ReplyOptions {
  /** 不传就用默认（GPT-6.2 Sol） */
  model?: string;
  web_search: boolean;
}

// 联网回答常要 20~40 秒，失败后后端还会不联网再答一次：比一般的短文本请求多等一会儿
const REPLY_TIMEOUT = 240_000;

/** 会话存在服务器上（data/chat_sessions），换浏览器、换设备都在 */
export const chatApi = {
  list: () => apiClient.get<{ sessions: ChatSessionSummary[] }>('/tools/chat/sessions', { retry: false }),
  get: (id: string) => apiClient.get<ChatSession>(`/tools/chat/sessions/${id}`, { retry: false }),
  /** messages：导入以前存在浏览器里的那段对话 */
  create: (messages: ChatTurn[] = []) => apiClient.post<ChatSession>('/tools/chat/sessions', { messages }),
  rename: (id: string, title: string) => apiClient.patch<ChatSession>(`/tools/chat/sessions/${id}`, { title }),
  remove: (id: string) => apiClient.delete<{ deleted: boolean }>(`/tools/chat/sessions/${id}`),
  send: (id: string, content: string, options: ReplyOptions) =>
    apiClient.post<ChatSession>(`/tools/chat/sessions/${id}/messages`, { content, ...options }, { timeout: REPLY_TIMEOUT, retry: false }),
  /** 重新回答最后一个问题（出错后重试也用它） */
  reply: (id: string, options: ReplyOptions) =>
    apiClient.post<ChatSession>(`/tools/chat/sessions/${id}/reply`, options, { timeout: REPLY_TIMEOUT, retry: false }),
};
