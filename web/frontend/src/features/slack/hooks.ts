import { useMutation } from '@tanstack/react-query';
import type { ComposeDto, ProcessMessageDto } from '../../shared/types';
import { useToast } from '../../components/ui';
import { useErrorHandler } from '../../shared/hooks/useErrorHandler';
import { slackApi } from './api';

export function useGenerateReply() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (data: ProcessMessageDto) => slackApi.processMessage(data),
    onSuccess: result => {
      showSuccess('建议回复已生成');
      return result;
    },
    onError: error => {
      handleError(error, '生成建议回复失败');
    },
  });
}

export function useComposeReply() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: (data: ComposeDto) => slackApi.composeReply(data),
    onSuccess: () => {
      showSuccess('英文版本已生成');
    },
    onError: error => {
      handleError(error, '中译英失败');
    },
  });
}
