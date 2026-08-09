import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/shared/api/client';
import { REQUEST_TIMEOUTS } from '@/shared/constants';
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
        undefined,
        {
          params: {
            version: params.version,
            chinese: params.chinese,
            style: params.style,
          },
          timeout: REQUEST_TIMEOUTS.SHORT_FORM_LLM,
          retry: false,
        }
      );
      return response;
    },
  });
}
