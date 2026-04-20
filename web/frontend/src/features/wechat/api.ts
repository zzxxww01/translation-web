import { apiClient } from '../../shared/api/client';
import type { WechatFormatRequest, WechatFormatResponse, WechatThemesResponse } from './types';

/**
 * 微信排版 API
 */
export const wechatApi = {
  /**
   * 格式化 Markdown 为微信公众号格式
   */
  format: (data: WechatFormatRequest) =>
    apiClient.post<WechatFormatResponse>('/wechat/format', data, {
      timeout: 300000, // 5分钟，支持大量图片处理
      retry: false,
    }),

  /**
   * 获取可用主题列表
   */
  getThemes: () =>
    apiClient.get<WechatThemesResponse>('/wechat/themes'),
};
