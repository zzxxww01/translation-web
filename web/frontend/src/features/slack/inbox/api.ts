import { apiClient } from '@/shared/api/client';
import { API_BASE } from '@/shared/constants';
import type { SlackConversationList, SlackMessagePage, SlackReplies, SlackStatus, SlackThread } from './types';

// 后端只读：查询、导出、保存凭证，加上推进我自己的已读位置；没有任何往 Slack 发送的接口
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

  channelThreads: (channelId: string) =>
    apiClient.get<{ threads: SlackThread[] }>(`/slack-inbox/conversations/${channelId}/threads`),

  markRead: (channelId: string, ts: string) =>
    apiClient.post<{ ok: boolean; marked: boolean }>(`/slack-inbox/conversations/${channelId}/mark`, { ts }, { retry: false }),

  markThreadRead: (channelId: string, threadTs: string, ts: string) =>
    apiClient.post<{ ok: boolean; marked: boolean }>(
      `/slack-inbox/conversations/${channelId}/threads/${threadTs}/mark`, { ts }, { retry: false }
    ),

  exportUrl: (channelId: string, format: 'md' | 'json') =>
    `${API_BASE}/slack-inbox/conversations/${channelId}/export?format=${format}`,
};
