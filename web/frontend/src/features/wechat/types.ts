/**
 * 微信排版功能类型定义
 */

export interface WechatFormatRequest {
  markdown: string;
  theme?: string;
  upload_images?: boolean;
  image_to_base64?: boolean;
}

export interface WechatFormatResponse {
  html: string;
  css: string;
  image_count: number;
  image_urls: string[];
  /** 识别到的数学公式条数，用于提示公众号侧的已知限制 */
  formula_count?: number;
}

export interface WechatTheme {
  id: string;
  name: string;
  description: string;
}

export interface WechatThemesResponse {
  themes: WechatTheme[];
}

export type WechatImageMode = 'keep' | 'upload' | 'base64';

export interface WechatDraft {
  markdown: string;
  selectedTheme: string;
  imageMode: WechatImageMode;
}
