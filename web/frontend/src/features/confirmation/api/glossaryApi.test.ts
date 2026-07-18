import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiErrorWrapper, apiClient } from '../../../shared/api/client';
import type { TermReviewDecision, TermReviewPayload } from '../types';
import {
  glossaryApi,
  isTermReviewArtifactConflict,
  isTermReviewModelConflict,
  type TermReviewJob,
} from './glossaryApi';

const reviewPayload: TermReviewPayload = {
  artifact_id: 'artifact-1',
  project_id: 'project-1',
  project_title: 'Project',
  review_required: true,
  generated_at: '2026-07-19T00:00:00',
  total_candidates: 1,
  sections: [],
};

const succeededJob: TermReviewJob = {
  job_id: 'artifact-1',
  project_id: 'project-1',
  model: 'model-a',
  status: 'succeeded',
  created_at: '2026-07-19T00:00:00',
  updated_at: '2026-07-19T00:00:01',
  result: reviewPayload,
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe('glossaryApi terminology review identity', () => {
  it('preserves the prepared artifact identity from the completed job', async () => {
    vi.spyOn(apiClient, 'post').mockResolvedValueOnce(succeededJob);

    const result = await glossaryApi.prepareTermReview(
      'project-1',
      'model-a'
    );

    expect(result).toEqual(reviewPayload);
    expect(result.artifact_id).toBe('artifact-1');
  });

  it('submits decisions with the identity of the displayed artifact', async () => {
    const decisions: TermReviewDecision[] = [
      {
        term: 'API',
        action: 'accept',
        translation: '应用程序编程接口',
      },
    ];
    const response = {
      project_id: 'project-1',
      applied_count: 1,
      skipped_count: 0,
      applied_terms: [],
      skipped_terms: [],
    };
    const post = vi.spyOn(apiClient, 'post').mockResolvedValueOnce(response);

    await glossaryApi.submitTermReview(
      'project-1',
      'artifact-from-this-page',
      decisions
    );

    expect(post).toHaveBeenCalledWith(
      '/projects/project-1/term-review/submit',
      {
        artifact_id: 'artifact-from-this-page',
        decisions,
      },
      {
        retry: false,
        signal: undefined,
      }
    );
  });

  it('identifies only the explicit active-model conflict as blocking', () => {
    const modelConflict = new ApiErrorWrapper(
      'A terminology review is already running with another model.',
      409,
      {
        detail: 'A terminology review is already running with another model.',
        error_code: 'TERM_REVIEW_MODEL_CONFLICT',
      }
    );
    const artifactConflict = new ApiErrorWrapper(
      'The terminology review artifact changed.',
      409,
      {
        detail: 'The terminology review artifact changed.',
        error_code: 'TERM_REVIEW_ARTIFACT_CONFLICT',
      }
    );

    expect(isTermReviewModelConflict(modelConflict)).toBe(true);
    expect(isTermReviewModelConflict(artifactConflict)).toBe(false);
    expect(isTermReviewModelConflict(new Error('network error'))).toBe(false);
    expect(isTermReviewArtifactConflict(artifactConflict)).toBe(true);
    expect(isTermReviewArtifactConflict(modelConflict)).toBe(false);
  });
});
