/**
 * 全局常量定义
 * 集中管理应用中的常量，避免硬编码和重复定义
 */

// ============ 段落状态相关 ============

/**
 * 段落状态枚举
 * 注意：后端返回的是小写值，需要保持一致
 */
export enum ParagraphStatus {
  PENDING = 'pending',
  TRANSLATING = 'translating',
  TRANSLATED = 'translated',
  REVIEWING = 'reviewing',
  MODIFIED = 'modified',
  APPROVED = 'approved',
}

/**
 * 段落状态对应的图标
 */
export const PARAGRAPH_STATUS_ICONS: Record<ParagraphStatus, string> = {
  [ParagraphStatus.PENDING]: '○',
  [ParagraphStatus.TRANSLATING]: '⏳',
  [ParagraphStatus.TRANSLATED]: '📝',
  [ParagraphStatus.REVIEWING]: '👀',
  [ParagraphStatus.MODIFIED]: '✏️',
  [ParagraphStatus.APPROVED]: '✓',
} as const;

/**
 * 段落状态对应的 CSS 类名
 */
export const PARAGRAPH_STATUS_CLASSES: Record<ParagraphStatus, string> = {
  [ParagraphStatus.PENDING]: 'text-text-muted',
  [ParagraphStatus.TRANSLATING]: 'text-warning',
  [ParagraphStatus.TRANSLATED]: 'text-info',
  [ParagraphStatus.REVIEWING]: 'text-warning',
  [ParagraphStatus.MODIFIED]: 'text-warning',
  [ParagraphStatus.APPROVED]: 'text-success',
} as const;

/**
 * 段落状态对应的显示文本
 */
export const PARAGRAPH_STATUS_LABELS: Record<ParagraphStatus, string> = {
  [ParagraphStatus.PENDING]: '待翻译',
  [ParagraphStatus.TRANSLATING]: '翻译中',
  [ParagraphStatus.TRANSLATED]: '已翻译',
  [ParagraphStatus.REVIEWING]: '审阅中',
  [ParagraphStatus.MODIFIED]: '已修改',
  [ParagraphStatus.APPROVED]: '已确认',
} as const;

// ============ 对话风格相关 ============

/**
 * 对话风格枚举
 */
export enum ConversationStyle {
  CASUAL = 'casual',
  PROFESSIONAL = 'professional',
}

/**
 * 对话风格对应的显示文本
 */
export const CONVERSATION_STYLE_LABELS: Record<ConversationStyle, string> = {
  [ConversationStyle.CASUAL]: '轻松随意',
  [ConversationStyle.PROFESSIONAL]: '正式商务',
} as const;

// ============ 消息角色相关 ============

/**
 * 消息角色枚举
 */
export enum MessageRole {
  ME = 'me',
  THEM = 'them',
}

/**
 * 消息角色对应的显示文本
 */
export const MESSAGE_ROLE_LABELS: Record<MessageRole, string> = {
  [MessageRole.ME]: '我',
  [MessageRole.THEM]: '对方',
} as const;

// ============ 邮件风格相关 ============

/**
 * 邮件回复风格枚举
 */
export enum EmailStyle {
  PROFESSIONAL = 'professional',
  POLITE = 'polite',
  CASUAL = 'casual',
}

/**
 * 邮件风格对应的显示文本
 */
export const EMAIL_STYLE_LABELS: Record<EmailStyle, string> = {
  [EmailStyle.PROFESSIONAL]: '正式',
  [EmailStyle.POLITE]: '礼貌',
  [EmailStyle.CASUAL]: '随意',
} as const;

// ============ 翻译版本类型相关 ============

/**
 * 翻译版本类型枚举
 */
export enum TranslationVersionType {
  TRANSLATION = 'translation',
  OPTIMIZATION = 'optimization',
  MANUAL = 'manual',
}

/**
 * 翻译版本类型对应的显示文本
 */
export const TRANSLATION_VERSION_TYPE_LABELS: Record<TranslationVersionType, string> = {
  [TranslationVersionType.TRANSLATION]: '翻译',
  [TranslationVersionType.OPTIMIZATION]: '优化',
  [TranslationVersionType.MANUAL]: '手动编辑',
} as const;

// ============ API 相关 ============

/**
 * API 基础路径
 */
export const API_BASE = '/api';

/**
 * API 请求超时时间（毫秒）
 */
export const API_TIMEOUT = 30000;

/**
 * API 重试次数
 */
export const API_RETRY_COUNT = 3;

/**
 * API 重试延迟（毫秒）
 */
export const API_RETRY_DELAY = 1000;

// ============ React Query 相关 ============

/**
 * 默认的缓存时间（毫秒）
 */
export const DEFAULT_STALE_TIME = 5 * 60 * 1000; // 5 分钟

/**
 * 默认的 GC 时间（毫秒）
 */
export const DEFAULT_GC_TIME = 10 * 60 * 1000; // 10 分钟

// ============ Toast 消息相关 ============

/**
 * Toast 消息持续时间（毫秒）
 */
export const TOAST_DURATION = 3000;

/**
 * Toast 类型
 */
export type ToastType = 'success' | 'error' | 'info' | 'warning';

// ============ 本地存储相关 ============

/**
 * 本地存储键名
 */
export const STORAGE_KEYS = {
  CONVERSATIONS: 'translation_agent_conversations',
  CURRENT_CONVERSATION: 'translation_agent_current_conversation',
  DOCUMENT_STATE: 'translation_agent_document_state',
  THEME: 'translation_agent_theme',
} as const;

// ============ 路由相关 ============

/**
 * 应用路由路径
 */
export const ROUTES = {
  HOME: '/',
  DOCUMENT: '/document',
  POST: '/post',
  SLACK: '/slack',
  TOOLS: '/tools',
} as const;

// ============ 分页相关 ============

/**
 * 默认分页大小
 */
export const DEFAULT_PAGE_SIZE = 20;

/**
 * 分页大小选项
 */
export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;


// ============ Request timeout config (ms) ============

export const REQUEST_TIMEOUTS = {
  DEFAULT: API_TIMEOUT,
  POST_TRANSLATE: 180000,
  POST_OPTIMIZE: 180000,
  POST_TITLE: 180000,
} as const;

// ============ 翻译模型相关 ============

/**
 * 翻译模型选项
 */
export interface ModelOption {
  id: string;
  name: string;
  description: string;
}

/**
 * 可用的翻译模型列表
 */
export const MODEL_OPTIONS: ModelOption[] = [
  {
    id: 'preview',
    name: 'Gemini Preview',
    description: '前沿能力模型，质量优先',
  },
  {
    id: 'pro',
    name: 'Gemini Pro',
    description: '通用主力模型，质量与速度平衡',
  },
  {
    id: 'flash',
    name: 'Gemini Flash',
    description: '快速低成本模型，适合批量场景',
  },
];

/**
 * 默认翻译模型
 */
export const DEFAULT_MODEL = 'pro';

// ============ 翻译方法相关 ============

/**
 * 翻译方法枚举
 */
export enum TranslationMethod {
  NORMAL = 'normal',
  FOUR_STEP = 'four-step',
}

/**
 * 翻译方法选项接口
 */
export interface TranslationMethodOption {
  id: TranslationMethod;
  name: string;
  description: string;
  endpoint: string;
}

/**
 * 可用的翻译方法列表
 */
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
    description: '深度分析+反思润色，适合高质量需求',
    endpoint: '/translate-four-step',
  },
];

/**
 * 默认翻译方法
 */
export const DEFAULT_TRANSLATION_METHOD = TranslationMethod.NORMAL;
