import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * 合并 Tailwind CSS 类名
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 截断文本
 */
export function truncate(text: string, maxLength: number): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
}

/**
 * 复制到剪贴板
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    console.error('Copy failed:', err);
    return false;
  }
}

/**
 * 格式化日期
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
}

/**
 * 格式化时间
 */
export function formatTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * 格式化日期时间
 */
export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}

/**
 * 节流函数
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;

  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * 检测文本语言
 */
export function detectLanguage(text: string): 'zh' | 'en' | 'unknown' {
  const chineseRegex = /[\u4e00-\u9fa5]/;
  const englishRegex = /[a-zA-Z]/;

  const hasChinese = chineseRegex.test(text);
  const hasEnglish = englishRegex.test(text);

  if (hasChinese && !hasEnglish) return 'zh';
  if (hasEnglish && !hasChinese) return 'en';
  if (hasChinese && hasEnglish) {
    // 计算中文字符比例
    const chineseCount = (text.match(chineseRegex) || []).length;
    const englishCount = (text.match(englishRegex) || []).length;
    return chineseCount > englishCount ? 'zh' : 'en';
  }

  return 'unknown';
}


/**
 * 增强版语言检测 - 支持混合语言
 */
export function detectInputType(text: string): 'english' | 'chinese' | 'mixed' {
  const zhRatio = (text.match(/[\u4e00-\u9fa5]/g) || []).length / text.length;
  const enRatio = (text.match(/[a-zA-Z]/g) || []).length / text.length;

  if (zhRatio > 0.6) return 'chinese';
  if (enRatio > 0.6) return 'english';
  return 'mixed';
}


/**
 * 智能意图检测
 */
export interface ConversationContext {
  lastMessageRole?: 'me' | 'them';
  recentMessages?: Array<{ role: 'me' | 'them'; content: string }>;
  conversationLength?: number;
}

export type IntentType = 'reply' | 'record' | 'compose' | 'translate';

export function detectIntent(text: string, context?: ConversationContext): IntentType {
  // 回复意图: 肯定词、情感词、时间承诺
  const replyPatterns = /^(好|行|可以|我会|我来|明白|收到|sure|yes|okay|ok|got it|will do)/i;

  // 记录意图: 第三人称、过去时态
  const recordPatterns = /(他说|她说|刚才|会议中|提到|他们|她们|said|mentioned|told me|in the meeting)/i;

  // 翻译意图: 需要翻译的明显标志
  const translatePatterns = /(翻译|translate|how do you say|怎么说)/i;

  if (translatePatterns.test(text)) return 'translate';
  if (replyPatterns.test(text)) return 'reply';
  if (recordPatterns.test(text)) return 'record';

  // 基于上下文判断
  if (context?.lastMessageRole === 'them') return 'reply';

  return 'compose';
}


/**
 * 智能操作建议生成
 */
export interface SmartAction {
  id: string;
  label: string;
  description: string;
  icon: string;
  primary?: boolean;
  requiresTarget?: boolean;
}

export interface SmartInputState {
  content: string;
  detectedLanguage: 'zh' | 'en' | 'mixed';
  detectedIntent: IntentType;
  suggestedActions: SmartAction[];
  previewResult?: unknown;
}

export function computeAvailableActions(inputState: SmartInputState, _context?: ConversationContext): SmartAction[] {
  const { content, detectedLanguage, detectedIntent } = inputState;
  const actions: SmartAction[] = [];

  // 基于语言和意图生成动作
  if (detectedLanguage === 'zh') {
    // 中文输入
    if (detectedIntent === 'reply') {
      actions.push({
        id: 'translate-and-reply',
        label: '翻译并回复',
        description: '将中文翻译成英文并发送',
        icon: '🔄',
        primary: true
      });
    } else {
      actions.push({
        id: 'translate-to-english',
        label: '翻译为英文',
        description: '翻译成英文',
        icon: '🌐',
        primary: true
      });
    }
    actions.push({
      id: 'send-chinese-directly',
      label: '直接发送中文',
      description: '记录中文内容',
      icon: '📝'
    });
  } else if (detectedLanguage === 'en') {
    // 英文输入
    actions.push({
      id: 'send-english-directly',
      label: '发送英文',
      description: '直接发送英文内容',
      icon: '📤',
      primary: true
    });
    actions.push({
      id: 'translate-to-chinese',
      label: '翻译为中文',
      description: '翻译成中文查看',
      icon: '🌐'
    });
  } else if (detectedLanguage === 'mixed') {
    // 混合语言
    actions.push({
      id: 'optimize-expression',
      label: '优化表达',
      description: '优化成单一语言表达',
      icon: '✨',
      primary: true
    });
    actions.push({
      id: 'translate-to-english',
      label: '翻译为英文',
      description: '统一翻译为英文',
      icon: '🌐'
    });
    actions.push({
      id: 'translate-to-chinese',
      label: '翻译为中文',
      description: '统一翻译为中文',
      icon: '🌏'
    });
  }

  // 基于意图添加额外动作
  if (detectedIntent === 'record') {
    actions.push({
      id: 'record-their-message',
      label: '记录对方消息',
      description: '以对方身份记录消息',
      icon: '👤'
    });
  }

  // 通用动作
  if (content.length > 10) {
    actions.push({
      id: 'optimize-tone',
      label: '优化语调',
      description: '调整语气更适合职场',
      icon: '🎯'
    });
  }

  return actions;
}


/**
 * 预览动作结果
 */
export interface PreviewResult {
  actionId: string;
  previewText: string;
  confidence?: number;
  improvements?: string[];
}

export async function previewSmartAction(
  _actionId: string,
  _inputState: SmartInputState,
  _apiClient?: unknown
): Promise<PreviewResult | null> {
  // 这里是预览逻辑的占位符
  // 实际实现时会调用相应的API
  return null;
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

/**
 * 生成随机 ID
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 深度克隆对象
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') return obj;
  if (obj instanceof Date) return new Date(obj.getTime()) as T;
  if (obj instanceof Array) return obj.map(item => deepClone(item)) as T;

  const clonedObj = {} as T;
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      clonedObj[key] = deepClone(obj[key]);
    }
  }
  return clonedObj;
}

/**
 * 睡眠函数
 */
export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 获取字符计数（中文字符算2个，英文字符算1个）
 */
export function getCharCount(text: string): number {
  let count = 0;
  for (const char of text) {
    if (/[\u4e00-\u9fa5]/.test(char)) {
      count += 2;
    } else {
      count += 1;
    }
  }
  return count;
}

/**
 * 本地存储工具
 */
export const storage = {
  get<T>(key: string, defaultValue?: T): T | null {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue ?? null;
    } catch {
      return defaultValue ?? null;
    }
  },

  set<T>(key: string, value: T): void {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.error('Failed to save to localStorage:', e);
    }
  },

  remove(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch (e) {
      console.error('Failed to remove from localStorage:', e);
    }
  },

  clear(): void {
    try {
      localStorage.clear();
    } catch (e) {
      console.error('Failed to clear localStorage:', e);
    }
  },
};
