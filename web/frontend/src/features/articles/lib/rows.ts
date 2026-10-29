import type { WorkbenchRow } from '../types';

/**
 * 行的版式。英文原文用衬线体（Source Serif），中文用思源宋体；章节标题、列表、引用、代码各有样式。
 * text-wrap: pretty 避免段末只剩一两个字孤零零一行。
 */
export function rowTextClass(row: WorkbenchRow, lang: 'en' | 'zh' = 'zh'): string {
  const face = `${lang === 'en' ? '[font-family:var(--font-source)]' : '[font-family:var(--font-display)]'} [text-wrap:pretty]`;
  if (row.kind === 'section') return `pt-6 text-[19px] font-semibold leading-snug text-text-primary ${face}`;
  if (/^h[1-4]$/.test(row.kind)) return `pt-3 text-[16.5px] font-semibold leading-snug text-text-primary ${face}`;
  if (row.is_metadata) return 'text-[13px] leading-relaxed text-text-muted';
  if (row.kind === 'blockquote') return `border-l-2 border-border pl-3 text-[15px] leading-[1.85] text-text-secondary ${face}`;
  if (row.kind === 'code' || row.kind === 'table') return 'whitespace-pre-wrap font-mono text-[12.5px] leading-relaxed text-text-secondary';
  return lang === 'en'
    ? `text-[14.5px] leading-[1.78] text-text-secondary ${face}`
    : `text-[15.5px] leading-[1.95] text-text-primary ${face}`;
}
