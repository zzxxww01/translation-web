/**
 * 一致性审查 Hook
 */

import { useState, useCallback } from 'react';
import { consistencyApi, ConsistencyReviewResult } from '../api/consistencyApi';

export function useConsistencyReview(projectId: string) {
  const [result, setResult] = useState<ConsistencyReviewResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runReview = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const reviewResult = await consistencyApi.runReview(projectId);
      setResult(reviewResult);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to run consistency review';
      setError(message);
      console.error('Consistency review error:', err);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  const clearResult = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    result,
    isLoading,
    error,
    runReview,
    clearResult,
  };
}
