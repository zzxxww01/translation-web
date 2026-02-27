import { apiClient } from '../../shared/api/client';
import type {
  Task,
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
  // 获取任务列表
  getTasks: () => apiClient.get<Task[]>('/tasks'),

  // 任务管理
  saveTasks: (tasks: Task[]) =>
    apiClient.post('/tasks', tasks),

  // 文本翻译
  translateText: (data: TranslateTextDto) =>
    apiClient.post<TranslateTextResult>('/tools/translate', data),

  // 邮件回复
  generateEmailReply: (data: EmailReplyDto) =>
    apiClient.post<EmailReplyResult>('/tools/email-reply', data),

  // 时区转换
  convertTimezone: (data: TimezoneConvertDto) =>
    apiClient.post<TimezoneConvertResult>('/tools/timezone-convert', data),
};
