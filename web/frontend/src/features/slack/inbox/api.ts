import { apiClient } from '@/shared/api/client';
import { API_BASE } from '@/shared/constants';
import type { SlackConversation, SlackMessagePage, SlackStatus } from './types';

// 后端只读：这里只有查询、导出和保存凭证，没有任何往 Slack 发送的接口
export const slackInboxApi = {
  status: () => apiClient.get<SlackStatus>('/slack-inbox/status', { retry: false }),

  saveCredentials: (data: { token: string; cookie_d: string }) =>
    apiClient.put<SlackStatus>('/slack-inbox/credentials', data, { retry: false }),

  conversations: (refresh = false) =>
    apiClient.get<{ conversations: SlackConversation[] }>('/slack-inbox/conversations', {
      params: refresh ? { refresh: true } : undefined,
    }),

  messages: (channelId: string, cursor?: string) =>
    apiClient.get<SlackMessagePage>(`/slack-inbox/conversations/${channelId}/messages`, {
      params: cursor ? { limit: 50, cursor } : { limit: 50 },
    }),

  replies: (channelId: string, threadTs: string) =>
    apiClient.get<SlackMessagePage>(`/slack-inbox/conversations/${channelId}/replies/${threadTs}`),

  exportUrl: (channelId: string, format: 'md' | 'json') =>
    `${API_BASE}/slack-inbox/conversations/${channelId}/export?format=${format}`,
};
