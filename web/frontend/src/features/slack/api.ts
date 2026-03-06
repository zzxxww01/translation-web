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
};
