/**
 * 分段确认工作流 - 核心Hook
 */

import { useCallback, useEffect } from 'react';
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
    setCustomTranslation,
    goToNext,
    goToPrev,
    jumpTo,
    setLoading,
    setError,
  } = useConfirmationStore();

  // 初始化工作流
  const initialize = useCallback(async (id: string) => {
    setProjectId(id);
    setLoading(true);
    setError(null);

    try {
      // 检查翻译状态
      const status = await confirmationApi.getTranslationStatus(id);

      if (status.status === 'completed' || status.status === 'not_started') {
        // 翻译已完成或未开始
        if (status.translated_paragraphs === 0) {
          // 需要启动翻译
          await confirmationApi.startTranslation(id);
          setWorkflowStatus('translating');
        } else {
          setWorkflowStatus('ready');
        }
      } else if (status.status === 'processing') {
        setWorkflowStatus('translating');
      } else if (status.status === 'failed') {
        setError('翻译失败，请重试');
        setWorkflowStatus('loading');
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : '初始化失败';
      setError(message);
      setWorkflowStatus('loading');
    } finally {
      setLoading(false);
    }
  }, [setProjectId, setLoading, setError, setWorkflowStatus]);

  // 轮询翻译状态
  useEffect(() => {
    if (!projectId || workflowStatus !== 'translating') return;

    const interval = setInterval(async () => {
      try {
        const status = await confirmationApi.getTranslationStatus(projectId);

        if (status.status === 'completed') {
          setWorkflowStatus('ready');
          clearInterval(interval);
        } else if (status.status === 'failed') {
          setError('翻译失败，请重试');
          setWorkflowStatus('loading');
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Failed to check translation status:', error);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [projectId, workflowStatus, setWorkflowStatus, setError]);

  // 加载段落
  const loadParagraph = useCallback(async (index: number): Promise<ParagraphConfirmationResponse | undefined> => {
    if (!projectId) {
      setError('未选择项目');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await confirmationApi.getParagraphConfirmation(projectId, index);
      setCurrentParagraph(data.paragraph, data.versions);
      jumpTo(index);
      return data;
    } catch (error) {
      const message = error instanceof Error ? error.message : '加载段落失败';
      setError(message);
      return undefined;
    } finally {
      setLoading(false);
    }
  }, [projectId, setCurrentParagraph, jumpTo, setLoading, setError]);

  // 选择版本
  const selectVersion = useCallback((versionId: string) => {
    const { versions } = useConfirmationStore.getState();
    const version = versions.find((v) => v.id === versionId);

    if (version) {
      setCustomTranslation(version.translation);
    }
  }, [setCustomTranslation]);

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
