/**
 * 分段确认工作流 - 类型定义
 */

/**
 * 翻译策略
 */
export type TranslationStrategy = 'preserve' | 'first_annotate' | 'translate' | 'preserve_annotate';

/**
 * 术语条目
 */
export interface GlossaryTerm {
  original: string;
  translation?: string | null;
  strategy: TranslationStrategy;
  note?: string | null;
  tags?: string[] | null;
  first_occurrence?: string | null;
  scope?: 'global' | 'project' | string;
  source?: string | null;
  status?: 'active' | 'disabled' | string;
  updated_at?: string | null;
}

export type GlossaryBatchAction =
  | 'delete'
  | 'set_status'
  | 'set_strategy'
  | 'add_tags'
  | 'replace_tags'
  | 'remove_tags';

export interface SimilarGlossaryTerm {
  original: string;
  translation?: string | null;
  strategy: TranslationStrategy;
  scope: 'global' | 'project' | string;
  note?: string | null;
  similarity: number;
}

export interface TermReviewCandidate {
  term: string;
  suggested_translation: string;
  reasons: string[];
  occurrence_count: number;
  first_occurrence?: string | null;
  related_sections: Array<{
    section_id: string;
    section_title: string;
  }>;
  contexts: string[];
  similar_terms: SimilarGlossaryTerm[];
}

export interface TermReviewSectionGroup {
  section_id: string;
  section_title: string;
  candidates: TermReviewCandidate[];
}

export interface TermReviewPayload {
  project_id: string;
  project_title: string;
  review_required: boolean;
  generated_at: string;
  total_candidates: number;
  sections: TermReviewSectionGroup[];
}

export interface TermReviewDecision {
  term: string;
  action: 'accept' | 'custom' | 'skip';
  translation?: string | null;
  note?: string | null;
  first_occurrence?: string | null;
}

export interface GlossaryRecommendation extends GlossaryTerm {
  usage_count: number;
  section_ids: string[];
  section_titles: Array<{
    section_id: string;
    title: string;
  }>;
  recommended_reason: string;
}

/**
 * 段落信息
 */
export interface Paragraph {
  id: string;
  index: number;
  source: string;
  element_type: string;
  status: string;
  section_id: string;
  section_title: string;
}

/**
 * AI透明度数据
 */
export interface AIInsight {
  overall_score: number;
  is_excellent: boolean;
  applied_terms: string[];
  style: string;
  steps: {
    understand: boolean;
    translate: boolean;
    reflect: boolean;
    refine: boolean;
  };
  understanding?: string;
  scores?: {
    readability: number;
    accuracy: number;
  };
  issues?: Array<{
    type: string;
    description: string;
  }>;
  model?: string;
  created_at?: string;
}

/**
 * 段落版本
 */
export interface ParagraphVersion {
  id: string;
  name: string;
  source_type: 'ai' | 'imported';
  translation: string;
  model?: string;
  created_at: string;
  ai_insight?: AIInsight;
  metadata?: Record<string, unknown>;
}

/**
 * 段落确认状态
 */
export interface ParagraphConfirmation {
  paragraph_id: string;
  selected_version_id?: string;
  custom_translation?: string;
  confirmed_at?: string;
}

/**
 * 段落确认响应
 */
export interface ParagraphConfirmationResponse {
  paragraph: Paragraph;
  versions: ParagraphVersion[];
  current_confirmation: ParagraphConfirmation | null;
  total_paragraphs: number;
}

/**
 * 确认段落请求
 */
export interface ConfirmParagraphRequest {
  translation: string;
  version_id?: string;
  custom_edit?: boolean;
}

/**
 * 确认段落响应
 */
export interface ConfirmParagraphResponse {
  paragraph_id: string;
  translation: string;
  status: string;
  selected_version_id?: string;
  confirmed_at: string;
}

/**
 * 术语变更
 */
export interface TermChange {
  term: string;
  old_translation: string;
  new_translation: string;
}

/**
 * 更新术语请求
 */
export interface UpdateTermsRequest {
  changes: TermChange[];
}

/**
 * 更新术语响应
 */
export interface UpdateTermsResponse {
  updated_count: number;
  terms: TermChange[];
}

/**
 * 导入版本请求
 */
export interface ImportVersionRequest {
  version_name: string;
  markdown_content: string;
}

/**
 * 导入版本响应
 */
export interface ImportVersionResponse {
  version_id: string;
  name: string;
  aligned_count: number;
  unaligned_count: number;
  unaligned_items: UnalignedItem[];
}

/**
 * 未对齐项目
 */
export interface UnalignedItem {
  ref_index: number;
  ref_text: string;
  ref_type: string;
  recommendations: Recommendation[];
}

/**
 * 对齐推荐
 */
export interface Recommendation {
  paragraph_id: string;
  source_preview: string;
  similarity: number;
  element_type: string;
}

/**
 * 手动对齐请求
 */
export interface ManualAlignRequest {
  ref_index: number;
  target_paragraph_id: string;
}

/**
 * 翻译状态
 */
export interface TranslationStatus {
  status: 'processing' | 'completed' | 'failed' | 'cancelled' | 'not_started';
  progress_percent?: number;
  translated_paragraphs?: number;
  total_paragraphs?: number;
  current_section?: string;
  current_step?: string;
  error_count?: number;
  is_complete?: boolean;
  run_id?: string | null;
  final_status?: string | null;
  last_updated_at?: string | null;
  finished_at?: string | null;
  active_project_id?: string | null;
  active_run_id?: string | null;
  can_stop?: boolean;
  is_cancelling?: boolean;
  cancel_requested?: boolean;
}

/**
 * 确认进度
 */
export interface ConfirmationProgress {
  project_id: string;
  status: string;
  total_paragraphs: number;
  translated_paragraphs: number;
  confirmed_paragraphs: number;
  progress_percent: number;
  is_complete: boolean;
}

/**
 * 导出译文响应
 */
export interface ExportTranslationResponse {
  content: string;
  filename: string;
  paragraph_count: number;
}

/**
 * 工作流状态
 */
export type WorkflowStatus = 'loading' | 'translating' | 'ready' | 'complete';

/**
 * 版本卡片属性
 */
export interface VersionCardProps {
  version: ParagraphVersion;
  isSelected: boolean;
  onSelect: (versionId: string) => void;
  onEdit: (version: ParagraphVersion) => void;
}

/**
 * 键盘快捷键
 */
export interface KeyboardShortcuts {
  confirm: string;
  next: string;
  prev: string;
  cancel: string;
}

/**
 * 默认键盘快捷键
 */
export const DEFAULT_SHORTCUTS: KeyboardShortcuts = {
  confirm: 'Ctrl+Enter',
  next: 'Ctrl+ArrowDown',
  prev: 'Ctrl+ArrowUp',
  cancel: 'Escape',
};
