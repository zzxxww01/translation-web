/**
 * 分段确认工作流 - 实用工具函数
 */

/**
 * 格式化日期时间
 */
export function formatDateTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  // 小于1分钟
  if (diff < 60000) {
    return '刚刚';
  }

  // 小于1小时
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000);
    return `${minutes}分钟前`;
  }

  // 小于24小时
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours}小时前`;
  }

  // 小于7天
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000);
    return `${days}天前`;
  }

  // 其他情况显示完整日期
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * 计算进度百分比
 */
export function calculateProgress(current: number, total: number): number {
  if (total === 0) return 0;
  return Math.round((current / total) * 100);
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

/**
 * 截断文本
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

/**
 * 高亮文本中的术语
 */
export function highlightTerms(
  text: string,
  terms: Array<{ original: string; translation: string }>
): string {
  let result = text;

  terms.forEach(term => {
    const regex = new RegExp(`(${term.original})`, 'gi');
    result = result.replace(
      regex,
      `<mark class="bg-primary/20 text-primary rounded px-0.5">$1</mark>`
    );
  });

  return result;
}

/**
 * 生成唯一ID
 */
export function generateId(prefix = 'id'): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * 深度克隆对象
 */
export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }

  if (obj instanceof Date) {
    return new Date(obj.getTime()) as T;
  }

  if (obj instanceof Array) {
    return obj.map(item => deepClone(item)) as T;
  }

  const source = obj as Record<string, unknown>;
  const clonedObj: Record<string, unknown> = {};
  for (const key in source) {
    if (Object.prototype.hasOwnProperty.call(source, key)) {
      clonedObj[key] = deepClone(source[key]);
    }
  }
  return clonedObj as T;

  return obj;
}

/**
 * 防止事件冒泡
 */
export function stopPropagation(event: React.UIEvent): void {
  event.stopPropagation();
}

/**
 * 阻止默认行为
 */
export function preventDefault(event: React.UIEvent): void {
  event.preventDefault();
}

/**
 * 同时阻止冒泡和默认行为
 */
export function stopEvent(event: React.UIEvent): void {
  event.stopPropagation();
  event.preventDefault();
}

/**
 * 检查是否为移动设备
 */
export function isMobile(): boolean {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  );
}

/**
 * 复制到剪贴板
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }

    // 回退方案
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand('copy');
      textArea.remove();
      return true;
    } catch (error) {
      console.error('Failed to copy:', error);
      textArea.remove();
      return false;
    }
  } catch (error) {
    console.error('Failed to copy:', error);
    return false;
  }
}

/**
 * 下载文件
 */
export function downloadFile(content: string, filename: string, mimeType = 'text/plain'): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * 解析Markdown为段落列表
 */
export function parseMarkdownToParagraphs(content: string): string[] {
  const lines = content.split('\n');
  const paragraphs: string[] = [];
  let currentParagraph = '';

  for (const line of lines) {
    const trimmed = line.trim();

    if (!trimmed) {
      if (currentParagraph) {
        paragraphs.push(currentParagraph);
        currentParagraph = '';
      }
      continue;
    }

    if (trimmed.startsWith('#')) {
      // 标题行单独作为一段
      if (currentParagraph) {
        paragraphs.push(currentParagraph);
        currentParagraph = '';
      }
      paragraphs.push(trimmed);
    } else {
      currentParagraph += (currentParagraph ? ' ' : '') + trimmed;
    }
  }

  if (currentParagraph) {
    paragraphs.push(currentParagraph);
  }

  return paragraphs;
}

/**
 * 计算文本相似度（简化版）
 */
export function calculateSimilarity(text1: string, text2: string): number {
  if (text1 === text2) return 1;

  const len1 = text1.length;
  const len2 = text2.length;
  const maxLen = Math.max(len1, len2);

  if (maxLen === 0) return 1;

  // 简化的编辑距离算法
  const matrix: number[][] = [];

  for (let i = 0; i <= len1; i++) {
    matrix[i] = [i];
  }

  for (let j = 0; j <= len2; j++) {
    matrix[0][j] = j;
  }

  for (let i = 1; i <= len1; i++) {
    for (let j = 1; j <= len2; j++) {
      const cost = text1[i - 1] === text2[j - 1] ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost
      );
    }
  }

  const distance = matrix[len1][len2];
  return 1 - distance / maxLen;
}
