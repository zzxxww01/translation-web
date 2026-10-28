import { API_BASE } from '@/shared/constants';
import { apiClient, ApiErrorWrapper } from '@/shared/api/client';
import type { ChangesReport, Workbench } from './types';
import type { Harness } from '@/features/skills/harness';

export interface ExportResult {
  content: string;
  filename: string;
  is_incomplete?: boolean;
}

export const articlesApi = {
  workbench: (projectId: string) => apiClient.get<Workbench>(`/projects/${projectId}/workbench`),

  setReadingMark: (projectId: string, key: string | null) =>
    apiClient.put<{ ok: boolean; reading_mark: Workbench['reading_mark'] }>(
      `/projects/${projectId}/workbench/reading-mark`, { key }, { retry: false }),

  saveText: (projectId: string, body: { target: string; section_id: string; paragraph_id: string | null; text: string }) =>
    apiClient.put<{ ok: boolean }>(`/projects/${projectId}/workbench/text`, body, { retry: false }),

  changes: (projectId: string, target: string) =>
    apiClient.get<ChangesReport>(`/projects/${projectId}/workbench/changes`, { params: { target } }),

  createModelVariant: (projectId: string, model: string, label: string) =>
    apiClient.post<{ variant_id: string }>(`/projects/${projectId}/variants`, { kind: 'model', model, label }, { retry: false }),

  importClaude: (projectId: string, body: {
    run_id: string; zh_markdown: string; en_markdown: string; agent: Harness; model?: string | null; force?: boolean;
  }) =>
    apiClient.post<{ variant_id: string; aligned: number; unaligned: number }>(
      `/projects/${projectId}/variants/claude`, body, { retry: false, timeout: 120_000 }),

  setPrimary: (projectId: string, target: string) =>
    apiClient.put<{ ok: boolean; primary_target: string }>(
      `/projects/${projectId}/workbench/primary`, { target }, { retry: false }),

  setClaudeRun: (projectId: string, runId: string | null) =>
    apiClient.put<{ ok: boolean }>(`/projects/${projectId}/claude-run`, { run_id: runId }, { retry: false }),

  /**
   * 后台四步法；译本 2 传 model 并自动采用术语建议，不打断用户。
   * sectionIds：只重译这些章节（覆盖其中已有的译文）。补译不能用续译——续译要求提示词版本和上次一致，发版后会被拒。
   */
  startWorkflow: (projectId: string, options: { model?: string; autoAcceptTerms?: boolean; sectionIds?: string[] } = {}) =>
    apiClient.post<{ run_id: string }>(
      `/projects/${projectId}/translation-workflow`,
      {
        method: 'four-step',
        ...(options.model ? { model: options.model } : {}),
        ...(options.autoAcceptTerms ? { auto_accept_terms: true } : {}),
        ...(options.sectionIds?.length ? { retranslate_scope: 'section', retranslate_section_ids: options.sectionIds } : {}),
      },
      { retry: false },
    ),

  exportMarkdown: (projectId: string, format: 'zh' | 'en', allowQaOverride = false) =>
    apiClient.post<ExportResult>(`/projects/${projectId}/export`, undefined, {
      params: { format, ...(allowQaOverride ? { allow_qa_override: true } : {}) },
      retry: false,
      timeout: 120_000,
    }),

  deleteProject: (projectId: string) => apiClient.delete<{ message: string }>(`/projects/${projectId}`),

  /** 原文 HTML（交给 Claude 的 four-step-translate） */
  async sourceHtml(projectId: string): Promise<File> {
    const response = await fetch(`${API_BASE}/projects/${projectId}/source-html`);
    if (!response.ok) throw new ApiErrorWrapper('取不到原文 HTML', response.status);
    return new File([await response.blob()], `${projectId}.html`, { type: 'text/html' });
  },
};

/** 所有文章、所有版本的人工改动（机翻初稿 → 现在，JSONL），给以后优化用 */
export const HUMAN_EDITS_URL = `${API_BASE}/workbench/human-edits.jsonl`;

export function downloadText(filename: string, content: string): void {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/markdown;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
