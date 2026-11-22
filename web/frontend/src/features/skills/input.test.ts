import { describe, expect, it } from 'vitest';
import type { KeyboardEvent } from 'react';
import { isSendKey } from './input';
import { foldEvents } from './state';
import type { SkillEvent } from './types';

const key = (init: Partial<{ key: string; shiftKey: boolean; ctrlKey: boolean; metaKey: boolean; altKey: boolean; isComposing: boolean; keyCode: number }>) =>
  ({
    key: 'Enter', shiftKey: false, ctrlKey: false, metaKey: false, altKey: false, keyCode: 13, ...init,
    nativeEvent: { isComposing: Boolean(init.isComposing) },
  }) as unknown as KeyboardEvent<HTMLTextAreaElement>;

describe('isSendKey', () => {
  it('sends on Enter, keeps Shift+Enter for a new line and ignores IME composition', () => {
    expect(isSendKey(key({}))).toBe(true);
    expect(isSendKey(key({ ctrlKey: true }))).toBe(true);
    expect(isSendKey(key({ shiftKey: true }))).toBe(false);
    expect(isSendKey(key({ isComposing: true }))).toBe(false);
    expect(isSendKey(key({ keyCode: 229 }))).toBe(false);
    expect(isSendKey(key({ key: 'a' }))).toBe(false);
  });
});

describe('foldEvents', () => {
  const base = { ts: 0 };
  it('keeps a detached question answerable and tracks held messages', () => {
    const events: SkillEvent[] = [
      { ...base, seq: 1, type: 'question', qid: 'q1', questions: [{ question: '术语？', options: [{ label: '好' }] }] },
      { ...base, seq: 2, type: 'notice', level: 'info', text: '10 分钟内没有回复，会自动按推荐方案继续' },
      { ...base, seq: 3, type: 'status', status: 'idle', error: null, awaiting: true },
      { ...base, seq: 4, type: 'held', items: [{ id: 'h1', text: '补一句', files: [], created_at: 0 }] },
      { ...base, seq: 5, type: 'report', title: '当前状态', lines: ['状态：空闲'] },
    ];
    const view = foldEvents(events);
    expect(view.pendingQids).toEqual(['q1']);
    expect(view.items.some(item => item.kind === 'notice')).toBe(false);
    expect(view.held?.map(item => item.text)).toEqual(['补一句']);
    expect(view.items.at(-1)).toMatchObject({ kind: 'report', lines: ['状态：空闲'] });
  });
});
