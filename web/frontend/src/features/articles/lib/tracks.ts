import type { ArticleStatus } from '@/features/substack/api';
import type { TrackStatus, WorkbenchRow } from '../types';

/** 译本 2 换模型时可选的模型（llm_providers.yaml 里的别名）。label 也用作孪生项目 id 后缀。 */
export const SECOND_MODELS = [
  { model: 'gemini-official-argon', label: 'argon', note: '盲评最好' },
  { model: 'deepseek-flash-official', label: 'DeepSeek', note: '便宜、快' },
  { model: 'gemini-pro-fallback', label: '3.1 Pro', note: '' },
] as const;

export const TERMS_STEP = '等待术语确认';

/** 一栏已有译文的段数 / 需要译文的段数（图片不算）。 */
export function countFilled(rows: WorkbenchRow[], text: (row: WorkbenchRow) => string | null): { done: number; total: number } {
  const needed = rows.filter(row => row.kind !== 'image');
  return { done: needed.filter(row => Boolean(text(row))).length, total: needed.length };
}

/** 后台步骤名常带章节标题（「处理中: The shape of …」），状态里只留前半截，太长就统称翻译中。 */
export function shortStep(step: string | null): string {
  const head = (step ?? '').split(/[:：]/)[0].trim();
  return head && head.length <= 8 ? head : '翻译中';
}

export function trackSummary(status: TrackStatus, filled: { done: number; total: number }): { text: string; tone: 'busy' | 'wait' | 'done' | 'idle' | 'error' } {
  if (status.active) {
    if (status.current_step === TERMS_STEP) return { text: '等你确认术语', tone: 'wait' };
    return { text: `${shortStep(status.current_step)} ${filled.done}/${filled.total}`, tone: 'busy' };
  }
  if (status.error) return { text: '出错了', tone: 'error' };
  if (filled.total && filled.done >= filled.total) return { text: '已完成', tone: 'done' };
  if (filled.done) return { text: `缺 ${filled.total - filled.done} 段`, tone: 'wait' };
  return { text: '还没开始', tone: 'idle' };
}

/** 停下来了但还缺段：可以只补译缺的（后台续译，不重翻已有的） */
export function canFillMissing(status: TrackStatus, filled: { done: number; total: number }): boolean {
  return !status.active && filled.done > 0 && filled.done < filled.total;
}

/** 文章库列表里一篇文章的状态文字；没导入时为空。 */
export function statusText(status: ArticleStatus, progress: number): string {
  switch (status) {
    case 'imported': return '已导入';
    case 'awaiting_terms': return '等你确认术语';
    case 'translating': return `翻译中 ${Math.round(progress)}%`;
    case 'partial': return `已译 ${Math.round(progress)}%`;
    case 'translated': return '已译完';
    default: return '';
  }
}
