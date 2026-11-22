import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { toolsApi } from './api';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';

export function useTranslateText() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: toolsApi.translateText,
    onSuccess: () => {
      toast.success('翻译完成');
    },
    onError: (error) => {
      handleError(error, 'Translation failed');
    },
  });
}

export function useGenerateEmailReply() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: toolsApi.generateEmailReply,
    onSuccess: () => {
      toast.success('回复已生成');
    },
    onError: (error) => {
      handleError(error, 'Generate reply failed');
    },
  });
}

export function useConvertTimezone() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: toolsApi.convertTimezone,
    onSuccess: () => {
      toast.success('转换完成');
    },
    onError: (error) => {
      handleError(error, 'Timezone conversion failed');
    },
  });
}
