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
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('glossaryApi term addressing', () => {
  // 含 "/" 的术语（W/m²、$/kW 等）拼进路径段会被 uvicorn 还原成真斜杠导致 404，
  // 因此原文必须走 query 参数
  it('addresses global terms by query parameter instead of a path segment', async () => {
    const put = vi.spyOn(apiClient, 'put').mockResolvedValueOnce({ message: 'ok', term: {} });
    const del = vi.spyOn(apiClient, 'delete').mockResolvedValueOnce({ message: 'ok', original: 'W/m²' });

    await glossaryApi.updateGlobalTerm('W/m²', { translation: '瓦每平方米' });
    await glossaryApi.deleteGlobalTerm('W/m²');

    expect(put).toHaveBeenCalledWith(
      '/glossary/term',
      { translation: '瓦每平方米' },
      { params: { original: 'W/m²' } }
    );
    expect(del).toHaveBeenCalledWith('/glossary/term', { params: { original: 'W/m²' } });
  });

  it('addresses project terms by query parameter instead of a path segment', async () => {
    const put = vi.spyOn(apiClient, 'put').mockResolvedValueOnce({ message: 'ok', term: {} });
    const del = vi.spyOn(apiClient, 'delete').mockResolvedValueOnce({ message: 'ok', original: '$/kW' });

    await glossaryApi.updateProjectTerm('project-1', '$/kW', { translation: '美元每千瓦' });
    await glossaryApi.deleteProjectTerm('project-1', '$/kW');

    expect(put).toHaveBeenCalledWith(
      '/projects/project-1/glossary/term',
      { translation: '美元每千瓦' },
      { params: { original: '$/kW' } }
    );
    expect(del).toHaveBeenCalledWith('/projects/project-1/glossary/term', {
      params: { original: '$/kW' },
    });
  });

  it('forwards the abort signal on read requests so stale project loads can be cancelled', async () => {
    const get = vi.spyOn(apiClient, 'get').mockResolvedValue({ version: 1, terms: [] });
    const controller = new AbortController();

    await glossaryApi.getGlobalGlossary({ signal: controller.signal });
    await glossaryApi.getProjectGlossary('project-1', { signal: controller.signal });

    expect(get).toHaveBeenNthCalledWith(1, '/glossary', { signal: controller.signal });
    expect(get).toHaveBeenNthCalledWith(2, '/projects/project-1/glossary', {
      signal: controller.signal,
    });
  });
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

  it('backs off polling for long-running terminology review jobs', async () => {
    vi.useFakeTimers();
    vi.spyOn(apiClient, 'post').mockResolvedValueOnce({
      ...succeededJob,
      status: 'queued',
      result: null,
    });
    vi.spyOn(apiClient, 'get')
      .mockResolvedValueOnce({ ...succeededJob, status: 'running', result: null })
      .mockResolvedValueOnce({ ...succeededJob, status: 'running', result: null })
      .mockResolvedValueOnce(succeededJob);
    const timeoutSpy = vi.spyOn(globalThis, 'setTimeout');

    const pending = glossaryApi.prepareTermReview('project-1', 'model-a');
    await vi.runAllTimersAsync();

    await expect(pending).resolves.toEqual(reviewPayload);
    expect(timeoutSpy.mock.calls.map(call => call[1])).toEqual([
      1000,
      1600,
      2560,
    ]);
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
