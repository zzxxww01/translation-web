import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  glossaryApi,
  isTermReviewArtifactConflict,
  isTermReviewModelConflict,
} from '../../confirmation/api/glossaryApi';
import type { TermReviewDecision, TermReviewPayload } from '../../confirmation/types';
import { TranslationMethod } from '@/shared/constants';
import { documentApi } from '../api';

interface PendingTranslationRequest {
  termReviewJobId: string;
  timeoutSeconds: number;
}

interface UseTermReviewFlowOptions {
  currentProjectId?: string;
  activeRunId?: string | null;
  setView: (view: 'glossary' | 'term-review' | null) => void;
}

export function useTermReviewFlow({
  currentProjectId,
  activeRunId,
  setView,
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
  const dismissedTermReviewJobRef = useRef<string | null>(null);
  currentProjectIdRef.current = currentProjectId;

  useEffect(() => {
    operationGenerationRef.current += 1;
    prepareControllerRef.current?.abort();
    submitControllerRef.current?.abort();
    prepareControllerRef.current = null;
    submitControllerRef.current = null;
    dismissedTermReviewJobRef.current = null;
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
      dismissedTermReviewJobRef.current = null;

      let workflowStarted = false;
      try {
        const workflow = await documentApi.startLongformWorkflow(
          projectId,
          method,
          model,
        );
        workflowStarted = true;
        if (
          operationGenerationRef.current !== generation ||
          currentProjectIdRef.current !== projectId
        ) {
          return true;
        }
        if (workflow.resumed || !workflow.term_review_job_id) {
          const checkpoint = workflow.resume_checkpoint;
          if (checkpoint) {
            toast.success(
              `已从断点继续：保留 ${checkpoint.translated_paragraphs} 段，只处理剩余 ${checkpoint.remaining_paragraphs} 段`
            );
          } else {
            toast.info('后台已从最近断点继续翻译');
          }
          return true;
        }
        setPendingTranslationRequest({
          termReviewJobId: workflow.term_review_job_id,
          timeoutSeconds: workflow.term_review_timeout_seconds,
        });
        toast.info('任务已交给后台，关闭或刷新页面不会中断翻译');

        const job = await glossaryApi.waitForTermReviewJob(
          projectId,
          workflow.term_review_job_id,
          controller.signal
        );
        if (
          controller.signal.aborted ||
          operationGenerationRef.current !== generation ||
          currentProjectIdRef.current !== projectId
        ) {
          return true;
        }
        if (job.status !== 'succeeded' || !job.result) {
          toast.warning('术语预检未完成，后台将跳过确认并继续全文翻译');
          return true;
        }
        const review = job.result;
        if (review.is_partial && (review.failed_sections || 0) > 0) {
          toast.warning(
            `术语预检已保留可用结果，${review.failed_sections} 个章节因模型波动被跳过`
          );
        }
        const reviewAlreadyResolved = Boolean(
          job.confirmation_status && job.confirmation_status !== 'waiting'
        );
        if (
          review.review_required &&
          review.total_candidates > 0 &&
          !reviewAlreadyResolved
        ) {
          setPendingTermReview(review);
          setView('term-review');
          const timeoutMinutes = Math.max(
            1,
            Math.ceil(workflow.term_review_timeout_seconds / 60)
          );
          toast.info(
            `检测到 ${review.total_candidates} 个新术语；${timeoutMinutes} 分钟未确认将自动采用当前建议继续`
          );
          return true;
        }
        toast.success('术语预检完成，后台已继续全文翻译');
      } catch (error) {
        if (
          controller.signal.aborted ||
          operationGenerationRef.current !== generation ||
          currentProjectIdRef.current !== projectId
        ) {
          return true;
        }
        console.error('Failed to prepare term review:', error);
        if (workflowStarted) {
          toast.warning('后台任务已启动；即使当前页面无法获取术语结果，任务仍会自动继续');
          return true;
        }
        try {
          const status = await documentApi.getTranslationStatus(projectId);
          if (status.active_project_id === projectId) {
            toast.info('后台已存在运行中的全文翻译任务，页面会继续同步进度');
            return true;
          }
        } catch {
          // Preserve the original start error when the read-only verification
          // is unavailable as well.
        }
        if (isTermReviewModelConflict(error)) {
          toast.error('该项目正在使用另一模型进行术语预检，请稍后重试');
          return true;
        }
        toast.error('后台任务启动失败，请重试');
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

      return true;
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
        dismissedTermReviewJobRef.current = artifactId;
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

        toast.info('术语确认已提交，后台将自动继续全文翻译');
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
          dismissedTermReviewJobRef.current = artifactId;
          setView(null);
          toast.info('术语确认窗口已结束，后台任务已经继续');
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
      setView,
    ]
  );

  const cancelTermReview = useCallback(() => {
    dismissedTermReviewJobRef.current =
      pendingTranslationRequest?.termReviewJobId || activeRunId || null;
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
    toast.info(
      '已关闭术语确认；后台会在确认窗口结束后自动继续，如需终止请点击“停止全文翻译”'
    );
  }, [activeRunId, pendingTranslationRequest?.termReviewJobId, setView]);

  useEffect(() => {
    if (!activeRunId || /^[0-9a-f]{32}$/i.test(activeRunId)) {
      return;
    }
    // The placeholder job id changes to the real translation run id when the
    // server releases the terminology gate (submission or timeout).
    setPendingTermReview(null);
    setPendingTranslationRequest(null);
    dismissedTermReviewJobRef.current = null;
    setView(null);
  }, [activeRunId, setView]);

  useEffect(() => {
    if (
      !currentProjectId ||
      !activeRunId ||
      !/^[0-9a-f]{32}$/i.test(activeRunId) ||
      dismissedTermReviewJobRef.current === activeRunId ||
      pendingTranslationRequest?.termReviewJobId === activeRunId
    ) {
      return;
    }

    const controller = new AbortController();
    const projectId = currentProjectId;
    const generation = ++operationGenerationRef.current;
    setIsPreparingFullTranslate(true);

    void glossaryApi
      .waitForTermReviewJob(projectId, activeRunId, controller.signal)
      .then(job => {
        if (
          controller.signal.aborted ||
          generation !== operationGenerationRef.current ||
          currentProjectIdRef.current !== projectId ||
          job.status !== 'succeeded' ||
          !job.result ||
          !job.result.review_required ||
          job.result.total_candidates <= 0 ||
          (job.confirmation_status && job.confirmation_status !== 'waiting')
        ) {
          return;
        }
        const deadlineMs = job.confirmation_deadline
          ? Date.parse(job.confirmation_deadline)
          : Number.NaN;
        const remainingSeconds = Number.isFinite(deadlineMs)
          ? Math.max(0, Math.ceil((deadlineMs - Date.now()) / 1000))
          : 600;
        setPendingTermReview(job.result);
        setPendingTranslationRequest({
          termReviewJobId: activeRunId,
          timeoutSeconds: remainingSeconds,
        });
        setView('term-review');
        toast.info('已恢复后台任务的术语确认页面');
      })
      .catch(error => {
        if (!controller.signal.aborted) {
          console.debug('Unable to restore terminology review:', error);
        }
      })
      .finally(() => {
        if (
          !controller.signal.aborted &&
          generation === operationGenerationRef.current &&
          currentProjectIdRef.current === projectId
        ) {
          setIsPreparingFullTranslate(false);
        }
      });

    return () => controller.abort();
  }, [
    activeRunId,
    currentProjectId,
    pendingTranslationRequest?.termReviewJobId,
    setView,
  ]);

  return {
    cancelTermReview,
    isPreparingFullTranslate,
    isSubmittingTermReview,
    pendingTermReview,
    termReviewTimeoutSeconds: pendingTranslationRequest?.timeoutSeconds,
    prepareTermReviewIfNeeded,
    submitTermReview,
  };
}
