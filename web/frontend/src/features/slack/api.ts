import { apiClient } from '../../shared/api/client';
import type {
  ComposeDto,
  ComposeResult,
  ProcessMessageDto,
  ProcessResult,
} from '../../shared/types';

export const slackApi = {
  processMessage: (data: ProcessMessageDto) =>
    apiClient.post<ProcessResult>('/slack/process', data),

  composeReply: (data: ComposeDto) =>
    apiClient.post<ComposeResult>('/slack/compose', data),

  refine: (data: {
    context_type: 'incoming' | 'draft';
    original_result: string;
    adjustment_instruction: string;
    conversation_history: Array<{ role: string; content: string }>;
  }) =>
    apiClient.post<{ refined_result: string }>('/slack/refine', data),
};
