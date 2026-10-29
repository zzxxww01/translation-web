/**
 * 撤销记录（Ctrl/⌘+Z、Ctrl+Y / ⌘+⇧+Z）。编辑框离开编辑状态就会卸掉，浏览器自带的撤销跟着没了，
 * 所以记在这里：每段一份，按「版本@内容版次:行」记，换栏、切标签、重新进入编辑都还在；整篇重翻导入后换新的。
 * 连续打字或连续删除（停顿不到 1 秒）算一步；粘贴、剪切、整段采用各算一步；一次输入法上屏算一步。
 * 不在编辑框里按撤销时，撤销页面上最近改过的那一段；一次整段采用改了好几个片段的，一起撤回。
 */

export interface Snapshot {
  text: string;
  start: number;
  end: number;
}

export type EditKind = 'type' | 'delete' | 'other';

interface Step extends Snapshot {
  /** 同一次操作改了好几段时共用的标记（整段采用） */
  group?: string;
}

interface Stack {
  undo: Step[];
  redo: Step[];
  /** 正在累积的一步：同类修改、间隔够短就并进去 */
  open: { kind: EditKind; at: number } | null;
}

/** 页面上挂着、能被「不在编辑框里的撤销」叫到的段落 */
export interface UndoTarget {
  undo: () => boolean;
  redo: () => boolean;
}

interface Entry {
  key: string;
  group?: string;
}

export const COALESCE_MS = 1000;
const STEPS_PER_CELL = 100;

const stacks = new Map<string, Stack>();
const targets = new Map<string, UndoTarget>();
// 全页的先后顺序：每一步撤销记录对应一项
const undoOrder: Entry[] = [];
const redoOrder: Entry[] = [];

function stackOf(key: string): Stack {
  let stack = stacks.get(key);
  if (!stack) {
    stack = { undo: [], redo: [], open: null };
    stacks.set(key, stack);
  }
  return stack;
}

function removeLast(order: Entry[], key: string) {
  for (let index = order.length - 1; index >= 0; index -= 1) {
    if (order[index].key !== key) continue;
    order.splice(index, 1);
    return;
  }
}

function removeAll(order: Entry[], key: string) {
  for (let index = order.findIndex(entry => entry.key === key); index >= 0; index = order.findIndex(entry => entry.key === key)) {
    order.splice(index, 1);
  }
}

/** 从后往前找还在页面上的那一步，撤销（或重做）它；同组的一起 */
function stepLatest(order: Entry[], run: (target: UndoTarget) => boolean): boolean {
  let group: string | undefined;
  let done = false;
  for (let index = order.length - 1; index >= 0; index -= 1) {
    const entry = order[index];
    if (done && (!group || entry.group !== group)) continue;
    const target = targets.get(entry.key);
    if (!target || !run(target)) continue;
    if (!done) {
      done = true;
      group = entry.group;
      if (!group) break;
    }
  }
  return done;
}

export const editHistory = {
  /** 改之前记一下原样；和上一下是同一类、间隔不到 1 秒就并成一步 */
  record(key: string, before: Snapshot, kind: EditKind, options: { now?: number; group?: string } = {}): void {
    const now = options.now ?? Date.now();
    const stack = stackOf(key);
    const open = stack.open;
    if (!open || kind === 'other' || open.kind !== kind || now - open.at >= COALESCE_MS) {
      stack.undo.push({ ...before, group: options.group });
      undoOrder.push({ key, group: options.group });
      if (stack.undo.length > STEPS_PER_CELL) {
        stack.undo.shift();
        undoOrder.splice(undoOrder.findIndex(entry => entry.key === key), 1);
      }
    }
    stack.open = kind === 'other' ? null : { kind, at: now };
    if (stack.redo.length) {
      stack.redo = [];
      removeAll(redoOrder, key);
    }
  },
  /** 光标挪开、失焦之后，下一下另起一步 */
  close(key: string): void {
    const stack = stacks.get(key);
    if (stack) stack.open = null;
  },
  undo(key: string, current: Snapshot): Snapshot | null {
    const stack = stacks.get(key);
    const previous = stack?.undo.pop();
    if (!stack || !previous) return null;
    stack.redo.push({ ...current, group: previous.group });
    stack.open = null;
    removeLast(undoOrder, key);
    redoOrder.push({ key, group: previous.group });
    return previous;
  },
  redo(key: string, current: Snapshot): Snapshot | null {
    const stack = stacks.get(key);
    const next = stack?.redo.pop();
    if (!stack || !next) return null;
    stack.undo.push({ ...current, group: next.group });
    stack.open = null;
    removeLast(redoOrder, key);
    undoOrder.push({ key, group: next.group });
    return next;
  },
  /** 这一段被外面整段换掉了（别处的新译文）：旧记录作废 */
  reset(key: string): void {
    if (!stacks.delete(key)) return;
    removeAll(undoOrder, key);
    removeAll(redoOrder, key);
  },
  register(key: string, target: UndoTarget): () => void {
    targets.set(key, target);
    return () => {
      if (targets.get(key) === target) targets.delete(key);
    };
  },
  /** 撤销页面上最近改过、现在还显示着的那一段；没有可撤销的返回 false */
  undoLatest(): boolean {
    return stepLatest(undoOrder, target => target.undo());
  },
  redoLatest(): boolean {
    return stepLatest(redoOrder, target => target.redo());
  },
  /** 测试用 */
  clear(): void {
    stacks.clear();
    targets.clear();
    undoOrder.length = 0;
    redoOrder.length = 0;
  },
};

/** 编辑快捷键：'undo' / 'redo' / null。输入法正在拼写时不算。 */
export function undoShortcut(event: KeyboardEvent): 'undo' | 'redo' | null {
  if (event.isComposing || event.altKey || !(event.ctrlKey || event.metaKey)) return null;
  const key = event.key.toLowerCase();
  if (key === 'z') return event.shiftKey ? 'redo' : 'undo';
  if (key === 'y' && event.ctrlKey && !event.shiftKey) return 'redo';
  return null;
}
