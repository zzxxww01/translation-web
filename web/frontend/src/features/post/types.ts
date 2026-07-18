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
