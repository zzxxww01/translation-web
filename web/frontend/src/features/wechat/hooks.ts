import { useMutation, useQuery } from '@tanstack/react-query';
import { wechatApi } from './api';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';

/**
 * 格式化 Markdown
 */
export function useFormatWechat() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: wechatApi.format,
    onError: error => {
      handleError(error, '排版转换失败');
    },
  });
}

/**
 * 获取主题列表
 *
 * 注意：react-query v5 的 useQuery 已移除 onError，失败提示需由页面消费 isError 后触发。
 */
export function useWechatThemes() {
  return useQuery({
    queryKey: ['wechat-themes'],
    queryFn: wechatApi.getThemes,
    staleTime: Infinity,
  });
}
