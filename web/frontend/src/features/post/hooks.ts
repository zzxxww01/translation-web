/**
 * 帖子翻译相关的 React Query hooks
 */

import { useMutation } from '@tanstack/react-query';
import { postApi } from './api';
import { useToast } from '../../components/ui';
import { useErrorHandler } from '../../shared/hooks/useErrorHandler';

/**
 * 翻译帖子
 */
export function useTranslatePost() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: postApi.translate,
    onSuccess: () => {
      showSuccess('翻译完成');
    },
    onError: error => {
      handleError(error, '翻译失败');
    },
  });
}

/**
 * 优化译文
 */
export function useOptimizePost() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: postApi.optimize,
    onSuccess: () => {
      showSuccess('优化完成');
    },
    onError: error => {
      handleError(error, '优化失败');
    },
  });
}

/**
 * 生成标题
 */
export function useGenerateTitle() {
  const { showToast } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: postApi.generateTitle,
    onSuccess: () => {
      showToast('正在生成标题...', 'info');
    },
    onError: error => {
      handleError(error, '生成标题失败');
    },
  });
}
