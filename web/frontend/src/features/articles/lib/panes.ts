import type { PaneId } from '../types';

export const PANES: PaneId[] = ['source', 'web', 'alt'];
const STORAGE_KEY = 'momo.workbench.collapsed';

export type Collapsed = Record<PaneId, boolean>;

export const NONE_COLLAPSED: Collapsed = { source: false, web: false, alt: false };

/** 收起或展开一栏；至少留一栏展开，最后一栏不让收。 */
export function togglePane(collapsed: Collapsed, pane: PaneId): Collapsed {
  const next = { ...collapsed, [pane]: !collapsed[pane] };
  return PANES.every(id => next[id]) ? collapsed : next;
}

/** 收起的栏是 36px 竖条，展开的平分剩下的宽度。 */
export function gridTemplate(collapsed: Collapsed): string {
  return PANES.map(id => (collapsed[id] ? '36px' : 'minmax(0, 1fr)')).join(' ');
}

export function loadCollapsed(): Collapsed {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? 'null') as Partial<Collapsed> | null;
    if (!raw) return NONE_COLLAPSED;
    const value = { ...NONE_COLLAPSED, ...raw };
    return PANES.every(id => value[id]) ? NONE_COLLAPSED : value;
  } catch {
    return NONE_COLLAPSED;
  }
}

export function saveCollapsed(collapsed: Collapsed): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(collapsed));
  } catch {
    // 无痕模式等拿不到存储时，只是下次不记得
  }
}
