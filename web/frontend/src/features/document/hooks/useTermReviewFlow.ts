import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  glossaryApi,
  isTermReviewArtifactConflict,
  isTermReviewModelConflict,
} from '../../confirmation/api/glossaryApi';
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
  const currentProjectIdRef = useRef(currentProjectId);
  const operationGenerationRef = useRef(0);
  const prepareControllerRef = useRef<AbortController | null>(null);
  const submitControllerRef = useRef<AbortController | null>(null);
  currentProjectIdRef.current = currentProjectId;

  useEffect(() => {
    operationGenerationRef.current += 1;
    prepareControllerRef.current?.abort();
    submitControllerRef.current?.abort();
    prepareControllerRef.current = null;
    submitControllerRef.current = null;
    setPendingTermReview(null);
    setPendingTranslationRequest(null);
    setIsSubmittingTermReview(false);
    setIsPreparingFullTranslate(false);
  }, [currentProjectId]);

  useEffect(
    () => () => {
      operationGenerationRef.current += 1;
      prepareControllerRef.current?.abort();
      submitControllerRef.current?.abort();
    },
    []
  );

  const prepareTermReviewIfNeeded = useCallback(
    async (method: TranslationMethod = TranslationMethod.FOUR_STEP, model?: string) => {
      if (!currentProjectId) {
        return false;
      }

      prepareControllerRef.current?.abort();
      const controller = new AbortController();
      prepareControllerRef.current = controller;
      const projectId = currentProjectId;
      const generation = ++operationGenerationRef.current;
      setIsPreparingFullTranslate(true);
      setPendingTermReview(null);
      setPendingTranslationRequest(null);

      try {
        const review = await glossaryApi.prepareTermReview(
          projectId,
          model,
          controller.signal
        );
        if (
          controller.signal.aborted ||
          operationGenerationRef.current !== generation ||
          currentProjectIdRef.current !== projectId
        ) {
          return true;
        }
        if (review.review_required && review.total_candidates > 0) {
          setPendingTermReview(review);
          setPendingTranslationRequest({ method, model });
          setView('term-review');
          toast.info(`检测到 ${review.total_candidates} 个高优先级新术语，先确认再开始全文翻译`);
          return true;
        }
      } catch (error) {
        if (
          controller.signal.aborted ||
          operationGenerationRef.current !== generation ||
          currentProjectIdRef.current !== projectId
        ) {
          return true;
        }
        console.error('Failed to prepare term review:', error);
        if (isTermReviewModelConflict(error)) {
          toast.error('该项目正在使用另一模型进行术语预检，请稍后重试');
          return true;
        }
        toast.warning('术语预检失败，已跳过并直接开始全文翻译');
      } finally {
        if (prepareControllerRef.current === controller) {
          prepareControllerRef.current = null;
        }
        if (
          operationGenerationRef.current === generation &&
          currentProjectIdRef.current === projectId
        ) {
          setIsPreparingFullTranslate(false);
        }
      }

      return false;
    },
    [currentProjectId, setView]
  );

  const submitTermReview = useCallback(
    async (decisions: TermReviewDecision[]) => {
      if (!currentProjectId || !pendingTermReview || !pendingTranslationRequest) {
        return;
      }
      if (decisions.length === 0) {
        toast.warning('请至少确认一个术语');
        return;
      }

      submitControllerRef.current?.abort();
      const controller = new AbortController();
      submitControllerRef.current = controller;
      const projectId = currentProjectId;
      const artifactId = pendingTermReview.artifact_id;
      const translationRequest = pendingTranslationRequest;
      const generation = ++operationGenerationRef.current;
      setIsSubmittingTermReview(true);
      try {
        const result = await glossaryApi.submitTermReview(
          projectId,
          artifactId,
          decisions,
          controller.signal
        );
        if (
          controller.signal.aborted ||
          operationGenerationRef.current !== generation ||
          currentProjectIdRef.current !== projectId
        ) {
          return;
        }

        setPendingTermReview(null);
        setPendingTranslationRequest(null);
        setView(null);
        if (result.applied_count > 0) {
          const skippedMessage = result.skipped_count > 0
            ? `，跳过 ${result.skipped_count} 个`
            : '';
          toast.success(
            `已应用 ${result.applied_count} 个术语${skippedMessage}，开始全文翻译`
          );
        } else {
          toast.info(`已跳过 ${result.skipped_count} 个术语，开始全文翻译`);
        }

        try {
          await runFullTranslate(translationRequest.method, translationRequest.model);
        } catch (error) {
          console.error('Failed to start translation after term review:', error);
          toast.error('术语预检已保存，但全文翻译启动失败，请重试');
        }
      } catch (error) {
        if (
          controller.signal.aborted ||
          operationGenerationRef.current !== generation ||
          currentProjectIdRef.current !== projectId
        ) {
          return;
        }
        console.error('Failed to submit term review:', error);
        if (isTermReviewArtifactConflict(error)) {
          setPendingTermReview(null);
          setPendingTranslationRequest(null);
          setView(null);
          toast.error('术语预检已更新，请重新开始全文翻译');
          return;
        }
        toast.error('保存术语预检失败');
      } finally {
        if (submitControllerRef.current === controller) {
          submitControllerRef.current = null;
        }
        if (
          operationGenerationRef.current === generation &&
          currentProjectIdRef.current === projectId
        ) {
          setIsSubmittingTermReview(false);
        }
      }
    },
    [
      currentProjectId,
      pendingTermReview,
      pendingTranslationRequest,
      runFullTranslate,
      setView,
    ]
  );

  const cancelTermReview = useCallback(() => {
    operationGenerationRef.current += 1;
    prepareControllerRef.current?.abort();
    submitControllerRef.current?.abort();
    prepareControllerRef.current = null;
    submitControllerRef.current = null;
    setPendingTermReview(null);
    setPendingTranslationRequest(null);
    setIsPreparingFullTranslate(false);
    setIsSubmittingTermReview(false);
    setView(null);
  }, [setView]);

  return {
    cancelTermReview,
    isPreparingFullTranslate,
    isSubmittingTermReview,
    pendingTermReview,
    prepareTermReviewIfNeeded,
    submitTermReview,
  };
}
