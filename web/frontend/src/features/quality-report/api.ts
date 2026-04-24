/**
 * 质量报告 - API 客户端
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../shared/api/client';
import {
  normalizeScore,
  toQualityIssue,
  type ProjectQualityReport,
  type SectionQualityReport,
  type TranslationIssueDTO,
} from './types';

const REPORT_REQUEST_OPTIONS = { timeout: 8000, retry: false };

interface BackendSectionQualityScore {
  section_id: string;
  section_title: string;
  overall_score: number;
  readability_score: number;
  accuracy_score: number;
  conciseness_score: number;
  is_excellent: boolean;
  issue_count: number;
  auto_fixed_count: number;
  manual_review_count: number;
  paragraph_count: number;
}

interface BackendProjectQualityReport {
  run_id: string;
  project_id: string;
  timestamp: string;
  overall_score: number;
  sections: BackendSectionQualityScore[];
  total_issues: number;
  auto_fixed_issues: number;
  manual_review_issues: number;
  consistency_stats?: Record<string, unknown>;
}

interface BackendSectionQualityReport {
  section_id: string;
  section_title: string;
  overall_score: number;
  readability_score: number;
  accuracy_score: number;
  conciseness_score: number;
  is_excellent: boolean;
  issues: TranslationIssueDTO[];
  revision_count: number;
}

function mapSection(section: BackendSectionQualityScore): SectionQualityReport {
  return {
    section_id: section.section_id,
    section_title: section.section_title,
    overall_score: normalizeScore(section.overall_score),
    readability_score: normalizeScore(section.readability_score),
    accuracy_score: normalizeScore(section.accuracy_score),
    conciseness_score: normalizeScore(section.conciseness_score),
    is_excellent: section.is_excellent,
    issues: [],
    issue_count: section.issue_count,
    revision_count: section.auto_fixed_count > 0 ? 1 : 0,
  };
}

function mapSectionDetails(section: BackendSectionQualityReport): SectionQualityReport {
  return {
    section_id: section.section_id,
    section_title: section.section_title,
    overall_score: normalizeScore(section.overall_score),
    readability_score: normalizeScore(section.readability_score),
    accuracy_score: normalizeScore(section.accuracy_score),
    conciseness_score: normalizeScore(section.conciseness_score),
    is_excellent: section.is_excellent,
    issues: section.issues.map(toQualityIssue),
    issue_count: section.issues.length,
    revision_count: section.revision_count,
  };
}

function mapProjectReport(report: BackendProjectQualityReport): ProjectQualityReport {
  return {
    project_id: report.project_id,
    project_title: report.project_id,
    overall_score: normalizeScore(report.overall_score),
    total_issues: report.total_issues,
    issues_by_status: {
      auto_fixed: report.auto_fixed_issues,
      pending: report.manual_review_issues,
      manual_fixed: 0,
      dismissed: 0,
    },
    issues_by_severity: {
      critical: 0,
      major: 0,
      minor: 0,
    },
    sections: report.sections.map(mapSection),
    generated_at: report.timestamp,
  };
}

/**
 * 获取项目质量报告
 */
export function useProjectQualityReport(projectId: string) {
  return useQuery({
    queryKey: ['quality-report', projectId],
    queryFn: async () => {
      const report = await apiClient.get<BackendProjectQualityReport>(
        `/quality-report/projects/${projectId}/quality-report`,
        REPORT_REQUEST_OPTIONS
      );
      return mapProjectReport(report);
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
      const section = await apiClient.get<BackendSectionQualityReport>(
        `/quality-report/projects/${projectId}/sections/${sectionId}/quality-report`,
        REPORT_REQUEST_OPTIONS
      );
      return mapSectionDetails(section);
    },
    enabled: !!projectId && !!sectionId,
    staleTime: 2 * 60 * 1000, // 2 分钟
  });
}
