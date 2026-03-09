/**
 * 术语库 API
 * 提供术语库的增删改查和匹配功能
 */

import { apiClient } from '../../../shared/api/client';
import type {
  GlossaryRecommendation,
  GlossaryTerm,
  TermReviewDecision,
  TermReviewPayload,
  TranslationStrategy,
} from '../types';

/**
 * 术语表
 */
export interface Glossary {
  version: number;
  terms: GlossaryTerm[];
}

/**
 * 术语匹配结果
 */
export interface TermMatch {
  original: string;
  translation?: string | null;
  strategy: TranslationStrategy;
  note?: string | null;
  score: number;
  match_type: 'exact' | 'partial';
}

/**
 * 匹配术语响应
 */
export interface MatchTermsResponse {
  total_terms: number;
  matched_count: number;
  matches: TermMatch[];
}

/**
 * 添加术语请求
 */
export interface AddTermRequest {
  original: string;
  translation?: string | null;
  strategy?: TranslationStrategy;
  note?: string | null;
  status?: 'active' | 'disabled' | string;
}

/**
 * 术语库 API
 */
export const glossaryApi = {
  /**
   * 获取项目术语表
   */
  async getProjectGlossary(projectId: string): Promise<Glossary> {
    return apiClient.get<Glossary>(
      `/projects/${projectId}/glossary`
    );
  },

  /**
   * 获取全局术语表
   */
  async getGlobalGlossary(): Promise<Glossary> {
    return apiClient.get<Glossary>('/glossary');
  },

  /**
   * 添加项目术语
   */
  async addProjectTerm(
    projectId: string,
    request: AddTermRequest
  ): Promise<{ message: string; term: GlossaryTerm }> {
    return apiClient.put<{ message: string; term: GlossaryTerm }>(
      `/projects/${projectId}/glossary`,
      request
    );
  },

  /**
   * 添加全局术语
   */
  async addGlobalTerm(
    request: AddTermRequest
  ): Promise<{ message: string; term: GlossaryTerm }> {
    return apiClient.post<{ message: string; term: GlossaryTerm }>(
      '/glossary',
      request
    );
  },

  /**
   * 更新全局术语
   */
  async updateGlobalTerm(
    original: string,
    updates: Partial<AddTermRequest>
  ): Promise<{ message: string; term: GlossaryTerm }> {
    const params = new URLSearchParams();

    if (updates.translation !== undefined && updates.translation !== null) {
      params.append('translation', updates.translation);
    }
    if (updates.strategy !== undefined) {
      params.append('strategy', updates.strategy);
    }
    if (updates.note !== undefined && updates.note !== null) {
      params.append('note', updates.note);
    }
    if (updates.status !== undefined && updates.status !== null) {
      params.append('status', updates.status);
    }

    const encodedOriginal = encodeURIComponent(original);

    return apiClient.put<{ message: string; term: GlossaryTerm }>(
      `/glossary/terms/${encodedOriginal}?${params.toString()}`
    );
  },

  /**
   * 删除全局术语
   */
  async deleteGlobalTerm(
    original: string
  ): Promise<{ message: string; original: string }> {
    const encodedOriginal = encodeURIComponent(original);

    return apiClient.delete<{ message: string; original: string }>(
      `/glossary/terms/${encodedOriginal}`
    );
  },

  /**
   * 更新项目术语
   */
  async updateProjectTerm(
    projectId: string,
    original: string,
    updates: Partial<AddTermRequest>
  ): Promise<{ message: string; term: GlossaryTerm }> {
    const params = new URLSearchParams();

    if (updates.translation !== undefined && updates.translation !== null) {
      params.append('translation', updates.translation);
    }
    if (updates.strategy !== undefined) {
      params.append('strategy', updates.strategy);
    }
    if (updates.note !== undefined && updates.note !== null) {
      params.append('note', updates.note);
    }
    if (updates.status !== undefined && updates.status !== null) {
      params.append('status', updates.status);
    }

    const encodedOriginal = encodeURIComponent(original);

    return apiClient.put<{ message: string; term: GlossaryTerm }>(
      `/projects/${projectId}/glossary/terms/${encodedOriginal}?${params.toString()}`
    );
  },

  /**
   * 删除项目术语
   */
  async deleteProjectTerm(
    projectId: string,
    original: string
  ): Promise<{ message: string; original: string }> {
    const encodedOriginal = encodeURIComponent(original);

    return apiClient.delete<{ message: string; original: string }>(
      `/projects/${projectId}/glossary/terms/${encodedOriginal}`
    );
  },

  /**
   * 匹配段落相关术语
   */
  async matchParagraphTerms(
    projectId: string,
    paragraph: string,
    maxTerms: number = 20
  ): Promise<MatchTermsResponse> {
    return apiClient.post<MatchTermsResponse>(
      `/projects/${projectId}/glossary/match`,
      { paragraph, max_terms: maxTerms }
    );
  },

  async prepareTermReview(projectId: string): Promise<TermReviewPayload> {
    return apiClient.post<TermReviewPayload>(`/projects/${projectId}/term-review/prepare`);
  },

  async submitTermReview(
    projectId: string,
    decisions: TermReviewDecision[]
  ): Promise<{
    project_id: string;
    applied_count: number;
    skipped_count: number;
    applied_terms: GlossaryTerm[];
    skipped_terms: string[];
  }> {
    return apiClient.post(`/projects/${projectId}/term-review/submit`, {
      decisions,
    });
  },

  async getProjectRecommendations(
    projectId: string
  ): Promise<{ project_id: string; recommendations: GlossaryRecommendation[] }> {
    return apiClient.get(`/projects/${projectId}/glossary/recommendations`);
  },

  async promoteProjectTerm(
    projectId: string,
    original: string
  ): Promise<{ message: string; term: GlossaryTerm }> {
    const encodedOriginal = encodeURIComponent(original);
    return apiClient.post(`/projects/${projectId}/glossary/terms/${encodedOriginal}/promote`);
  },
};
