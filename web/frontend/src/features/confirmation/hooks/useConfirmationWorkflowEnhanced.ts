/**
 * 分段确认工作流 - 增强版Hook
 * 包含Toast通知和错误处理
 */

import { useCallback } from 'react';
import { useConfirmationWorkflow as useBaseWorkflow } from './useConfirmationWorkflow';
import { toast } from 'sonner';
import type { TermChange } from '../types';

export function useConfirmationWorkflow() {
  const baseWorkflow = useBaseWorkflow();

  // 包装初始化函数
  const initialize = useCallback(
    async (id: string) => {
      try {
        await baseWorkflow.initialize(id);
        toast.success('工作流初始化成功');
      } catch (error) {
        const message = error instanceof Error ? error.message : '初始化失败';
        toast.error(message);
        throw error;
      }
    },
    [baseWorkflow]
  );

  // 包装确认段落函数
  const confirmParagraph = useCallback(
    async (translation: string, versionId?: string, customEdit = false) => {
      try {
        await baseWorkflow.confirmParagraph(translation, versionId, customEdit);
        toast.success('译文已确认', { duration: 2000 });
      } catch (error) {
        const message = error instanceof Error ? error.message : '确认失败';
        toast.error(message);
        throw error;
      }
    },
    [baseWorkflow]
  );

  // 包装术语更新函数
  const updateTerms = useCallback(
    async (changes: TermChange[]) => {
      if (changes.length === 0) return;

      try {
        await baseWorkflow.updateTerms(changes);
        toast.success(`已自动更新${changes.length}个术语翻译`, { duration: 3000 });
      } catch (error) {
        console.error('Failed to update terms:', error);
        // 静默失败，不阻塞用户操作
      }
    },
    [baseWorkflow]
  );

  // 包装导出函数
  const exportTranslation = useCallback(async () => {
    try {
      const result = await baseWorkflow.exportTranslation();
      toast.success('译文导出成功');
      return result;
    } catch (error) {
      const message = error instanceof Error ? error.message : '导出失败';
      toast.error(message);
      throw error;
    }
  }, [baseWorkflow]);

  // 包装导入函数
  const importReferenceVersion = useCallback(
    async (versionName: string, markdownContent: string) => {
      try {
        const result = await baseWorkflow.importReferenceVersion(versionName, markdownContent);
        toast.success(`成功导入参考译文"${versionName}"`);
        return result;
      } catch (error) {
        const message = error instanceof Error ? error.message : '导入失败';
        toast.error(message);
        throw error;
      }
    },
    [baseWorkflow]
  );

  return {
    ...baseWorkflow,
    initialize,
    confirmParagraph,
    updateTerms,
    exportTranslation,
    importReferenceVersion,
  };
}
