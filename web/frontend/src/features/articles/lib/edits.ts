import { useSyncExternalStore } from 'react';

export const SAVE_DELAY_MS = 1000;

/** 一格（某一栏的某一段）的保存状态；存好了就从表里删掉 */
export type CellState = 'dirty' | 'saving' | 'error';

// 格子 id 是「栏:行」，例如 web:s01/p003
const cells = new Map<string, CellState>();
const savedAt = new Map<string, number>();
const listeners = new Set<() => void>();
const notify = () => listeners.forEach(listener => listener());
const paneOf = (id: string) => id.split(':')[0];

/** 页面上还没存下的修改：每栏表头显示自动保存状态，离开页面、保存全文前据此等一等或提醒。 */
export const unsavedEdits = {
  set(id: string, state: CellState): void {
    cells.set(id, state);
    notify();
  },
  saved(id: string): void {
    cells.delete(id);
    savedAt.set(paneOf(id), Date.now());
    notify();
  },
  remove(id: string): void {
    if (cells.delete(id)) notify();
  },
  any: () => cells.size > 0,
  subscribe(listener: () => void): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  /** 一栏的状态，拼成字符串好让 useSyncExternalStore 比较：「保存中段数|失败段数|上次保存时间」 */
  snapshot(pane: string): string {
    let busy = 0;
    let failed = 0;
    cells.forEach((state, id) => {
      if (paneOf(id) !== pane) return;
      if (state === 'error') failed += 1;
      else busy += 1;
    });
    return `${busy}|${failed}|${savedAt.get(pane) ?? 0}`;
  },
};

export interface PaneSaveState {
  busy: number;
  failed: number;
  savedAt: number | null;
}

export function usePaneSaveState(pane: string): PaneSaveState {
  const raw = useSyncExternalStore(unsavedEdits.subscribe, () => unsavedEdits.snapshot(pane));
  const [busy, failed, saved] = raw.split('|').map(Number);
  return { busy, failed, savedAt: saved || null };
}

/** 手动保存：让正在编辑的格子失焦（会立刻保存），再等所有修改存好；超时或有失败返回 false。 */
export async function flushEdits(timeoutMs = 8000): Promise<boolean> {
  const active = document.activeElement;
  if (active instanceof HTMLElement && active.tagName === 'TEXTAREA') active.blur();
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const states = [...cells.values()];
    if (states.includes('error')) return false;
    if (!states.length) return true;
    if (Date.now() > deadline) return false;
    await new Promise(resolve => setTimeout(resolve, 150));
  }
}
