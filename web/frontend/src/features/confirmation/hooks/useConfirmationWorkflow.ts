/**
 * 分段确认工作流 - 核心Hook
 */

import { useCallback, useEffect, useRef } from 'react';
import { useConfirmationStore } from '../stores/confirmationStore';
import { confirmationApi } from '../api/confirmationApi';
import type {
  ConfirmParagraphRequest,
  ParagraphConfirmationResponse,
  TermChange,
} from '../types';

export function useConfirmationWorkflow() {
  const {
    projectId,
    workflowStatus,
    currentIndex,
    setProjectId,
    setWorkflowStatus,
    setCurrentParagraph,
    setTotalParagraphs,
    setSelectedVersion,
    setCustomTranslation,
    goToNext,
    goToPrev,
    jumpTo,
    setLoading,
    setError,
  } = useConfirmationStore();

  // N13: 单调递增的请求ID，用于丢弃过期的 loadParagraph 响应（防止并发/快速切段时旧数据覆盖新段落）
  const loadRequestRef = useRef(0);

  const getCompletionState = useCallback(
    (status: {
      translated_paragraphs?: number;
      total_paragraphs?: number;
      is_complete?: boolean;
    }) => {
      const translated = status.translated_paragraphs ?? 0;
      const total = status.total_paragraphs ?? 0;
      const isComplete = status.is_complete ?? (total > 0 && translated >= total);
      return { translated, total, isComplete };
    },
    []
  );

  // 初始化工作流
  const initialize = useCallback(async (id: string) => {
    setProjectId(id);
    setLoading(true);
    setError(null);

    try {
      // 检查翻译状态
      const status = await confirmationApi.getTranslationStatus(id);

      const { isComplete } = getCompletionState(status);

      if (status.status === 'processing') {
        setWorkflowStatus('translating');
      } else if (status.status === 'cancelled') {
        setError('翻译已取消，可重新开始');
        setWorkflowStatus('ready');
      } else if (status.status === 'failed') {
        setError('翻译失败，请重试');
        setWorkflowStatus('ready');
      } else if (!isComplete) {
        await confirmationApi.startTranslation(id);
        setWorkflowStatus('translating');
      } else {
        setWorkflowStatus('ready');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '初始化失败';
      setError(message);
      setWorkflowStatus('ready');
    } finally {
      setLoading(false);
    }
  }, [getCompletionState, setProjectId, setLoading, setError, setWorkflowStatus]);

  // 轮询翻译状态
  useEffect(() => {
    if (!projectId || workflowStatus !== 'translating') return;

    const interval = setInterval(async () => {
      try {
        const status = await confirmationApi.getTranslationStatus(projectId);
        const { isComplete } = getCompletionState(status);

        if (status.status === 'processing') {
          return;
        }

        if (status.status === 'cancelled') {
          setError('翻译已取消，可重新开始');
          setWorkflowStatus('ready');
          clearInterval(interval);
        } else if (status.status === 'failed') {
          setError('翻译失败，请重试');
          setWorkflowStatus('ready');
          clearInterval(interval);
        } else if (isComplete) {
          setWorkflowStatus('ready');
          clearInterval(interval);
        } else {
          setError('翻译未完成，请点击重试继续翻译');
          setWorkflowStatus('ready');
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Failed to check translation status:', error);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [getCompletionState, projectId, workflowStatus, setWorkflowStatus, setError]);

  // 加载段落
  const loadParagraph = useCallback(async (index: number): Promise<ParagraphConfirmationResponse | undefined> => {
    if (!projectId) {
      setError('未选择项目');
      return;
    }

    // N13: 记录本次请求ID；若响应返回时已被更新的请求取代，则丢弃本次结果，避免旧数据覆盖新段落或回拨 index
    const requestId = ++loadRequestRef.current;

    setLoading(true);
    setError(null);

    try {
      const data = await confirmationApi.getParagraphConfirmation(projectId, index);
      // 过期请求：直接丢弃，不写入任何状态
      if (requestId !== loadRequestRef.current) {
        return data;
      }
      setCurrentParagraph(data.paragraph, data.versions);
      if (typeof data.total_paragraphs === 'number') {
        setTotalParagraphs(data.total_paragraphs);
      }
      jumpTo(index);
      return data;
    } catch (error) {
      // 过期请求的错误同样丢弃，避免覆盖更新请求的状态
      if (requestId !== loadRequestRef.current) {
        return undefined;
      }
      const message = error instanceof Error ? error.message : '加载段落失败';
      setError(message);
      return undefined;
    } finally {
      // 仅最新请求负责清除 loading，避免过期请求提前关闭新请求的加载态
      if (requestId === loadRequestRef.current) {
        setLoading(false);
      }
    }
  }, [projectId, setCurrentParagraph, setTotalParagraphs, jumpTo, setLoading, setError]);

  // 选择版本
  const selectVersion = useCallback((versionId: string) => {
    const { versions } = useConfirmationStore.getState();
    const version = versions.find((v) => v.id === versionId);

    if (version) {
      // N21: 同时记录选中版本 ID,使卡片显示选中态、确认时能带上 version_id 归因
      setSelectedVersion(versionId);
      setCustomTranslation(version.translation);
    }
  }, [setSelectedVersion, setCustomTranslation]);

  // 确认段落
  const confirmParagraph = useCallback(async (translation: string, versionId?: string, customEdit = false) => {
    if (!projectId) {
      setError('未选择项目');
      return;
    }

    const { currentParagraph } = useConfirmationStore.getState();
    if (!currentParagraph) {
      setError('未加载段落');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const request: ConfirmParagraphRequest = {
        translation,
        version_id: versionId,
        custom_edit: customEdit,
      };

      await confirmationApi.confirmParagraph(projectId, currentParagraph.id, request);

      // 移至下一段
      goToNext();
    } catch (error) {
      const message = error instanceof Error ? error.message : '确认失败';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [projectId, goToNext, setLoading, setError]);

  // 更新术语
  const updateTerms = useCallback(async (changes: TermChange[]) => {
    if (!projectId) {
      setError('未选择项目');
      return;
    }

    try {
      await confirmationApi.updateTerms(projectId, changes);
    } catch (error) {
      console.error('Failed to update terms:', error);
    }
  }, [projectId, setError]);

  // 导出译文
  const exportTranslation = useCallback(async () => {
    if (!projectId) {
      setError('未选择项目');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await confirmationApi.exportTranslation(projectId);
      confirmationApi.downloadExportedTranslation(result.content, result.filename);
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : '导出失败';
      setError(message);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [projectId, setLoading, setError]);

  // 导入参考译文
  const importReferenceVersion = useCallback(async (versionName: string, markdownContent: string) => {
    if (!projectId) {
      setError('未选择项目');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await confirmationApi.importReferenceVersion(projectId, {
        version_name: versionName,
        markdown_content: markdownContent,
      });
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : '导入失败';
      setError(message);
      throw error;
    } finally {
      setLoading(false);
    }
  }, [projectId, setLoading, setError]);

  return {
    // 状态
    projectId,
    workflowStatus,
    currentIndex,
    isLoading: useConfirmationStore((state) => state.isLoading),
    error: useConfirmationStore((state) => state.error),
    currentParagraph: useConfirmationStore((state) => state.currentParagraph),
    versions: useConfirmationStore((state) => state.versions),
    totalParagraphs: useConfirmationStore((state) => state.totalParagraphs),

    // 操作方法
    initialize,
    loadParagraph,
    selectVersion,
    confirmParagraph,
    updateTerms,
    exportTranslation,
    importReferenceVersion,
    nextParagraph: goToNext,
    prevParagraph: goToPrev,
    jumpTo,
  };
}
