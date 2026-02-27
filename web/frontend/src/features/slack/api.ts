import { apiClient } from '../../shared/api/client';
import type {
  Conversation,
  CreateConversationDto,
  AddMessageDto,
  ProcessMessageDto,
  ProcessResult,
  ComposeDto,
  ComposeResult,
} from '../../shared/types';

// 新增智能优化相关类型
export interface OptimizeRequest {
  content: string;
  target_language: 'en' | 'cn';
  context_type: 'translation' | 'grammar' | 'tone' | 'formality';
  conversation_id?: string;
  original_text?: string;
}

export interface OptimizeResponse {
  optimized_text: string;
  improvements: string[];
  confidence: number;
}

export interface SyncRequest {
  chinese_reply: string;
  conversation_id?: string;
}

export interface SyncResponse {
  english_reply: string;
}

/**
 * Slack 回复 API
 */
export const slackApi = {
  /**
   * 获取对话列表
   */
  getConversations: () => apiClient.get<Conversation[]>('/conversations'),

  /**
   * 获取对话详情（包含历史消息）
   */
  getConversation: (id: string) => apiClient.get<Conversation>(`/conversations/${id}`),

  /**
   * 创建对话
   */
  createConversation: (data: CreateConversationDto) =>
    apiClient.post<Conversation>('/conversations', data),

  /**
   * 更新对话（重命名/置顶）
   */
  updateConversation: (id: string, data: { name?: string; is_pinned?: boolean }) =>
    apiClient.put<Conversation>(`/conversations/${id}`, data),

  /**
   * 删除对话
   */
  deleteConversation: (id: string) =>
    apiClient.delete(`/conversations/${id}`),

  /**
   * 添加消息
   */
  addMessage: (conversationId: string, data: AddMessageDto) =>
    apiClient.post(`/conversations/${conversationId}/messages`, data),

  /**
   * 切换消息角色
   */
  toggleMessageRole: (conversationId: string, messageIndex: number, role: 'me' | 'them') =>
    apiClient.put(`/conversations/${conversationId}/messages/${messageIndex}`, { role }),

  /**
   * 处理消息（翻译/生成回复）
   */
  processMessage: (data: ProcessMessageDto) =>
    apiClient.post<ProcessResult>('/slack/process', data),

  /**
   * AI 润色回复
   */
  composeReply: (data: ComposeDto) =>
    apiClient.post<ComposeResult>('/slack/compose', data),

  /**
   * 智能文本优化
   */
  optimizeText: (data: OptimizeRequest) =>
    apiClient.post<OptimizeResponse>('/slack/optimize', data),

  /**
   * 同步中文回复到英文
   */
  syncReply: (data: SyncRequest) =>
    apiClient.post<SyncResponse>('/slack/sync', data),
};
