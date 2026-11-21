import { apiClient } from '@/shared/api/client';
import { API_BASE } from '@/shared/constants';
import type {
  SlackAgentContext, SlackConversationList, SlackMessagePage, SlackReplies, SlackStatus, SlackThread,
  SlackDigestSection, SlackThreadSummary, SlackActivityItem,
} from './types';

// Slack 完全只读：查询、导出、保存凭证；「标记已读」只写 momo 本地，不碰 Slack
export const slackInboxApi = {
  status: () => apiClient.get<SlackStatus>('/slack-inbox/status', { retry: false }),

  saveCredentials: (data: { token: string; cookie_d: string }) =>
    apiClient.put<SlackStatus>('/slack-inbox/credentials', data, { retry: false }),

  conversations: (refresh = false) =>
    apiClient.get<SlackConversationList>('/slack-inbox/conversations', {
      params: refresh ? { refresh: true } : undefined,
    }),

  messages: (channelId: string, cursor?: string) =>
    apiClient.get<SlackMessagePage>(`/slack-inbox/conversations/${channelId}/messages`, {
      params: cursor ? { limit: 50, cursor } : { limit: 50 },
    }),

  replies: (channelId: string, threadTs: string) =>
    apiClient.get<SlackReplies>(`/slack-inbox/conversations/${channelId}/replies/${threadTs}`),

  threads: () => apiClient.get<{ threads: SlackThread[] }>('/slack-inbox/threads'),

  activity: () => apiClient.get<{ items: SlackActivityItem[] }>('/slack-inbox/activity'),

  channelThreads: (channelId: string) =>
    apiClient.get<{ threads: SlackThread[] }>(`/slack-inbox/conversations/${channelId}/threads`),

  markRead: (channelId: string, ts: string) =>
    apiClient.post<{ ok: boolean; marked: boolean }>(`/slack-inbox/conversations/${channelId}/mark`, { ts }, { retry: false }),

  /** 全部标为已读：只记在 momo 本地 */
  markAllRead: () => apiClient.post<{ ok: boolean; marked: number }>('/slack-inbox/mark-all', {}, { retry: false }),

  markThreadRead: (channelId: string, threadTs: string, ts: string) =>
    apiClient.post<{ ok: boolean; marked: boolean }>(
      `/slack-inbox/conversations/${channelId}/threads/${threadTs}/mark`, { ts }, { retry: false }
    ),

  agentContext: (channelId: string, threadTs?: string) =>
    apiClient.get<SlackAgentContext>(`/slack-inbox/conversations/${channelId}/agent-context`, {
      params: threadTs ? { thread_ts: threadTs } : undefined,
    }),

  // 轻量 AI（后端按内容缓存）：逐条中文、thread 中文短标题、thread 摘要
  translate: (texts: string[]) =>
    apiClient.post<{ translations: (string | null)[] }>('/slack-inbox/ai/translate', { texts }, { retry: false, timeout: 180_000 }),


  threadSummary: (channelId: string, threadTs: string) =>
    apiClient.get<SlackThreadSummary>(`/slack-inbox/conversations/${channelId}/threads/${threadTs}/summary`, {
      retry: false, timeout: 180_000,
    }),

  digest: () =>
    apiClient.get<{ sections: SlackDigestSection[] }>('/slack-inbox/digest', { retry: false, timeout: 300_000 }),


  exportUrl: (channelId: string, format: 'md' | 'json') =>
    `${API_BASE}/slack-inbox/conversations/${channelId}/export?format=${format}`,
};
