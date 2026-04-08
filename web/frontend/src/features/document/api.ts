import { apiClient } from '../../shared/api/client';
import type {
  Project,
  Section,
  CreateProjectDto,
  AnalysisResult,
  SectionAnalysis,
} from '../../shared/types';
import { ParagraphStatus, REQUEST_TIMEOUTS } from '../../shared/constants';

export interface WordMeaningMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface UpdateParagraphPayload {
  translation?: string;
  status?: ParagraphStatus;
  edit_source?: string;
  source_text?: string;
}

export interface ConsistencyIssue {
  section_id: string;
  paragraph_index: number;
  issue_type: string;
  description: string;
  auto_fixable: boolean;
  fix_suggestion?: string | null;
}

export interface LatestConsistencyReportResponse {
  project_id: string;
  report: {
    is_consistent: boolean;
    issue_count: number;
    total_issues: number;
    auto_fixable_count: number;
    manual_review_count: number;
    issues: ConsistencyIssue[];
  } | null;
  run_id?: string;
  status?: string;
  started_at?: string;
  finished_at?: string;
  artifacts_path?: string;
  source?: string;
  message?: string;
}

/**
 * 长文翻译 API
 */
export const documentApi = {
  /**
   * 获取所有项目
   */
  getProjects: () => apiClient.get<Project[]>('/projects'),

  /**
   * 获取项目详情
   */
  getProject: (id: string) => apiClient.get<Project>(`/projects/${id}`),

  /**
   * 创建新项目
   */
  createProject: (data: CreateProjectDto) =>
    apiClient.post<Project>('/projects', data),

  /**
   * 上传文件创建项目
   */
  uploadProject: (formData: FormData) =>
    apiClient.postForm<Project>('/projects/upload', formData),

  /**
   * 获取章节详情
   */
  getSection: (projectId: string, sectionId: string) =>
    apiClient.get<Section>(`/projects/${projectId}/sections/${sectionId}`),

  /**
   * 翻译段落
   */
  translateParagraph: (
    projectId: string,
    sectionId: string,
    paragraphId: string,
    instruction?: string,
    optionId?: string,
  ) =>
    apiClient.post<{ id: string; translation: string; status: ParagraphStatus; confirmed?: string | null }>(
      `/projects/${projectId}/sections/${sectionId}/paragraphs/${paragraphId}/translate`,
      { instruction, option_id: optionId },
      {
        timeout: REQUEST_TIMEOUTS.PARAGRAPH_TRANSLATE,
        retry: false,
      }
    ),

  /**
   * 查询选中词语含义（支持连续追问）
   */
  queryWordMeaning: (
    projectId: string,
    sectionId: string,
    paragraphId: string,
    word: string,
    query: string,
    history: WordMeaningMessage[] = [],
  ) =>
    apiClient.post<{ answer: string }>(
      `/projects/${projectId}/sections/${sectionId}/paragraphs/${paragraphId}/word-meaning`,
      { word, query, history },
      {
        timeout: REQUEST_TIMEOUTS.PARAGRAPH_WORD_MEANING,
        retry: false,
      }
    ),

  /**
   * 确认段落翻译
   */
  confirmParagraph: (
    projectId: string,
    sectionId: string,
    paragraphId: string,
    translation: string
  ) =>
    apiClient.put(
      `/projects/${projectId}/sections/${sectionId}/paragraphs/${paragraphId}/confirm`,
      { translation }
    ),

  updateParagraph: (
    projectId: string,
    sectionId: string,
    paragraphId: string,
    data: UpdateParagraphPayload
  ) =>
    apiClient.put<{ id: string; translation?: string; status: ParagraphStatus; confirmed?: string | null }>(
      `/projects/${projectId}/sections/${sectionId}/paragraphs/${paragraphId}`,
      data
    ),

  /**
   * 分析项目
   */
  analyzeProject: (projectId: string) =>
    apiClient.post<AnalysisResult>(`/projects/${projectId}/analyze`),

  /**
   * 分析章节
   */
  analyzeSection: (projectId: string, sectionId: string) =>
    apiClient.post<SectionAnalysis>(
      `/projects/${projectId}/sections/${sectionId}/analyze`
    ),

  /**
   * 批量翻译章节
   */
  batchTranslate: (projectId: string, sectionId: string) =>
    apiClient.post<{ translated_count: number }>(
      `/projects/${projectId}/sections/${sectionId}/translate_all`
    ),

  /**
   * 导出项目
   */
  exportProject: (projectId: string, format: 'en' | 'zh' = 'zh') =>
    apiClient.post<{ content: string; path: string; filename: string; format: string }>(
      `/projects/${projectId}/export`,
      undefined,
      { params: { format } }
    ),

  getLatestConsistencyReport: (projectId: string) =>
    apiClient.get<LatestConsistencyReportResponse>(
      `/projects/${projectId}/consistency-report`
    ),

  runConsistencyReview: (projectId: string) =>
    apiClient.post<{
      is_consistent: boolean;
      style_score: number;
      issue_count: number;
      auto_fixable_count: number;
      manual_review_count: number;
      issues: ConsistencyIssue[];
    }>(`/projects/${projectId}/consistency-review`),

  /**
   * 批量翻译指定段落
   */
  batchTranslateParagraphs: (
    projectId: string,
    sectionId: string,
    paragraphIds: string[],
    instruction?: string,
    optionId?: string,
  ) =>
    apiClient.post<{
      translations: Array<{
        id: string;
        translation: string;
        status: ParagraphStatus;
        confirmed?: string | null;
      }>;
      success_count: number;
      error_count: number;
      errors: Array<{ id: string; error: string }>;
    }>(
      `/projects/${projectId}/sections/${sectionId}/translate_batch`,
      {
        paragraph_ids: paragraphIds,
        instruction,
        option_id: optionId,
      },
      {
        timeout: REQUEST_TIMEOUTS.PARAGRAPH_BATCH_TRANSLATE,
        retry: false,
      }
    ),

  /**
   * 全文一键翻译 (SSE 流式)
   * 返回 EventSource 的 URL
   */
  getFullTranslateUrl: (projectId: string) =>
    `/api/projects/${projectId}/translate-stream`,
};
