import { useEffect, useState } from 'react';
import { documentApi } from '../api';
import { fullTranslationService } from '../services/fullTranslationService';
import type { TranslationStatus } from '../../confirmation/types';
import { useDocumentStore } from '@/shared/stores';

export function useTranslationStatusSync(currentProjectId?: string) {
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [backendTranslationStatus, setBackendTranslationStatus] = useState<TranslationStatus | null>(null);

  const fullTranslateProjectId = useDocumentStore(state => state.fullTranslateProjectId);
  const setFullTranslating = useDocumentStore(state => state.setFullTranslating);
  const setFullTranslateProgress = useDocumentStore(state => state.setFullTranslateProgress);
  const setFullTranslateProjectId = useDocumentStore(state => state.setFullTranslateProjectId);
  const endFullTranslate = useDocumentStore(state => state.endFullTranslate);

  useEffect(() => {
    let cancelled = false;

    const syncStatus = async () => {
      setCurrentStep(null);
      setBackendTranslationStatus(null);

      if (!currentProjectId) {
        return;
      }

      try {
        const status = await documentApi.getTranslationStatus(currentProjectId);
        if (cancelled) {
          return;
        }

        setBackendTranslationStatus(status);

        const isActiveForCurrentProject = status.active_project_id === currentProjectId;
        const isRunning = status.status === 'processing' && isActiveForCurrentProject;
        const isCancelling = Boolean(status.is_cancelling && isActiveForCurrentProject);
        const hasTrackableRun = isRunning || isCancelling;

        if (hasTrackableRun) {
          setFullTranslateProjectId(currentProjectId);
          setFullTranslating(true);
          setFullTranslateProgress({
            current: status.translated_paragraphs || 0,
            total: status.total_paragraphs || 0,
          });
          setCurrentStep(status.current_step || null);
          return;
        }

        if (
          fullTranslateProjectId === currentProjectId ||
          (!fullTranslationService.isTranslating() && !status.active_project_id)
        ) {
          endFullTranslate();
          if (!fullTranslationService.isTranslating()) {
            setCurrentStep(null);
          }
        }
      } catch (error) {
        if (!cancelled) {
          console.error('Failed to sync translation status:', error);
        }
      }
    };

    void syncStatus();
    if (!currentProjectId) {
      return () => {
        cancelled = true;
      };
    }
    const intervalId = window.setInterval(syncStatus, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [
    currentProjectId,
    endFullTranslate,
    fullTranslateProjectId,
    setFullTranslateProgress,
    setFullTranslateProjectId,
    setFullTranslating,
  ]);

  return {
    backendTranslationStatus,
    currentStep,
    setBackendTranslationStatus,
    setCurrentStep,
  };
}
