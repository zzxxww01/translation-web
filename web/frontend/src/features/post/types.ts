/**
 * 帖子翻译相关的类型定义
 */

export interface Instruction {
  id: string;
  label: string;
  icon: string;
  instruction: string;
}

export const POST_CONTENT_MAX_LENGTH = 10_000;
export const OPTIMIZATION_INSTRUCTION_MAX_LENGTH = 1_000;
export const TITLE_INSTRUCTION_MAX_LENGTH = 1_000;

/**
 * 快捷优化选项的中文可读描述。
 *
 * 版本记录里的 instruction 会同时用于：版本下拉展示、以及作为多轮优化的
 * conversation_history 发回后端。写内部 id（如 `[readable]`）对两者都是无信息的，
 * 所以统一写成一句人话摘要。
 */
export const POST_OPTIMIZE_OPTION_LABELS: Record<string, string> = {
  readable: '按可读性优化：一句一事、主语明确、先结论后解释',
  idiomatic: '让中文更自然地道：去掉翻译腔与多余连接词',
  professional: '提高专业度与信息密度：删口水话，不增不减信息',
};

/** 取快捷优化选项的可读描述，未知 id 回退为 id 本身 */
export function describeOptimizeOption(optionId: string): string {
  return POST_OPTIMIZE_OPTION_LABELS[optionId] ?? optionId;
}
