import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { toast } from 'sonner';
import { toolsApi } from './api';
import { useToolsStore } from '@/shared/stores';
import { useErrorHandler } from '@/shared/hooks/useErrorHandler';

export function useLoadTasks() {
  const { setTasks } = useToolsStore();
  const { handleError } = useErrorHandler();

  const query = useQuery({
    queryKey: ['tools', 'tasks'],
    queryFn: toolsApi.getTasks,
  });

  useEffect(() => {
    if (query.data) {
      setTasks(query.data);
    }
  }, [query.data, setTasks]);

  useEffect(() => {
    if (query.error) {
      handleError(query.error, 'Load tasks failed');
    }
  }, [query.error, handleError]);

  return query;
}

export function useSaveTasks() {
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: toolsApi.saveTasks,
    onSuccess: () => {
      toast.success('任务已保存');
    },
    onError: (error) => {
      handleError(error, 'Save tasks failed');
    },
  });
}

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
