/**
 * 共享工具函数
 */

import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * 合并className的工具函数
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * 检测语言类型
 */
export function detectLanguage(text: string): 'zh' | 'en' | 'mixed' {
  const hasEnglish = /[a-zA-Z]/.test(text);
  const hasChinese = /[\u4e00-\u9fff]/.test(text);
  if (hasEnglish && hasChinese) return 'mixed';
  if (hasChinese) return 'zh';
  return 'en';
}

/**
 * 输入类型检测
 */
export function detectInputType(text: string): 'question' | 'command' | 'text' {
  if (text.endsWith('?')) return 'question';
  if (text.startsWith('/')) return 'command';
  return 'text';
}

/**
 * 意图检测
 */
export type IntentType = 'translate' | 'reply' | 'compose' | 'record';

export function detectIntent(text: string): IntentType {
  if (text.includes('翻译')) return 'translate';
  if (text.includes('回复')) return 'reply';
  if (text.includes('记录')) return 'record';
  return 'compose';
}

/**
 * 智能输入状态
 */
export type SmartInputState = {
  content: string;
  detectedLanguage: string;
  detectedIntent: string;
  suggestedActions: SmartAction[];
  previewResult?: unknown;
};

/**
 * 智能操作
 */
export type SmartAction = {
  id: string;
  label: string;
  action: () => void;
};

/**
 * 对话上下文
 */
export type ConversationContext = {
  lastMessage?: string;
  language?: 'zh' | 'en' | 'mixed';
  intent?: IntentType;
  lastMessageRole?: 'me' | 'them';
  recentMessages?: Array<{ role: 'me' | 'them'; content: string }>;
  conversationLength?: number;
};

/**
 * 计算可用操作
 */
export function computeAvailableActions(
  _inputType: string,
  _context: ConversationContext
): SmartAction[] {
  return [];
}

/**
 * 防抖函数
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(() => func(...args), wait);
  };
}

/**
 * 复制到剪贴板
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/**
 * 获取字符数量
 */
export function getCharCount(text: string): number {
  return text.length;
}

let idCounter = 0;

/**
 * 生成稳定唯一ID
 */
export function generateId(prefix = 'id'): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`;
  }

  idCounter += 1;
  return `${prefix}-${idCounter}`;
}
