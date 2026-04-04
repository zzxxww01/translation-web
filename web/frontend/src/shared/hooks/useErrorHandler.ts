/**
 * 统一的错误处理 Hook
 * 提供错误捕获、格式化和显示功能
 */

import { useCallback } from 'react';
import { toast } from 'sonner';

/**
 * API 错误接口
 */
export interface ApiErrorLike {
  detail?: string;
  message?: string;
  status?: number;
  data?: unknown;
}

/**
 * 判断是否为 API 错误
 */
function isApiError(error: unknown): error is ApiErrorLike {
  return (
    typeof error === 'object' &&
    error !== null &&
    ('detail' in error || 'message' in error || 'status' in error)
  );
}

/**
 * 提取错误消息
 */
function extractErrorMessage(error: unknown): string {
  // API 错误
  if (isApiError(error)) {
    return error.detail || error.message || '请求失败，请稍后重试';
  }

  // 标准错误对象
  if (error instanceof Error) {
    if (error.name === 'AbortError' || error.message.toLowerCase().includes('aborted')) {
      return 'Request timeout. Please try again.';
    }
    return error.message;
  }

  // 字符串错误
  if (typeof error === 'string') {
    return error;
  }

  // 未知错误
  return '发生未知错误，请稍后重试';
}

/**
 * 根据状态码获取用户友好的错误消息
 */
function getErrorMessageByStatus(status: number | undefined): string | null {
  if (!status) return null;

  const statusMessages: Record<number, string> = {
    400: '请求参数有误，请检查后重试',
    401: '登录已过期，请重新登录',
    403: '没有权限执行此操作',
    404: '请求的资源不存在',
    429: '请求过于频繁，请稍后重试',
    500: '服务器错误，请稍后重试',
    502: '网关错误，请稍后重试',
    503: '服务暂时不可用，请稍后重试',
  };

  return statusMessages[status] || null;
}

/**
 * 错误处理 Hook
 */
export function useErrorHandler() {
  /**
   * 处理错误并显示 Toast
   */
  const handleError = useCallback(
    (error: unknown, context?: string) => {
      const errorMessage = extractErrorMessage(error);

      // 尝试从状态码获取更友好的消息
      const statusMessage = isApiError(error)
        ? getErrorMessageByStatus(error.status)
        : null;

      // 400 常带有后端提供的可操作细节，不要用固定文案覆盖。
      const displayMessage =
        isApiError(error) && error.status === 400
          ? errorMessage
          : statusMessage || errorMessage;

      // 添加上下文信息
      const fullMessage = context ? `${context}: ${displayMessage}` : displayMessage;

      toast.error(fullMessage);

      // 在开发环境打印错误详情
      if (import.meta.env.DEV) {
        console.error('[Error Handler]', error);
      }
    },
    []
  );

  /**
   * 处理错误但不显示 Toast（静默处理）
   */
  const handleErrorSilently = useCallback((error: unknown) => {
    if (import.meta.env.DEV) {
      console.error('[Error Handler (Silent)]', error);
    }
  }, []);

  /**
   * 创建带有错误处理的异步函数包装器
   */
  const withErrorHandler = useCallback(
    <T extends (...args: unknown[]) => Promise<unknown>>(
      fn: T,
      context?: string
    ): T => {
      return (async (...args: Parameters<T>) => {
        try {
          return await fn(...args);
        } catch (error) {
          handleError(error, context);
          throw error;
        }
      }) as T;
    },
    [handleError]
  );

  return {
    handleError,
    handleErrorSilently,
    withErrorHandler,
    extractErrorMessage,
  };
}
