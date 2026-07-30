import { useEffect, useState } from 'react';
import { documentApi } from '../api';
import { fullTranslationService } from '../services/fullTranslationService';
import type { TranslationStatus } from '../../confirmation/types';
import { useDocumentStore } from '@/shared/stores';
import { isTranslationRunActive } from '../translationStatus';

export function useTranslationStatusSync(currentProjectId?: string) {
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [backendTranslationStatus, setBackendTranslationStatus] = useState<TranslationStatus | null>(null);

  // 注意：fullTranslateProjectId 由 syncStatus 自己写入（setFullTranslateProjectId / endFullTranslate），
  // 若订阅成组件状态并放进依赖数组，会导致 effect 反复重建 interval 并多打请求，
  // 因此改为在 syncStatus 内用 getState() 读取瞬时值。
  const setFullTranslating = useDocumentStore(state => state.setFullTranslating);
  const setFullTranslateProgress = useDocumentStore(state => state.setFullTranslateProgress);
  const setFullTranslateProjectId = useDocumentStore(state => state.setFullTranslateProjectId);
  const endFullTranslate = useDocumentStore(state => state.endFullTranslate);

  useEffect(() => {
    let cancelled = false;
    // 只在项目切换后的首次同步清一次旧项目状态；轮询回调内不再清空，
    // 否则每 5 秒都会先置 null 再等 HTTP 往返回填，侧栏步骤文案与百分比会周期性闪烁。
    let isFirstSync = true;

    const syncStatus = async () => {
      if (isFirstSync) {
        isFirstSync = false;
        setCurrentStep(null);
        setBackendTranslationStatus(null);
      }

      if (!currentProjectId) {
        return;
      }

      try {
        const status = await documentApi.getTranslationStatus(currentProjectId);
        if (cancelled) {
          return;
        }

        setBackendTranslationStatus(status);

        const hasTrackableRun = isTranslationRunActive(
          status,
          currentProjectId
        );

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

        const hasActiveLocalStream =
          fullTranslationService.isTranslating() &&
          fullTranslationService.getProjectId() === currentProjectId;
        if (
          useDocumentStore.getState().fullTranslateProjectId === currentProjectId &&
          !hasActiveLocalStream
        ) {
          endFullTranslate(currentProjectId);
        }
        // 后端没有在跑、本地也没有 SSE 流时清掉步骤文案。放在 if 外面：
        // 只在 if 内清会让「store 里记的是别的项目」这条路径永远留着上一次
        // 轮询的残留文案（消除闪烁不该顺带让文案永不过期）。
        if (!fullTranslationService.isTranslating()) {
          setCurrentStep(null);
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
