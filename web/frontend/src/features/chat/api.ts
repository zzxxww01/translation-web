import { apiClient } from '@/shared/api/client';
import { REQUEST_TIMEOUTS } from '@/shared/constants';

export interface ChatTurn {
  role: 'user' | 'assistant';
  content: string;
}

export const chatApi = {
  // 每次带上整段对话，返回一条回复；model 不传就用默认（GPT-6.2 Sol）
  send: (data: { messages: ChatTurn[]; model?: string }) =>
    apiClient.post<{ reply: string }>('/tools/chat', data, {
      timeout: REQUEST_TIMEOUTS.SHORT_FORM_LLM,
      retry: false,
    }),
};
