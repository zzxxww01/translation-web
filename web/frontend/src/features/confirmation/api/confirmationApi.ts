/**
 * 分段确认工作流 - API调用封装
 */

import { apiClient } from '../../../shared/api/client';
import type {
  ParagraphConfirmationResponse,
  ConfirmParagraphRequest,
  ConfirmParagraphResponse,
  UpdateTermsRequest,
  UpdateTermsResponse,
  ImportVersionRequest,
  ImportVersionResponse,
  ManualAlignRequest,
  TranslationStatus,
  ConfirmationProgress,
  ExportTranslationResponse,
} from '../types';

/**
 * 分段确认API
 */
export const confirmationApi = {
  /**
   * 启动全文翻译
   */
  async startTranslation(projectId: string): Promise<{ status: string }> {
    return apiClient.post<{ status: string }>(
      `/projects/${projectId}/translate-all`
    );
  },

  /**
   * 获取翻译状态
   */
  async getTranslationStatus(projectId: string): Promise<TranslationStatus> {
    return apiClient.get<TranslationStatus>(
      `/projects/${projectId}/translation-status`
    );
  },

  /**
   * 取消翻译
   */
  async cancelTranslation(projectId: string): Promise<{ status: string }> {
    return apiClient.post<{ status: string }>(
      `/projects/${projectId}/translation-cancel`
    );
  },

  /**
   * 获取段落的所有版本和确认状态
   */
  async getParagraphConfirmation(
    projectId: string,
    paragraphIndex: number
  ): Promise<ParagraphConfirmationResponse> {
    return apiClient.get<ParagraphConfirmationResponse>(
      `/projects/${projectId}/paragraph/${paragraphIndex}/confirmation`
    );
  },

  /**
   * 确认段落译文
   */
  async confirmParagraph(
    projectId: string,
    paragraphId: string,
    request: ConfirmParagraphRequest
  ): Promise<ConfirmParagraphResponse> {
    return apiClient.put<ConfirmParagraphResponse>(
      `/projects/${projectId}/paragraph/${paragraphId}/confirm`,
      request
    );
  },

  /**
   * 更新术语翻译
   */
  async updateTerms(
    projectId: string,
    changes: UpdateTermsRequest['changes']
  ): Promise<UpdateTermsResponse> {
    return apiClient.post<UpdateTermsResponse>(
      `/projects/${projectId}/term-update`,
      { changes }
    );
  },

  /**
   * 导入参考译文版本
   */
  async importReferenceVersion(
    projectId: string,
    request: ImportVersionRequest
  ): Promise<ImportVersionResponse> {
    return apiClient.post<ImportVersionResponse>(
      `/projects/${projectId}/import-version`,
      request
    );
  },

  /**
   * 手动对齐参考译文段落
   */
  async manualAlign(
    projectId: string,
    versionId: string,
    request: ManualAlignRequest
  ): Promise<{ version_id: string; aligned_count: number; unaligned_count: number }> {
    return apiClient.post<{ version_id: string; aligned_count: number; unaligned_count: number }>(
      `/projects/${projectId}/versions/${versionId}/align`,
      request
    );
  },

  /**
   * 跳过未对齐的参考段落
   */
  async skipUnaligned(
    projectId: string,
    versionId: string,
    refIndex: number
  ): Promise<{ version_id: string; unaligned_count: number }> {
    return apiClient.post<{ version_id: string; unaligned_count: number }>(
      `/projects/${projectId}/versions/${versionId}/skip`,
      null,
      { params: { ref_index: refIndex } }
    );
  },

  /**
   * 列出项目的所有参考译文版本
   */
  async listVersions(projectId: string): Promise<{
    versions: Array<{
      id: string;
      name: string;
      source_type: string;
      created_at: string;
      metadata: Record<string, unknown>;
    }>;
  }> {
    return apiClient.get<{
      versions: Array<{
        id: string;
        name: string;
        source_type: string;
        created_at: string;
        metadata: Record<string, unknown>;
      }>;
    }>(`/projects/${projectId}/versions`);
  },

  /**
   * 导出纯译文
   */
  async exportTranslation(
    projectId: string,
    includeSource: boolean = false
  ): Promise<ExportTranslationResponse> {
    return apiClient.post<ExportTranslationResponse>(
      `/projects/${projectId}/export-translation`,
      null,
      { params: { include_source: includeSource } }
    );
  },

  /**
   * 获取确认进度
   */
  async getConfirmationProgress(projectId: string): Promise<ConfirmationProgress> {
    return apiClient.get<ConfirmationProgress>(
      `/projects/${projectId}/confirmation-progress`
    );
  },

  /**
   * 下载导出的译文
   */
  downloadExportedTranslation(content: string, filename: string): void {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  /**
   * 重新翻译段落
   */
  async retranslateParagraph(
    projectId: string,
    paragraphId: string,
    instruction?: string,
    optionId?: string
  ): Promise<{
    version_id: string;
    paragraph_id: string;
    translation: string;
    instruction: string;
    created_at: string;
  }> {
    return apiClient.post<{
      version_id: string;
      paragraph_id: string;
      translation: string;
      instruction: string;
      created_at: string;
    }>(
      `/projects/${projectId}/paragraph/${paragraphId}/retranslate`,
      { instruction, option_id: optionId }
    );
  },

  /**
   * 获取重翻选项列表
   */
  async getRetranslateOptions(projectId: string): Promise<{
    options: Array<{
      id: string;
      label: string;
      description: string;
      instruction: string;
    }>;
  }> {
    return apiClient.get<{
      options: Array<{
        id: string;
        label: string;
        description: string;
        instruction: string;
      }>;
    }>(`/projects/${projectId}/retranslate-options`);
  },

  /**
   * 导出双语对照版
   */
  async exportBilingual(projectId: string): Promise<ExportTranslationResponse> {
    return apiClient.post<ExportTranslationResponse>(
      `/projects/${projectId}/export-bilingual`
    );
  },
};
