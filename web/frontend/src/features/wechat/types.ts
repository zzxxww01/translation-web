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
  image_count: number;
  image_urls: string[];
}

export interface WechatTheme {
  id: string;
  name: string;
}
