import { apiClient } from '../../shared/api/client';
import { REQUEST_TIMEOUTS } from '../../shared/constants';
import type {
  TranslatePostDto,
  TranslatePostResult,
  OptimizePostDto,
  OptimizePostResult,
  GenerateTitleDto,
  GenerateTitleResult,
} from '../../shared/types';

/** 允许调用方传入取消信号；signal 只用于 fetch，不会进入请求体 */
type Cancellable<T> = T & { signal?: AbortSignal };

/**
 * 帖子翻译 API
 */
export const postApi = {
  /**
   * 翻译帖子
   */
  translate: ({ signal, ...data }: Cancellable<TranslatePostDto>) =>
    apiClient.post<TranslatePostResult>('/translate/post', data, {
      timeout: REQUEST_TIMEOUTS.POST_TRANSLATE,
      retry: false,
      signal,
    }),

  /**
   * 优化译文
   */
  optimize: ({ signal, ...data }: Cancellable<OptimizePostDto>) =>
    apiClient.post<OptimizePostResult>('/translate/post/optimize', data, {
      timeout: REQUEST_TIMEOUTS.POST_OPTIMIZE,
      retry: false,
      signal,
    }),

  /**
   * 生成标题
   */
  generateTitle: ({ signal, ...data }: Cancellable<GenerateTitleDto>) =>
    apiClient.post<GenerateTitleResult>('/generate/title', data, {
      timeout: REQUEST_TIMEOUTS.POST_TITLE,
      retry: false,
      signal,
    }),
};
