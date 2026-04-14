/**
 * 质量报告 - API 客户端
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../shared/api/client';
import type { ProjectQualityReport, SectionQualityReport } from './types';

/**
 * 获取项目质量报告
 */
export function useProjectQualityReport(projectId: string) {
  return useQuery({
    queryKey: ['quality-report', projectId],
    queryFn: async () => {
      return apiClient.get<ProjectQualityReport>(`/projects/${projectId}/quality-report`);
    },
    enabled: !!projectId,
    staleTime: 2 * 60 * 1000, // 2 分钟
  });
}

/**
 * 获取章节质量报告
 */
export function useSectionQualityReport(projectId: string, sectionId: string) {
  return useQuery({
    queryKey: ['quality-report', projectId, sectionId],
    queryFn: async () => {
      return apiClient.get<SectionQualityReport>(
        `/projects/${projectId}/sections/${sectionId}/quality-report`
      );
    },
    enabled: !!projectId && !!sectionId,
    staleTime: 2 * 60 * 1000, // 2 分钟
  });
}
