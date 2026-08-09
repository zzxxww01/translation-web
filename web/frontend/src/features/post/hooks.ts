import { useMutation } from '@tanstack/react-query';
import { postApi } from './api';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';

/**
 * 用户主动取消时不弹错误提示。
 * client.ts 会把 AbortError/TimeoutError 统一归一化成「请求超时」，
 * 无法从 error 上区分，因此改为回看请求变量里的 signal 是否已被 abort。
 */
function isUserCancelled(variables: unknown): boolean {
  return Boolean((variables as { signal?: AbortSignal } | undefined)?.signal?.aborted);
}

export function useTranslatePost() {
  const { handleError } = useErrorHandler();
  return useMutation({
    mutationFn: postApi.translate,
    onError: (error, variables) => {
      if (isUserCancelled(variables)) return;
      handleError(error, '翻译失败');
    },
  });
}

export function useOptimizePost() {
  const { handleError } = useErrorHandler();
  return useMutation({
    mutationFn: postApi.optimize,
    onError: (error, variables) => {
      if (isUserCancelled(variables)) return;
      handleError(error, '优化失败');
    },
  });
}

export function useGenerateTitle() {
  const { handleError } = useErrorHandler();
  return useMutation({
    mutationFn: postApi.generateTitle,
    onError: (error, variables) => {
      if (isUserCancelled(variables)) return;
      handleError(error, '生成标题失败');
    },
  });
}

export function useGenerateHashtags() {
  const { handleError } = useErrorHandler();
  return useMutation({
    mutationFn: postApi.generateHashtags,
    onError: (error, variables) => {
      if (isUserCancelled(variables)) return;
      handleError(error, '生成标签失败');
    },
  });
}
