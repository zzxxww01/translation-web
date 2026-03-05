import { apiClient } from '../../shared/api/client';
import type {
  Project,
  Section,
  CreateProjectDto,
  AnalysisResult,
  SectionAnalysis,
} from '../../shared/types';
import { ParagraphStatus } from '../../shared/constants';

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
    model?: string
  ) =>
    apiClient.post<{ translation: string }>(
      `/projects/${projectId}/sections/${sectionId}/paragraphs/${paragraphId}/translate`,
      { model: model || 'preview', instruction }
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
    model?: string
  ) =>
    apiClient.post<{ answer: string }>(
      `/projects/${projectId}/sections/${sectionId}/paragraphs/${paragraphId}/word-meaning`,
      { word, query, history, model: model || 'preview' }
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
    apiClient.put<{ id: string; translation?: string; status: ParagraphStatus }>(
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
  exportProject: (projectId: string, format: 'markdown' | 'html' = 'markdown') =>
    apiClient.post<{ content: string; path: string; format: string }>(
      `/projects/${projectId}/export`,
      undefined,
      { params: { format } }
    ),

  /**
   * 全文一键翻译 (SSE 流式)
   * 返回 EventSource 的 URL
   */
  getFullTranslateUrl: (projectId: string) =>
    `/api/projects/${projectId}/translate-stream`,
};
