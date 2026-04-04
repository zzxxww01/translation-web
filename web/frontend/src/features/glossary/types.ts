export type { GlossaryTerm, GlossaryRecommendation, TranslationStrategy } from '@/features/confirmation/types';
import type { GlossaryTerm, TranslationStrategy } from '@/features/confirmation/types';

export type GlossaryScope = 'project' | 'global' | 'recommendations';
export type SortKey = 'updated_at' | 'original' | 'translation';
export type ListMode = 'table' | 'grouped';

export interface EditingTerm {
  original: string;
  translation: string;
  strategy: TranslationStrategy;
  note: string;
  tags: string[];
  status: 'active' | 'disabled';
}

export interface GlossaryCenterProps {
  projectId?: string | null;
  projectTitle?: string | null;
  defaultScope?: GlossaryScope;
  onBack?: () => void;
}

export const strategyLabels: Record<TranslationStrategy, string> = {
  preserve: '保留原文',
  preserve_annotate: '保留原文+首次注释',
  first_annotate: '首次标注',
  translate: '翻译',
};

export const strategyExamples: Record<TranslationStrategy, string> = {
  translate: '全文直接使用中文翻译。例：wafer → 全文写"晶圆"',
  first_annotate: '首次出现用中文并括号注原文，后续只用中文。例：TSMC → 首次写"台积电（TSMC）"，后文写"台积电"',
  preserve: '全文保留英文原文，不翻译不解释。例：AMD → 全文写"AMD"',
  preserve_annotate: '首次出现保留原文并括号注中文，后续只保留原文。例：TSMC → 首次写"TSMC（台积电）"，后文写"TSMC"',
};

export const emptyEditor: EditingTerm = {
  original: '',
  translation: '',
  strategy: 'translate',
  note: '',
  tags: [],
  status: 'active',
};

export function normalizeTags(raw: string[] | string): string[] {
  const items = Array.isArray(raw) ? raw : raw.split(',');
  const seen = new Set<string>();
  const result: string[] = [];
  items
    .map(item => item.trim())
    .filter(Boolean)
    .forEach(item => {
      const key = item.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      result.push(item);
    });
  return result;
}

export function toEditor(term: GlossaryTerm): EditingTerm {
  return {
    original: term.original,
    translation: term.translation || '',
    strategy: term.strategy,
    note: term.note || '',
    tags: [...(term.tags || [])],
    status: (term.status as 'active' | 'disabled') || 'active',
  };
}

export function scopeLabel(scope: GlossaryScope): string {
  if (scope === 'project') return '项目术语';
  if (scope === 'recommendations') return '推荐提升';
  return '全局术语';
}
