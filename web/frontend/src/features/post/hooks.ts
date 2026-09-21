import { useMutation } from '@tanstack/react-query';
import { postApi } from './api';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';

/**
 * 用户主动取消时不弹错误提示。
 * 请求变量的 signal 可识别主动取消；传输层还会保留 AbortError，
 * 与真正超时返回的 408 分开处理。
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
