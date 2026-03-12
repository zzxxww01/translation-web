/**
 * Shared application constants.
 */

export enum ParagraphStatus {
  PENDING = 'pending',
  TRANSLATING = 'translating',
  TRANSLATED = 'translated',
  REVIEWING = 'reviewing',
  MODIFIED = 'modified',
  APPROVED = 'approved',
}

export const PARAGRAPH_STATUS_ICONS: Record<ParagraphStatus, string> = {
  [ParagraphStatus.PENDING]: '○',
  [ParagraphStatus.TRANSLATING]: '◐',
  [ParagraphStatus.TRANSLATED]: '●',
  [ParagraphStatus.REVIEWING]: '◑',
  [ParagraphStatus.MODIFIED]: '✎',
  [ParagraphStatus.APPROVED]: '✓',
} as const;

export const PARAGRAPH_STATUS_CLASSES: Record<ParagraphStatus, string> = {
  [ParagraphStatus.PENDING]: 'text-text-muted',
  [ParagraphStatus.TRANSLATING]: 'text-warning',
  [ParagraphStatus.TRANSLATED]: 'text-info',
  [ParagraphStatus.REVIEWING]: 'text-warning',
  [ParagraphStatus.MODIFIED]: 'text-warning',
  [ParagraphStatus.APPROVED]: 'text-success',
} as const;

export const PARAGRAPH_STATUS_LABELS: Record<ParagraphStatus, string> = {
  [ParagraphStatus.PENDING]: '待翻译',
  [ParagraphStatus.TRANSLATING]: '翻译中',
  [ParagraphStatus.TRANSLATED]: '已翻译',
  [ParagraphStatus.REVIEWING]: '审核中',
  [ParagraphStatus.MODIFIED]: '已修改',
  [ParagraphStatus.APPROVED]: '已确认',
} as const;

export enum EmailStyle {
  PROFESSIONAL = 'professional',
  POLITE = 'polite',
  CASUAL = 'casual',
}

export const EMAIL_STYLE_LABELS: Record<EmailStyle, string> = {
  [EmailStyle.PROFESSIONAL]: '正式',
  [EmailStyle.POLITE]: '礼貌',
  [EmailStyle.CASUAL]: '随意',
} as const;

export enum TranslationVersionType {
  TRANSLATION = 'translation',
  OPTIMIZATION = 'optimization',
  MANUAL = 'manual',
}

export const TRANSLATION_VERSION_TYPE_LABELS: Record<TranslationVersionType, string> = {
  [TranslationVersionType.TRANSLATION]: '翻译',
  [TranslationVersionType.OPTIMIZATION]: '优化',
  [TranslationVersionType.MANUAL]: '手动编辑',
} as const;

export const API_BASE = '/api';
export const API_TIMEOUT = 30000;
export const API_RETRY_COUNT = 3;
export const API_RETRY_DELAY = 1000;

export const DEFAULT_STALE_TIME = 5 * 60 * 1000;
export const DEFAULT_GC_TIME = 10 * 60 * 1000;

export const TOAST_DURATION = 3000;
export type ToastType = 'success' | 'error' | 'info' | 'warning';

export const STORAGE_KEYS = {
  DOCUMENT_STATE: 'translation_agent_document_state',
  THEME: 'translation_agent_theme',
} as const;

export const ROUTES = {
  HOME: '/',
  DOCUMENT: '/document',
  POST: '/post',
  SLACK: '/slack',
  TOOLS: '/tools',
} as const;

export const DEFAULT_PAGE_SIZE = 20;
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;

export const REQUEST_TIMEOUTS = {
  DEFAULT: API_TIMEOUT,
  POST_TRANSLATE: 180000,
  POST_OPTIMIZE: 180000,
  POST_TITLE: 180000,
  PARAGRAPH_TRANSLATE: 180000,
  PARAGRAPH_BATCH_TRANSLATE: 600000,
  PARAGRAPH_WORD_MEANING: 120000,
} as const;

export enum TranslationMethod {
  NORMAL = 'normal',
  FOUR_STEP = 'four-step',
}

export interface TranslationMethodOption {
  id: TranslationMethod;
  name: string;
  description: string;
  endpoint: string;
}

export const TRANSLATION_METHOD_OPTIONS: TranslationMethodOption[] = [
  {
    id: TranslationMethod.NORMAL,
    name: '普通翻译',
    description: '快速逐段翻译，适合日常使用',
    endpoint: '/translate-stream',
  },
  {
    id: TranslationMethod.FOUR_STEP,
    name: '四步法翻译',
    description: '深度分析、反思和润色，适合高质量需求',
    endpoint: '/translate-four-step',
  },
];

export const DEFAULT_TRANSLATION_METHOD = TranslationMethod.FOUR_STEP;
