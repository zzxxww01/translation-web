import { useEffect, useState } from 'react';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';
import { slackInboxApi } from './api';
import type { SlackConversationList } from './types';

// 后端对 client.counts 缓存 30 秒；会话和消息接口限额约 50 次/分钟，thread 列表轮询放慢一些
const POLL_MS = 30_000;
// 读接口失败时自动再试两次（经隧道偶尔会断一下），还不行再在页面上报错
const READ_RETRY = 2;

export const slackInboxKeys = {
  status: ['slack-inbox', 'status'] as const,
  conversations: ['slack-inbox', 'conversations'] as const,
  messages: (channelId: string) => ['slack-inbox', 'messages', channelId] as const,
  replies: (channelId: string, threadTs: string) => ['slack-inbox', 'replies', channelId, threadTs] as const,
  threads: ['slack-inbox', 'threads'] as const,
  activity: ['slack-inbox', 'activity'] as const,
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
    retry: READ_RETRY,
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
    retry: READ_RETRY,
  });
}

export function useSlackReplies(channelId: string, threadTs: string, enabled = true) {
  return useQuery({
    queryKey: slackInboxKeys.replies(channelId, threadTs),
    queryFn: () => slackInboxApi.replies(channelId, threadTs),
    enabled,
    refetchInterval: POLL_MS,
    staleTime: 20_000,
    retry: READ_RETRY,
  });
}

/** 「动态」列表：频道 thread 和私信，按最近活动排序。 */
export function useSlackActivity(enabled: boolean) {
  return useQuery({
    queryKey: slackInboxKeys.activity,
    queryFn: slackInboxApi.activity,
    enabled,
    refetchInterval: POLL_MS,
    staleTime: 20_000,
    retry: READ_RETRY,
    select: data => data.items,
  });
}

/** 看过就记为已读——只记在翻译服务本地，不改 Slack（只往前推，后端不会往回退）。先本地清掉未读标记，界面立即生效。 */
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
      void queryClient.invalidateQueries({ queryKey: slackInboxKeys.activity });
      void queryClient.invalidateQueries({ queryKey: ['slack-inbox', 'todos'] });
      void queryClient.invalidateQueries({ queryKey: slackInboxKeys.conversations });
    },
  });
}

export function useMarkAllRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (items?: Parameters<typeof slackInboxApi.markAllRead>[0]) => slackInboxApi.markAllRead(items),
    onSuccess: (_data, items) => {
      toast.success(`${items ? '' : '全部'}已标为已读（只在这里，Slack 里的未读不变）`);
      void queryClient.invalidateQueries({ queryKey: ['slack-inbox'] });
    },
    onError: error => toast.error(error instanceof Error ? error.message : '没标成功'),
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

/** 我的待办（未读的 @我 和私信，后端一次模型调用，按这批消息缓存） */
export function useTodos(enabled: boolean) {
  return useQuery({
    queryKey: ['slack-inbox', 'todos'],
    queryFn: slackInboxApi.todos,
    enabled,
    staleTime: 60_000,
    refetchInterval: 120_000,
    retry: 1,
  });
}

export function useSlackSettings() {
  return useQuery({ queryKey: ['slack-inbox', 'settings'], queryFn: slackInboxApi.settings, staleTime: 5 * 60_000 });
}

export function useSaveSlackSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: slackInboxApi.saveSettings,
    onSuccess: data => queryClient.setQueryData(['slack-inbox', 'settings'], data),
    onError: error => toast.error(error instanceof Error ? error.message : '设置没存上'),
  });
}
