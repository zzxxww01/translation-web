import { apiClient } from '../../shared/api/client';
import { REQUEST_TIMEOUTS } from '../../shared/constants';
import type {
  ComposeDto,
  ComposeResult,
  ProcessMessageDto,
  ProcessResult,
} from '../../shared/types';

export const slackApi = {
  processMessage: (data: ProcessMessageDto) =>
    apiClient.post<ProcessResult>('/slack/process', data, {
      timeout: REQUEST_TIMEOUTS.SHORT_FORM_LLM,
      retry: false,
    }),

  composeReply: (data: ComposeDto) =>
    apiClient.post<ComposeResult>('/slack/compose', data, {
      timeout: REQUEST_TIMEOUTS.SHORT_FORM_LLM,
      retry: false,
    }),

  refine: (data: {
    context_type: 'incoming' | 'draft';
    original_result: string;
    adjustment_instruction: string;
    conversation_history: Array<{ role: string; content: string }>;
  }) =>
    apiClient.post<{ refined_result: string }>('/slack/refine', data, {
      timeout: REQUEST_TIMEOUTS.SHORT_FORM_LLM,
      retry: false,
    }),
};
