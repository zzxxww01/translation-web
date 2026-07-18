import { useMutation } from '@tanstack/react-query';
import { postApi } from './api';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';

export function useTranslatePost() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: postApi.translate,
    onError: error => {
      handleError(error, '翻译失败');
    },
  });
}

export function useOptimizePost() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: postApi.optimize,
    onError: error => {
      handleError(error, '优化失败');
    },
  });
}

export function useGenerateTitle() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: postApi.generateTitle,
    onError: error => {
      handleError(error, '生成标题失败');
    },
  });
}
