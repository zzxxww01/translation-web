import type { WorkbenchRow } from '../types';

/** 行的版式：章节标题、小标题、作者行、列表、引用、代码/表格。三栏共用，保证同一行高度接近。 */
export function rowTextClass(row: WorkbenchRow): string {
  if (row.kind === 'section') return 'pt-6 text-[19px] font-semibold leading-snug text-text-primary [font-family:var(--font-display)]';
  if (/^h[1-4]$/.test(row.kind)) return 'pt-3 text-[16px] font-semibold leading-snug text-text-primary';
  if (row.is_metadata) return 'text-[13px] leading-relaxed text-text-muted';
  if (row.kind === 'blockquote') return 'border-l-2 border-border pl-3 text-[15px] leading-[1.8] text-text-secondary';
  if (row.kind === 'code' || row.kind === 'table') return 'whitespace-pre-wrap font-mono text-[12.5px] leading-relaxed text-text-secondary';
  return 'text-[15px] leading-[1.8] text-text-primary';
}
