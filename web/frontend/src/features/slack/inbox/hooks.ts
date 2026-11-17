import { useEffect, useState } from 'react';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';
import { slackInboxApi } from './api';
import type { SlackConversationList } from './types';

// 后端对 client.counts 缓存 30 秒；会话和消息接口限额约 50 次/分钟，thread 列表轮询放慢一些
const POLL_MS = 30_000;
const THREAD_POLL_MS = 60_000;

export const slackInboxKeys = {
  status: ['slack-inbox', 'status'] as const,
  conversations: ['slack-inbox', 'conversations'] as const,
  messages: (channelId: string) => ['slack-inbox', 'messages', channelId] as const,
  replies: (channelId: string, threadTs: string) => ['slack-inbox', 'replies', channelId, threadTs] as const,
  threads: ['slack-inbox', 'threads'] as const,
  channelThreads: (channelId: string) => ['slack-inbox', 'channel-threads', channelId] as const,
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

export function useSlackReplies(channelId: string, threadTs: string, enabled = true) {
  return useQuery({
    queryKey: slackInboxKeys.replies(channelId, threadTs),
    queryFn: () => slackInboxApi.replies(channelId, threadTs),
    enabled,
    refetchInterval: POLL_MS,
    staleTime: 20_000,
  });
}

export function useSlackThreads(enabled: boolean) {
  return useQuery({
    queryKey: slackInboxKeys.threads,
    queryFn: slackInboxApi.threads,
    enabled,
    refetchInterval: THREAD_POLL_MS,
    staleTime: 20_000,
    select: data => data.threads,
  });
}

export function useChannelThreads(channelId: string, enabled: boolean) {
  return useQuery({
    queryKey: slackInboxKeys.channelThreads(channelId),
    queryFn: () => slackInboxApi.channelThreads(channelId),
    enabled,
    refetchInterval: THREAD_POLL_MS,
    staleTime: 20_000,
    select: data => data.threads,
  });
}

/** 看过就在 Slack 里标为已读（只推进我自己的已读位置，后端不会往回退）。先本地清掉未读标记，界面立即生效。 */
export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ channelId, ts }: { channelId: string; ts: string }) => slackInboxApi.markRead(channelId, ts),
    onMutate: ({ channelId, ts }) => {
      queryClient.setQueryData<SlackConversationList>(slackInboxKeys.conversations, data => data && {
        ...data,
        conversations: data.conversations.map(c =>
          c.id === channelId ? { ...c, has_unreads: false, mention_count: 0, last_read: ts } : c
        ),
      });
    },
    onSettled: () => void queryClient.invalidateQueries({ queryKey: slackInboxKeys.conversations }),
  });
}

export function useMarkThreadRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ channelId, threadTs, ts }: { channelId: string; threadTs: string; ts: string }) =>
      slackInboxApi.markThreadRead(channelId, threadTs, ts),
    onSuccess: result => {
      if (!result.marked) return;
      void queryClient.invalidateQueries({ queryKey: slackInboxKeys.threads });
      void queryClient.invalidateQueries({ queryKey: ['slack-inbox', 'channel-threads'] });
      void queryClient.invalidateQueries({ queryKey: slackInboxKeys.conversations });
    },
  });
}

export function useRefreshSlack() {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  return useMutation({
    mutationFn: () => slackInboxApi.conversations(true),
    onSuccess: data => {
      queryClient.setQueryData(slackInboxKeys.conversations, data);
      void queryClient.invalidateQueries({
        predicate: q => q.queryKey[0] === 'slack-inbox' && q.queryKey[1] !== 'conversations' && q.queryKey[1] !== 'status',
      });
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

/** 页面可见时才算「看过」，后台标签页里轮询到的新消息不标已读。 */
export function usePageVisible() {
  const [visible, setVisible] = useState(() => typeof document === 'undefined' || document.visibilityState === 'visible');
  useEffect(() => {
    const onChange = () => setVisible(document.visibilityState === 'visible');
    document.addEventListener('visibilitychange', onChange);
    return () => document.removeEventListener('visibilitychange', onChange);
  }, []);
  return visible;
}
