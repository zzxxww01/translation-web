import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { postApi } from './api';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';

export function useTranslatePost() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: postApi.translate,
    onSuccess: () => {
      toast.success('翻译完成');
    },
    onError: error => {
      handleError(error, '翻译失败');
    },
  });
}

export function useOptimizePost() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: postApi.optimize,
    onSuccess: () => {
      toast.success('优化完成');
    },
    onError: error => {
      handleError(error, '优化失败');
    },
  });
}

export function useGenerateTitle() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: postApi.generateTitle,
    onSuccess: () => {
      toast.info('正在生成标题...');
    },
    onError: error => {
      handleError(error, '生成标题失败');
    },
  });
}
