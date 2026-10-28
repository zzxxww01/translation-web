import type { ArticleStatus } from '@/features/substack/api';
import type { TrackStatus, WorkbenchRow } from '../types';

/** 以前「换个模型再翻一版」的模型（llm_providers.yaml 里的别名），只用来给模型版继续翻译。label 也是孪生项目 id 后缀。 */
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

/** 缺译的段落所在章节（按文中顺序），补译时重译这些章节 */
export function sectionsWithMissing(rows: WorkbenchRow[], text: (row: WorkbenchRow) => string | null): { id: string; title: string }[] {
  const titles = new Map(rows.filter(row => row.kind === 'section').map(row => [row.section_id, row.source]));
  const ids: string[] = [];
  for (const row of rows) {
    if (row.kind === 'image' || row.kind === 'section' || text(row) || ids.includes(row.section_id)) continue;
    ids.push(row.section_id);
  }
  return ids.map(id => ({ id, title: titles.get(id) ?? id }));
}

/** 停下来了但还缺段：可以补译（重译缺段所在的章节） */
export function canFillMissing(status: TrackStatus, filled: { done: number; total: number }): boolean {
  return !status.active && filled.done > 0 && filled.done < filled.total;
}

export type StatusTone = 'muted' | 'busy' | 'wait' | 'done';

/** 已导入文章的翻译进度（只看主译本，后端算好）；没导入时为 null。 */
export function articleStatus(status: ArticleStatus, progress: number): { text: string; tone: StatusTone; percent: number } | null {
  const percent = Math.round(progress);
  switch (status) {
    case 'imported': return { text: '还没翻', tone: 'muted', percent: 0 };
    case 'awaiting_terms': return { text: '等你确认术语', tone: 'wait', percent };
    case 'translating': return { text: `翻译中 ${percent}%`, tone: 'busy', percent };
    case 'partial': return { text: `已译 ${percent}%`, tone: 'wait', percent };
    case 'translated': return { text: '已翻译', tone: 'done', percent: 100 };
    default: return null;
  }
}
