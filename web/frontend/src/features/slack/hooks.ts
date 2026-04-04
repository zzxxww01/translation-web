import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import type { ComposeDto, ProcessMessageDto } from '@/shared/types';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';
import { slackApi } from './api';

export function useGenerateReply() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (data: ProcessMessageDto) => slackApi.processMessage(data),
    onSuccess: () => {
      toast.success('建议回复已生成');
    },
    onError: error => {
      handleError(error, '生成建议回复失败');
    },
  });
}

export function useComposeReply() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (data: ComposeDto) => slackApi.composeReply(data),
    onSuccess: () => {
      toast.success('英文版本已生成');
    },
    onError: error => {
      handleError(error, '中译英失败');
    },
  });
}
