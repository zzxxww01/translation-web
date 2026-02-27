/**
 * 分段确认工作流 - 验证工具
 */

import { TEXT_LIMITS, REGEX_PATTERNS } from './constants';

/**
 * 验证结果
 */
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

/**
 * 创建验证结果
 */
function createResult(
  isValid: boolean,
  errors: string[] = [],
  warnings: string[] = []
): ValidationResult {
  return { isValid, errors, warnings };
}

/**
 * 验证项目ID
 */
export function validateProjectId(projectId: string): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!projectId) {
    errors.push('项目ID不能为空');
  }

  if (projectId.length > 100) {
    errors.push('项目ID过长');
  }

  if (!/^[a-zA-Z0-9_-]+$/.test(projectId)) {
    errors.push('项目ID只能包含字母、数字、下划线和连字符');
  }

  return createResult(errors.length === 0, errors, warnings);
}

/**
 * 验证段落索引
 */
export function validateParagraphIndex(
  index: number,
  total: number
): ValidationResult {
  const errors: string[] = [];

  if (index < 0) {
    errors.push('段落索引不能为负数');
  }

  if (index >= total && total > 0) {
    errors.push(`段落索引超出范围（0-${total - 1}）`);
  }

  return createResult(errors.length === 0, errors);
}

/**
 * 验证段落文本
 */
export function validateParagraphText(text: string): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!text || text.trim().length === 0) {
    errors.push('段落文本不能为空');
  }

  if (text.length > TEXT_LIMITS.MAX_PARAGRAPH_LENGTH) {
    errors.push(`段落文本过长（最大${TEXT_LIMITS.MAX_PARAGRAPH_LENGTH}字符）`);
  }

  // 检查是否包含特殊字符
  if (text.includes('\x00') || text.includes('\ufffd')) {
    warnings.push('文本可能包含无效字符');
  }

  return createResult(errors.length === 0, errors, warnings);
}

/**
 * 验证译文
 */
export function validateTranslation(translation: string): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!translation || translation.trim().length === 0) {
    errors.push('译文不能为空');
  }

  if (translation.length > TEXT_LIMITS.MAX_PARAGRAPH_LENGTH) {
    errors.push('译文过长');
  }

  // 检查是否包含未配对的Markdown符号
  const unmatchedBrackets = (translation.match(/\*\*/g) || []).length % 2 !== 0;
  if (unmatchedBrackets) {
    warnings.push('可能包含未配对的Markdown格式符号');
  }

  return createResult(errors.length === 0, errors, warnings);
}

/**
 * 验证术语
 */
export function validateTerm(term: {
  original: string;
  translation?: string;
}): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!term.original || term.original.trim().length === 0) {
    errors.push('术语原文不能为空');
  }

  if (term.original.length > TEXT_LIMITS.MAX_TERM_LENGTH) {
    errors.push(`术语原文过长（最大${TEXT_LIMITS.MAX_TERM_LENGTH}字符）`);
  }

  if (term.translation && term.translation.length > TEXT_LIMITS.MAX_TERM_LENGTH) {
    errors.push('术语译文过长');
  }

  return createResult(errors.length === 0, errors, warnings);
}

/**
 * 验证版本名称
 */
export function validateVersionName(name: string): ValidationResult {
  const errors: string[] = [];

  if (!name || name.trim().length === 0) {
    errors.push('版本名称不能为空');
  }

  if (name.length > TEXT_LIMITS.MAX_VERSION_NAME_LENGTH) {
    errors.push('版本名称过长');
  }

  return createResult(errors.length === 0, errors);
}

/**
 * 验证Markdown内容
 */
export function validateMarkdownContent(content: string): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!content || content.trim().length === 0) {
    errors.push('Markdown内容不能为空');
    return createResult(false, errors);
  }

  // 检查是否为有效的Markdown
  const lines = content.split('\n');
  const nonEmptyLines = lines.filter(line => line.trim().length > 0);

  if (nonEmptyLines.length === 0) {
    errors.push('Markdown内容不包含有效文本');
  }

  // 检查是否有标题
  const hasHeading = lines.some(line => REGEX_PATTERNS.MARKDOWN_HEADING.test(line));
  if (!hasHeading) {
    warnings.push('建议添加标题以便更好地对齐');
  }

  return createResult(errors.length === 0, errors, warnings);
}

/**
 * 验证文件
 */
export function validateFile(file: File): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!file) {
    errors.push('未选择文件');
    return createResult(false, errors);
  }

  // 检查文件大小
  if (file.size > 10 * 1024 * 1024) { // 10MB
    errors.push('文件大小不能超过10MB');
  }

  // 检查文件类型
  const extension = '.' + file.name.split('.').pop()?.toLowerCase();
  const validExtensions = ['.md', '.txt', '.markdown'];

  if (!validExtensions.includes(extension)) {
    errors.push('不支持的文件类型，请上传.md或.txt文件');
  }

  return createResult(errors.length === 0, errors, warnings);
}

/**
 * 验证术语变更
 */
export function validateTermChanges(changes: Array<{
  term: string;
  old_translation: string;
  new_translation: string;
}>): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!changes || changes.length === 0) {
    warnings.push('没有术语变更');
  }

  changes.forEach((change, index) => {
    if (!change.term) {
      errors.push(`第${index + 1}项：术语不能为空`);
    }

    if (!change.old_translation || !change.new_translation) {
      errors.push(`第${index + 1}项：翻译不能为空`);
    }

    if (change.old_translation === change.new_translation) {
      warnings.push(`第${index + 1}项：翻译未发生变化`);
    }
  });

  return createResult(errors.length === 0, errors, warnings);
}

/**
 * 验证导出选项
 */
export function validateExportOptions(options: {
  includeSource: boolean;
  format: 'markdown' | 'html' | 'pdf';
}): ValidationResult {
  const errors: string[] = [];

  if (!['markdown', 'html', 'pdf'].includes(options.format)) {
    errors.push('不支持的导出格式');
  }

  return createResult(errors.length === 0, errors);
}

/**
 * 批量验证
 */
export function validateBatch<T>(
  items: T[],
  validator: (item: T, index: number) => ValidationResult
): ValidationResult {
  const allErrors: string[] = [];
  const allWarnings: string[] = [];

  items.forEach((item, index) => {
    const result = validator(item, index);
    allErrors.push(...result.errors.map(e => `[项目${index + 1}] ${e}`));
    allWarnings.push(...result.warnings.map(w => `[项目${index + 1}] ${w}`));
  });

  return createResult(
    allErrors.length === 0,
    allErrors,
    allWarnings
  );
}
