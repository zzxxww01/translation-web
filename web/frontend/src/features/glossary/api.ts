import { apiClient } from '@/shared/api/client';

export interface TranslationRule {
  index: number;
  text: string;
}

export interface TranslationRulesResponse {
  rules: TranslationRule[];
  total: number;
}

export const translationRulesApi = {
  getAll: () =>
    apiClient.get<TranslationRulesResponse>('/projects/translation-rules'),

  add: (text: string) =>
    apiClient.post<{ added: true; text: string }>('/projects/translation-rules', { text }),

  delete: (index: number) =>
    apiClient.delete<{ deleted: true; index: number }>(
      `/projects/translation-rules/${index}`
    ),
};
