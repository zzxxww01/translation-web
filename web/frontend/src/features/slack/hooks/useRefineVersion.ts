import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import type { ReplyVersion } from '../types';

interface RefineVersionParams {
  version: string;
  chinese: string;
  style: string;
}

export function useRefineVersion() {
  return useMutation({
    mutationFn: async (params: RefineVersionParams) => {
      const response = await apiClient.post<ReplyVersion>(
        '/slack/refine-version',
        null,
        { params }
      );
      return response.data;
    },
  });
}
