import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';
import { slackInboxApi } from './api';

// Slack 的会话和消息接口限额约 50 次/分钟；60 秒轮询一次足够，也给翻页和展开 thread 留余量
const POLL_MS = 60_000;

export const slackInboxKeys = {
  status: ['slack-inbox', 'status'] as const,
  conversations: ['slack-inbox', 'conversations'] as const,
  messages: (channelId: string) => ['slack-inbox', 'messages', channelId] as const,
  replies: (channelId: string, threadTs: string) => ['slack-inbox', 'replies', channelId, threadTs] as const,
};

export function useSlackStatus() {
  return useQuery({
    queryKey: slackInboxKeys.status,
    queryFn: slackInboxApi.status,
    staleTime: 60_000,
  });
}

export function useSlackConversations(enabled: boolean) {
  return useQuery({
    queryKey: slackInboxKeys.conversations,
    queryFn: () => slackInboxApi.conversations(),
    enabled,
    refetchInterval: POLL_MS,
    staleTime: 20_000,
    select: data => data.conversations,
  });
}

export function useSlackMessages(channelId: string | null) {
  return useInfiniteQuery({
    queryKey: slackInboxKeys.messages(channelId ?? ''),
    queryFn: ({ pageParam }) => slackInboxApi.messages(channelId!, pageParam || undefined),
    initialPageParam: '',
    getNextPageParam: page => page.next_cursor ?? undefined,
    enabled: !!channelId,
    refetchInterval: POLL_MS,
    staleTime: 20_000,
  });
}

export function useSlackReplies(channelId: string, threadTs: string, enabled: boolean) {
  return useQuery({
    queryKey: slackInboxKeys.replies(channelId, threadTs),
    queryFn: () => slackInboxApi.replies(channelId, threadTs),
    enabled,
    staleTime: 20_000,
    // 第一条是根消息本身，列表里已经有了
    select: data => data.messages.slice(1),
  });
}

export function useRefreshSlack() {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  return useMutation({
    mutationFn: () => slackInboxApi.conversations(true),
    onSuccess: data => {
      queryClient.setQueryData(slackInboxKeys.conversations, data);
      void queryClient.invalidateQueries({ queryKey: ['slack-inbox', 'messages'] });
      void queryClient.invalidateQueries({ queryKey: ['slack-inbox', 'replies'] });
    },
    onError: error => handleError(error, '刷新 Slack 失败'),
  });
}

export function useSaveSlackCredentials() {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  return useMutation({
    mutationFn: slackInboxApi.saveCredentials,
    onSuccess: status => {
      queryClient.setQueryData(slackInboxKeys.status, status);
      if (status.ok) {
        toast.success(`已连接 Slack：${status.user} · ${status.team}`);
        void queryClient.invalidateQueries({ queryKey: ['slack-inbox'] });
      } else {
        toast.error(status.error || '凭证无效');
      }
    },
    onError: error => handleError(error, '保存凭证失败'),
  });
}
