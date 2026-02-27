/**
 * 全局类型定义
 * 统一管理应用中的 TypeScript 类型
 */

import type {
  ParagraphStatus,
  ConversationStyle,
  MessageRole,
  EmailStyle,
  TranslationVersionType,
} from '../constants';

// ============ 项目相关类型 ============

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

// ============ 对话相关类型 ============

export interface Conversation {
  id: string;
  name: string;
  style: ConversationStyle;
  system_prompt?: string;
  is_pinned?: boolean;
  history?: Message[];
}

export interface Message {
  role: MessageRole;
  content_en?: string;
  content_cn?: string;
}

export interface CreateConversationDto {
  id: string;
  name: string;
  style: ConversationStyle;
  system_prompt?: string;
}

export interface AddMessageDto {
  role: MessageRole;
  content_en: string;
  content_cn?: string;
}

export interface ProcessMessageDto {
  message: string;
  conversation_id?: string;
}

export interface ProcessResult {
  translation: string;
  // 三种轻松职场风格的回复建议
  super_casual: string;      // 超随意，像熟朋友
  super_casual_cn: string;
  friendly_pro: string;      // 标准轻松职场
  friendly_pro_cn: string;
  polite_casual: string;     // 稍礼貌（对上级）
  polite_casual_cn: string;
}

export interface ComposeDto {
  content: string;
  conversation_id?: string;
  tone?: string;
}

export interface ComposeResult {
  casual: string;
  professional: string;
  formal: string;
}

// ============ 翻译相关类型 ============

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
}

export interface TranslatePostResult {
  translation: string;
}

export interface OptimizePostDto {
  original_text: string;
  current_translation: string;
  instruction: string;
  conversation_history?: Array<{ role: string; content: string }>;
}

export interface OptimizePostResult {
  optimized_translation: string;
}

export interface GenerateTitleDto {
  content: string;
}

export interface GenerateTitleResult {
  title: string;
}

// ============ 工具相关类型 ============

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
  content: string;
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

// ============ 通用类型 ============

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

// ============ 组件相关类型 ============

export interface BaseComponentProps {
  className?: string;
}

export interface SelectOption<T = string> {
  label: string;
  value: T;
  disabled?: boolean;
}
