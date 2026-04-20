/**
 * 閸忋劌鐪猾璇茬€风€规矮绠?
 * 缂佺喍绔寸粻锛勬倞鎼存梻鏁ゆ稉顓犳畱 TypeScript 缁鐎?
 */

import type {
  ParagraphStatus,
  EmailStyle,
  TranslationVersionType,
} from '../constants';

// ============ 妞ゅ湱娲伴惄绋垮彠缁鐎?============

export interface Project {
  id: string;
  title: string;
  html_path?: string;
  sections?: Section[];
  progress?: ProjectProgress;
  status?: string;
  created_at?: string;
}

export interface ProjectProgress {
  total?: number;
  total_sections?: number;
  total_paragraphs?: number;
  approved: number;
  percent: number;
}

export interface Section {
  section_id: string;
  title: string;
  title_translation?: string;
  is_complete: boolean;
  total_paragraphs: number;
  approved_count: number;
  paragraphs?: Paragraph[];
}

export interface Paragraph {
  id: string;
  index: number;
  source: string;
  source_html?: string | null;
  element_type?: string;
  translation?: string;
  status: ParagraphStatus;
  confirmed?: string;
}

export interface CreateProjectDto {
  name: string;
  html_path: string;
}

export interface AnalysisResult {
  summary: string;
  notes: string[];
  key_terms: string[];
}

export interface SectionAnalysis {
  summary: string;
  tips: string[];
}

// ============ 鐎电鐦介惄绋垮彠缁鐎?============

export type MessageRole = 'them' | 'me';

export interface ConversationMessage {
  id: string;  // UUID for React key
  role: MessageRole;
  content: string;
  timestamp: number;
}

export interface ProcessMessageDto {
  message: string;
  conversation_history?: ConversationMessage[];
}

export interface SlackReplyVariant {
  version: string;
  english: string;
  chinese?: string;
  style?: string;
}

export interface ProcessResult {
  translation: string;
  suggested_replies: SlackReplyVariant[];
}

export interface ComposeDto {
  content: string;
  conversation_history?: ConversationMessage[];
}

export interface ComposeResult {
  versions: SlackReplyVariant[];
}

// ============ 缂堟槒鐦ч惄绋垮彠缁鐎?============

export interface TranslationVersion {
  id: string;
  versionNumber: number;
  content: string;
  type: TranslationVersionType;
  instruction?: string;
  isCurrent: boolean;
  createdAt: Date;
}

export interface TranslatePostDto {
  content: string;
  model?: string;
}

export interface TranslatePostResult {
  translation: string;
}

export interface OptimizePostDto {
  original_text: string;
  current_translation: string;
  instruction?: string;
  option_id?: string;
  conversation_history?: Array<{ role: string; content: string }>;
  model?: string;
}

export interface OptimizePostResult {
  optimized_translation: string;
}

export interface GenerateTitleDto {
  content: string;
  instruction?: string;
  model?: string;
}

export interface GenerateTitleResult {
  title: string;
}

// ============ 瀹搞儱鍙块惄绋垮彠缁鐎?============

export interface Task {
  id: string;
  text: string;
  completed: boolean;
}

export interface TranslateTextDto {
  text: string;
  source_lang: string;
  target_lang: string;
}

export interface TranslateTextResult {
  translation: string;
}

export interface EmailReplyDto {
  sender?: string;
  subject?: string;
  content: string;
  style: EmailStyle;
}

export interface EmailReply {
  type: string;
  content_en: string;
  content_zh: string;
}

export interface EmailReplyResult {
  replies: EmailReply[];
}

export interface TimezoneConvertDto {
  input: string;
  source_timezone: string;
}

export interface TimezoneConvertResult {
  est: string;
  cst: string;
  mst: string;
  pst: string;
  beijing: string;
  original: string;
}

// ============ 闁氨鏁ょ猾璇茬€?============

export interface ApiError {
  detail: string;
  status?: number;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
}

// ============ 缂佸嫪娆㈤惄绋垮彠缁鐎?============

export interface BaseComponentProps {
  className?: string;
}

export interface SelectOption<T = string> {
  label: string;
  value: T;
  disabled?: boolean;
}

// ============ LLM Model Types ============

export interface ModelInfo {
  alias: string;
  name: string;
  description: string;
  supports_thinking: boolean;
  priority: number;
  available: boolean;
}

export interface ProviderInfo {
  id: string;
  name: string;
  description: string;
  models: ModelInfo[];
}

export interface ModelListResponse {
  providers: ProviderInfo[];
}

// Legacy flat model list (for backward compatibility)
export interface LegacyModelInfo {
  alias: string;
  provider: string;
  real_model: string;
  description: string;
  supports_thinking: boolean;
}

export interface LegacyModelListResponse {
  models: LegacyModelInfo[];
}
