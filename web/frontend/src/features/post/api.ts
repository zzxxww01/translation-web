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

/**
 * 帖子翻译 API
 */
export const postApi = {
  /**
   * 翻译帖子
   */
  translate: (data: TranslatePostDto) =>
    apiClient.post<TranslatePostResult>('/translate/post', data, {
      timeout: REQUEST_TIMEOUTS.POST_TRANSLATE,
      retry: false,
    }),

  /**
   * 优化译文
   */
  optimize: (data: OptimizePostDto) =>
    apiClient.post<OptimizePostResult>('/translate/post/optimize', data, {
      timeout: REQUEST_TIMEOUTS.POST_OPTIMIZE,
      retry: false,
    }),

  /**
   * 生成标题
   */
  generateTitle: (data: GenerateTitleDto) =>
    apiClient.post<GenerateTitleResult>('/generate/title', data, {
      timeout: REQUEST_TIMEOUTS.POST_TITLE,
    }),
};
