import { useMutation, useQuery } from '@tanstack/react-query';
import { wechatApi } from './api';

/**
 * 格式化 Markdown
 */
export function useFormatWechat() {
  return useMutation({
    mutationFn: wechatApi.format,
  });
}

/**
 * 获取主题列表
 */
export function useWechatThemes() {
  return useQuery({
    queryKey: ['wechat-themes'],
    queryFn: wechatApi.getThemes,
    staleTime: Infinity,
  });
}
