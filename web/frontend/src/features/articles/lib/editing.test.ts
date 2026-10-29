// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { COALESCE_MS, editHistory, undoShortcut } from './history';
import { hasInlineMarkup, rawSelection, renderedToRaw } from './inline';

describe('renderedToRaw', () => {
  it('maps a rendered offset back into the raw Markdown', () => {
    const raw = '见[行业模型](https://x.com/m)。后文';
    // 排版后是「见行业模型。后文」
    expect(renderedToRaw(raw, 0)).toBe(0);
    expect(renderedToRaw(raw, 1)).toBe(1); // 链接前
    expect(renderedToRaw(raw, 3)).toBe(raw.indexOf('模'));
    expect(renderedToRaw(raw, 6)).toBe(raw.indexOf('。') + 1);
    expect(renderedToRaw(raw, 8)).toBe(raw.length);
  });

  it('walks into bold and italic, including a link inside italics', () => {
    const raw = '*来源：[行业模型](https://x.com/m)* 和 **重点**';
    expect(renderedToRaw(raw, 2)).toBe(raw.indexOf('：'));
    expect(renderedToRaw(raw, 4)).toBe(raw.indexOf('业'));
    expect(renderedToRaw(raw, '来源：行业模型 和 重'.length)).toBe(raw.indexOf('点'));
  });

  it('knows when the rendered text equals the raw text', () => {
    expect(hasInlineMarkup('只是普通的一句话 * 不是斜体')).toBe(false);
    expect(hasInlineMarkup('有**加粗**')).toBe(true);
  });
});

describe('rawSelection', () => {
  const raw = '见[行业模型](https://x.com/m)。后文';
  // 排版后是「见行业模型。后文」
  const replace = (text: string, start: number, end: number, insert: string) => {
    const target = rawSelection(text, start, end);
    return target.text.slice(0, target.start) + insert + target.text.slice(target.end);
  };

  it('keeps the link when only its words are replaced', () => {
    expect(replace(raw, 1, 5, '模型')).toBe('见[模型](https://x.com/m)。后文');
    expect(replace(raw, 2, 4, 'X')).toBe('见[行X型](https://x.com/m)。后文');
  });

  it('replaces the whole link when the selection covers it and more', () => {
    expect(replace(raw, 0, 6, 'X')).toBe('X后文');
    expect(replace(raw, 1, 6, 'X')).toBe('见X后文');
  });

  it('turns a half-selected link into plain words instead of breaking the Markdown', () => {
    expect(replace(raw, 3, 7, 'X')).toBe('见行业X文');
    expect(replace(raw, 0, 3, 'X')).toBe('X模型。后文');
  });

  it('works inside italics that hold a link, and for a bare caret', () => {
    const caption = '*来源：[行业模型](https://x.com/m)*';
    expect(replace(caption, 0, 3, '出处：')).toBe('*出处：[行业模型](https://x.com/m)*');
    expect(rawSelection(raw, 6, 6)).toEqual({ text: raw, start: raw.indexOf('。') + 1, end: raw.indexOf('。') + 1 });
  });
});

describe('editHistory', () => {
  beforeEach(() => editHistory.clear());
  const at = (text: string) => ({ text, start: text.length, end: text.length });

  it('merges quick typing into one step and splits on pauses and pastes', () => {
    editHistory.record('a', at(''), 'type', { now: 0 });
    editHistory.record('a', at('一'), 'type', { now: 300 });
    editHistory.record('a', at('一二'), 'type', { now: 300 + COALESCE_MS }); // 停顿太久
    editHistory.record('a', at('一二三'), 'other', { now: 300 + COALESCE_MS + 10 }); // 粘贴
    expect(editHistory.undo('a', at('一二三粘贴'))?.text).toBe('一二三');
    expect(editHistory.undo('a', at('一二三'))?.text).toBe('一二');
    expect(editHistory.undo('a', at('一二'))?.text).toBe('');
    expect(editHistory.undo('a', at(''))).toBeNull();
    expect(editHistory.redo('a', at(''))?.text).toBe('一二');
  });

  it('a new edit drops what could be redone', () => {
    editHistory.record('a', at('旧'), 'other');
    editHistory.undo('a', at('新'));
    editHistory.record('a', at('旧'), 'other');
    expect(editHistory.redo('a', at('另一个'))).toBeNull();
  });

  it('undoes the most recently edited paragraph that is still on the page', () => {
    const first = { undo: vi.fn(() => editHistory.undo('first', at('x')) !== null), redo: vi.fn(() => false) };
    const second = { undo: vi.fn(() => editHistory.undo('second', at('y')) !== null), redo: vi.fn(() => false) };
    editHistory.register('first', first);
    const unregister = editHistory.register('second', second);
    editHistory.record('first', at('一'), 'other');
    editHistory.record('second', at('二'), 'other');
    expect(editHistory.undoLatest()).toBe(true);
    expect(second.undo).toHaveBeenCalledTimes(1);
    editHistory.record('second', at('二'), 'other');
    unregister(); // 那一栏换走了
    expect(editHistory.undoLatest()).toBe(true);
    expect(first.undo).toHaveBeenCalledTimes(1);
    expect(editHistory.undoLatest()).toBe(false);
  });

  it('undoes every fragment of one whole-paragraph adoption together', () => {
    const undo = (key: string) => vi.fn(() => editHistory.undo(key, at('新')) !== null);
    const targets = { a: undo('a'), b: undo('b'), c: undo('c') };
    Object.entries(targets).forEach(([key, fn]) => editHistory.register(key, { undo: fn, redo: () => false }));
    editHistory.record('c', at('更早'), 'other');
    editHistory.record('a', at('旧一'), 'other', { group: 'adopt-1' });
    editHistory.record('b', at('旧二'), 'other', { group: 'adopt-1' });
    expect(editHistory.undoLatest()).toBe(true);
    expect(targets.a).toHaveBeenCalledTimes(1);
    expect(targets.b).toHaveBeenCalledTimes(1);
    expect(targets.c).not.toHaveBeenCalled();
    expect(editHistory.undoLatest()).toBe(true);
    expect(targets.c).toHaveBeenCalledTimes(1);
  });

  it('reads the platform shortcuts and ignores them while composing', () => {
    const key = (init: KeyboardEventInit) => new KeyboardEvent('keydown', init);
    expect(undoShortcut(key({ key: 'z', ctrlKey: true }))).toBe('undo');
    expect(undoShortcut(key({ key: 'Z', metaKey: true, shiftKey: true }))).toBe('redo');
    expect(undoShortcut(key({ key: 'y', ctrlKey: true }))).toBe('redo');
    expect(undoShortcut(key({ key: 'z' }))).toBeNull();
    expect(undoShortcut(key({ key: 'z', ctrlKey: true, isComposing: true }))).toBeNull();
  });
});
