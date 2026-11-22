import { apiClient } from '../../shared/api/client';
import { REQUEST_TIMEOUTS } from '../../shared/constants';
import type {
  TranslateTextDto,
  TranslateTextResult,
  EmailReplyDto,
  EmailReplyResult,
  TimezoneConvertDto,
  TimezoneConvertResult,
} from '../../shared/types';

/**
 * 工具箱 API
 */
export const toolsApi = {
  // 文本翻译
  translateText: (data: TranslateTextDto) =>
    apiClient.post<TranslateTextResult>('/tools/translate', data, {
      timeout: REQUEST_TIMEOUTS.SHORT_FORM_LLM,
      retry: false,
    }),

  // 邮件回复
  generateEmailReply: (data: EmailReplyDto) =>
    apiClient.post<EmailReplyResult>('/tools/email-reply', data, {
      timeout: REQUEST_TIMEOUTS.SHORT_FORM_LLM,
      retry: false,
    }),

  // 时区转换
  convertTimezone: (data: TimezoneConvertDto) =>
    apiClient.post<TimezoneConvertResult>('/tools/timezone-convert', data),
};
