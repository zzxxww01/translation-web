/**
 * 质量报告 - 类型定义
 */

// 后端原始类型（与后端完全匹配）
export interface TranslationIssueDTO {
  paragraph_index: number;
  issue_type: string;
  severity: 'low' | 'medium' | 'high';
  original_text: string;
  description: string;
  why_it_matters: string;
  suggestion: string;
  auto_fixed: boolean;
  revised_text?: string;
  fix_method?: string;
}

// 前端视图模型
export interface QualityIssue {
  id: string;
  type: 'accuracy' | 'readability' | 'terminology' | 'consistency' | 'style';
  severity: 'critical' | 'major' | 'minor';
  paragraph_index: number;
  source_text: string;
  translation_text: string;
  description: string;
  suggestion?: string;
  status: 'pending' | 'auto_fixed' | 'manual_fixed' | 'dismissed';
  fixed_text?: string;
  why_it_matters: string;
}

export interface SectionQualityReport {
  section_id: string;
  section_title: string;
  overall_score: number;
  readability_score: number;
  accuracy_score: number;
  conciseness_score: number;
  is_excellent: boolean;
  issues: QualityIssue[];
  revision_count: number;
  final_assessment?: {
    passed: boolean;
    overall_score: number;
    failed_criteria: string[];
  };
}

export interface ProjectQualityReport {
  project_id: string;
  project_title: string;
  overall_score: number;
  total_issues: number;
  issues_by_status: Record<string, number>;
  issues_by_severity: Record<string, number>;
  sections: SectionQualityReport[];
  generated_at: string;
}

export type IssueType = QualityIssue['type'];
export type IssueSeverity = QualityIssue['severity'];
export type IssueStatus = QualityIssue['status'];
export type SortBy = 'severity' | 'type' | 'paragraph';

// 映射函数
export function mapSeverity(severity: string): 'critical' | 'major' | 'minor' {
  switch (severity) {
    case 'high': return 'critical';
    case 'medium': return 'major';
    case 'low': return 'minor';
    default: return 'minor';
  }
}

export function toQualityIssue(dto: TranslationIssueDTO, index: number): QualityIssue {
  return {
    id: `issue-${dto.paragraph_index}-${index}`,
    type: dto.issue_type as QualityIssue['type'],
    severity: mapSeverity(dto.severity),
    paragraph_index: dto.paragraph_index,
    source_text: dto.original_text,
    translation_text: '', // 需要从其他地方获取
    description: dto.description,
    suggestion: dto.suggestion,
    status: dto.auto_fixed ? 'auto_fixed' : 'pending',
    fixed_text: dto.revised_text,
    why_it_matters: dto.why_it_matters,
  };
}
