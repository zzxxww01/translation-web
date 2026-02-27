/**
 * Tools React Query hooks.
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { toolsApi } from './api';
import { useToolsStore } from '../../shared/stores';
import { useToast } from '../../components/ui';
import { useErrorHandler } from '../../shared/hooks/useErrorHandler';

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
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: toolsApi.saveTasks,
    onSuccess: () => {
      showSuccess('Tasks saved');
    },
    onError: (error) => {
      handleError(error, 'Save tasks failed');
    },
  });
}

export function useTranslateText() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: toolsApi.translateText,
    onSuccess: () => {
      showSuccess('Translation complete');
    },
    onError: (error) => {
      handleError(error, 'Translation failed');
    },
  });
}

export function useGenerateEmailReply() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: toolsApi.generateEmailReply,
    onSuccess: () => {
      showSuccess('Reply generated');
    },
    onError: (error) => {
      handleError(error, 'Generate reply failed');
    },
  });
}

export function useConvertTimezone() {
  const { showSuccess } = useToast();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: toolsApi.convertTimezone,
    onSuccess: () => {
      showSuccess('Conversion complete');
    },
    onError: (error) => {
      handleError(error, 'Timezone conversion failed');
    },
  });
}
