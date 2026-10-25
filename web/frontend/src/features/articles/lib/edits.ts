export const SAVE_DELAY_MS = 1000;

// 页面上所有还没存下的格子；离开页面前据此提醒
const pending = new Set<string>();

export const unsavedEdits = {
  add: (id: string) => void pending.add(id),
  remove: (id: string) => void pending.delete(id),
  any: () => pending.size > 0,
};
