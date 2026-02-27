/**
 * 一致性审查 API 封装
 */

import { apiClient } from '../../../shared/api/client';

export interface ConsistencyIssue {
  section_id: string;
  paragraph_index: number;
  issue_type: string;
  description: string;
  auto_fixable: boolean;
  fix_suggestion: string | null;
}

export interface TermStats {
  [term: string]: {
    total_count: number;
    translations: { [key: string]: number };
    is_consistent: boolean;
    preferred?: string;
  };
}

export interface Suggestion {
  issue_type: string;
  section_id: string;
  paragraph_index: number;
  description: string;
  action: string;
  auto_fixable: boolean;
  priority: number;
}

export interface ConsistencyReviewResult {
  is_consistent: boolean;
  style_score: number;
  issue_count: number;
  auto_fixable_count: number;
  manual_review_count: number;
  term_stats: TermStats;
  suggestions: Suggestion[];
  issues: ConsistencyIssue[];
}

/**
 * 一致性审查 API
 */
export const consistencyApi = {
  /**
   * 运行一致性审查
   */
  async runReview(projectId: string): Promise<ConsistencyReviewResult> {
    return apiClient.post<ConsistencyReviewResult>(
      `/projects/${projectId}/consistency-review`
    );
  },
};
