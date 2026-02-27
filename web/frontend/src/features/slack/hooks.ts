/**
 * Slack 助手相关的 React Query hooks
 */

import { useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { slackApi } from './api';
import { useSlackStore } from '../../shared/stores';
import { useToast } from '../../components/ui';
import { useErrorHandler } from '../../shared/hooks/useErrorHandler';
import type { AddMessageDto, ProcessMessageDto, ComposeDto } from '../../shared/types';

/**
 * 获取对话列表
 */
export function useConversations() {
  const { setConversations, setCurrentConversation, conversations } = useSlackStore();
  const { handleError } = useErrorHandler();

  // Fetch conversations and auto-select default pinned conversation.
  useEffect(() => {
    let isMounted = true;
    
    const fetchConversations = async () => {
      try {
        const data = await slackApi.getConversations();
        if (!isMounted) return;
        
        setConversations(data);
        
        // Auto-select first pinned conversation if none selected
        const store = useSlackStore.getState();
        if (!store.currentConversation && data.length > 0) {
          const pinned = data.find(c => c.is_pinned);
          if (pinned) {
            const fullConv = await slackApi.getConversation(pinned.id);
            if (isMounted) {
              setCurrentConversation(fullConv);
            }
          }
        }
      } catch (error) {
        if (isMounted) {
          handleError(error, '加载对话列表失败');
        }
      }
    };
    
    fetchConversations();
    
    return () => { isMounted = false; };
  }, [handleError, setConversations, setCurrentConversation]);

  return { data: conversations };
}

/**
 * 创建对话
 */
export function useCreateConversation() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: slackApi.createConversation,
    onSuccess: () => {
      showSuccess('对话创建成功');
    },
    onError: error => {
      handleError(error, '创建对话失败');
    },
  });
}

/**
 * 发送消息
 */
export function useSendMessage() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: ({ conversationId, data }: { conversationId: string; data: AddMessageDto }) =>
      slackApi.addMessage(conversationId, data),
    onSuccess: () => {
      showSuccess('消息已发送');
    },
    onError: error => {
      handleError(error, '发送消息失败');
    },
  });
}

/**
 * 翻译消息
 */
export function useTranslateMessage() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (data: ProcessMessageDto) => slackApi.processMessage(data),
    onSuccess: result => {
      showSuccess('翻译完成');
      return result;
    },
    onError: error => {
      handleError(error, '翻译失败');
    },
  });
}

/**
 * 生成回复建议
 */
export function useGenerateReply() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (data: ProcessMessageDto) => slackApi.processMessage(data),
    onSuccess: result => {
      showSuccess('回复建议已生成');
      return result;
    },
    onError: error => {
      handleError(error, '生成回复失败');
    },
  });
}

/**
 * AI 润色
 */
export function useComposeReply() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (data: ComposeDto) => slackApi.composeReply(data),
    onSuccess: () => {
      showSuccess('AI 润色完成');
    },
    onError: error => {
      handleError(error, 'AI 润色失败');
    },
  });
}

/**
 * 切换消息角色
 */
export function useToggleMessageRole() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: ({
      conversationId,
      messageIndex,
      role,
    }: {
      conversationId: string;
      messageIndex: number;
      role: 'me' | 'them';
    }) => slackApi.toggleMessageRole(conversationId, messageIndex, role),
    onSuccess: () => {
      showSuccess('角色已切换');
    },
    onError: error => {
      handleError(error, '切换角色失败');
    },
  });
}
