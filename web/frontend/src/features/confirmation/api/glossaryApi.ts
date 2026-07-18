/**
 * 术语库 API
 * 提供术语库的增删改查和匹配功能
 */

import { apiClient, ApiErrorWrapper } from '../../../shared/api/client';
import { REQUEST_TIMEOUTS } from '../../../shared/constants';
import type {
  GlossaryBatchAction,
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
  tags?: string[] | null;
  status?: 'active' | 'disabled' | string;
}

export interface BatchGlossaryRequest {
  originals: string[];
  action: GlossaryBatchAction;
  status?: 'active' | 'disabled' | string;
  strategy?: TranslationStrategy;
  tags?: string[] | null;
}

export interface TermReviewJob {
  job_id: string;
  project_id: string;
  model?: string | null;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  result?: TermReviewPayload | null;
  error?: string | null;
}

function hasTermReviewErrorCode(error: unknown, errorCode: string): boolean {
  if (!(error instanceof ApiErrorWrapper) || error.status !== 409) {
    return false;
  }
  const data = error.data;
  return (
    typeof data === 'object' &&
    data !== null &&
    'error_code' in data &&
    data.error_code === errorCode
  );
}

export function isTermReviewModelConflict(error: unknown): boolean {
  return hasTermReviewErrorCode(error, 'TERM_REVIEW_MODEL_CONFLICT');
}

export function isTermReviewArtifactConflict(error: unknown): boolean {
  return hasTermReviewErrorCode(error, 'TERM_REVIEW_ARTIFACT_CONFLICT');
}

function waitForPoll(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason ?? new DOMException('Request cancelled', 'AbortError'));
      return;
    }

    const timeoutId = setTimeout(() => {
      signal?.removeEventListener('abort', handleAbort);
      resolve();
    }, ms);
    const handleAbort = () => {
      clearTimeout(timeoutId);
      reject(signal?.reason ?? new DOMException('Request cancelled', 'AbortError'));
    };
    signal?.addEventListener('abort', handleAbort, { once: true });
  });
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
    const encodedOriginal = encodeURIComponent(original);
    return apiClient.put<{ message: string; term: GlossaryTerm }>(
      `/glossary/terms/${encodedOriginal}`,
      updates
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
    const encodedOriginal = encodeURIComponent(original);
    return apiClient.put<{ message: string; term: GlossaryTerm }>(
      `/projects/${projectId}/glossary/terms/${encodedOriginal}`,
      updates
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

  async batchUpdateGlobalGlossary(
    request: BatchGlossaryRequest
  ): Promise<{
    message: string;
    action: GlossaryBatchAction;
    matched_count: number;
    updated_count: number;
    terms: GlossaryTerm[];
    originals: string[];
  }> {
    return apiClient.post('/glossary/batch', request);
  },

  async batchUpdateProjectGlossary(
    projectId: string,
    request: BatchGlossaryRequest
  ): Promise<{
    message: string;
    action: GlossaryBatchAction;
    matched_count: number;
    updated_count: number;
    terms: GlossaryTerm[];
    originals: string[];
  }> {
    return apiClient.post(`/projects/${projectId}/glossary/batch`, request);
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

  async startTermReview(
    projectId: string,
    model?: string,
    signal?: AbortSignal
  ): Promise<TermReviewJob> {
    return apiClient.post<TermReviewJob>(
      `/projects/${projectId}/term-review/jobs`,
      {
        model,
      },
      {
        timeout: REQUEST_TIMEOUTS.DEFAULT,
        retry: false,
        signal,
      }
    );
  },

  async getTermReviewJob(
    projectId: string,
    jobId: string,
    signal?: AbortSignal
  ): Promise<TermReviewJob> {
    return apiClient.get<TermReviewJob>(
      `/projects/${projectId}/term-review/jobs/${encodeURIComponent(jobId)}`,
      {
        timeout: REQUEST_TIMEOUTS.DEFAULT,
        retry: false,
        signal,
      }
    );
  },

  async prepareTermReview(
    projectId: string,
    model?: string,
    signal?: AbortSignal
  ): Promise<TermReviewPayload> {
    let job = await this.startTermReview(projectId, model, signal);
    const deadline = Date.now() + REQUEST_TIMEOUTS.TERM_REVIEW_PREPARE;

    while (job.status === 'queued' || job.status === 'running') {
      if (Date.now() >= deadline) {
        throw new Error('Terminology review preparation timed out');
      }
      await waitForPoll(1000, signal);
      job = await this.getTermReviewJob(projectId, job.job_id, signal);
    }

    if (job.status === 'succeeded' && job.result) {
      return job.result;
    }
    throw new Error(job.error || 'Terminology review preparation failed');
  },

  async submitTermReview(
    projectId: string,
    artifactId: string,
    decisions: TermReviewDecision[],
    signal?: AbortSignal
  ): Promise<{
    project_id: string;
    applied_count: number;
    skipped_count: number;
    applied_terms: GlossaryTerm[];
    skipped_terms: string[];
  }> {
    return apiClient.post(
      `/projects/${projectId}/term-review/submit`,
      {
        artifact_id: artifactId,
        decisions,
      },
      {
        retry: false,
        signal,
      }
    );
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

  /**
   * 检查术语是否与项目/全局术语库存在冲突
   */
  async checkTermConflict(
    projectId: string,
    original: string,
    translation?: string | null
  ): Promise<{
    has_conflict: boolean;
    conflicts: Array<{
      scope: string;
      existing_translation: string | null;
      existing_strategy: string;
      existing_note: string | null;
    }>;
  }> {
    return apiClient.post(`/projects/${projectId}/glossary/check-conflict`, {
      original,
      translation,
    });
  },
};
