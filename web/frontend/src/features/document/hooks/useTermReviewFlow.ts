import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import { glossaryApi } from '../../confirmation/api/glossaryApi';
import type { TermReviewDecision, TermReviewPayload } from '../../confirmation/types';
import { TranslationMethod } from '@/shared/constants';

interface PendingTranslationRequest {
  method: TranslationMethod;
  model?: string;
}

interface UseTermReviewFlowOptions {
  currentProjectId?: string;
  setView: (view: 'glossary' | 'term-review' | null) => void;
  runFullTranslate: (method: TranslationMethod, model?: string) => Promise<void>;
}

export function useTermReviewFlow({
  currentProjectId,
  setView,
  runFullTranslate,
}: UseTermReviewFlowOptions) {
  const [pendingTermReview, setPendingTermReview] = useState<TermReviewPayload | null>(null);
  const [pendingTranslationRequest, setPendingTranslationRequest] =
    useState<PendingTranslationRequest | null>(null);
  const [isSubmittingTermReview, setIsSubmittingTermReview] = useState(false);
  const [isPreparingFullTranslate, setIsPreparingFullTranslate] = useState(false);

  useEffect(() => {
    setPendingTermReview(null);
    setPendingTranslationRequest(null);
    setIsSubmittingTermReview(false);
    setIsPreparingFullTranslate(false);
  }, [currentProjectId]);

  const prepareTermReviewIfNeeded = useCallback(
    async (method: TranslationMethod = TranslationMethod.FOUR_STEP, model?: string) => {
      if (!currentProjectId) {
        return false;
      }

      try {
        const review = await glossaryApi.prepareTermReview(currentProjectId, model);
        if (review.review_required && review.total_candidates > 0) {
          setPendingTermReview(review);
          setPendingTranslationRequest({ method, model });
          setView('term-review');
          toast.info(`检测到 ${review.total_candidates} 个高优先级新术语，先确认再开始全文翻译`);
          return true;
        }
      } catch (error) {
        console.error('Failed to prepare term review:', error);
        toast.warning('术语预检失败，已跳过并直接开始全文翻译');
      }

      return false;
    },
    [currentProjectId, setView]
  );

  const submitTermReview = useCallback(
    async (decisions: TermReviewDecision[]) => {
      if (!currentProjectId || !pendingTranslationRequest) {
        return;
      }

      setIsSubmittingTermReview(true);
      try {
        await glossaryApi.submitTermReview(currentProjectId, decisions);
        await glossaryApi.getProjectGlossary(currentProjectId);
        setPendingTermReview(null);
        setView(null);
        toast.success('术语预检已保存，开始全文翻译');
        await runFullTranslate(
          pendingTranslationRequest.method,
          pendingTranslationRequest.model
        );
      } catch (error) {
        console.error('Failed to submit term review:', error);
        toast.error('保存术语预检失败');
      } finally {
        setIsSubmittingTermReview(false);
      }
    },
    [currentProjectId, pendingTranslationRequest, runFullTranslate, setView]
  );

  const cancelTermReview = useCallback(() => {
    setPendingTermReview(null);
    setPendingTranslationRequest(null);
    setView(null);
  }, [setView]);

  return {
    cancelTermReview,
    isPreparingFullTranslate,
    isSubmittingTermReview,
    pendingTermReview,
    prepareTermReviewIfNeeded,
    setIsPreparingFullTranslate,
    submitTermReview,
  };
}
