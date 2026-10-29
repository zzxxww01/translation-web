import { useCallback, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState, type MouseEvent, type Ref } from 'react';
import { cn } from '@/lib/utils';
import { SAVE_DELAY_MS, unsavedEdits } from '../lib/edits';
import { editHistory, undoShortcut, type EditKind, type Snapshot } from '../lib/history';
import { hasInlineMarkup, renderedToRaw } from '../lib/inline';
import { InlineMarkdown } from './InlineMarkdown';

type SaveState = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

export interface EditableTextHandle {
  isProtected: () => boolean;
  /** group：同一次整段采用改的几个片段共用，撤销时一起撤回 */
  adopt: (text: string, group?: string) => Promise<void>;
}

interface EditableTextProps {
  ref?: Ref<EditableTextHandle>;
  id: string;
  /** 撤销记录的归属（版本 + 行），默认用 id */
  historyKey?: string;
  value: string | null;
  placeholder: string;
  ariaLabel: string;
  onSave: (text: string) => Promise<void>;
  onProtectionChange?: (id: string, protectedDraft: boolean) => void;
  className?: string;
  inline?: boolean;
  readOnly?: boolean;
}

// 排版视图和编辑框用同一套外框和内边距，换过去时字的位置一点不动
const BOX_OUTER = '-mx-2 block w-[calc(100%+1rem)]';
const BOX_INNER = 'rounded-md border px-2 py-1';
const BOX = `${BOX_OUTER} ${BOX_INNER}`;
// 编辑框默认的折行、字距和排版视图不一样，这里对齐
const SAME_TEXT = 'whitespace-pre-wrap break-words [text-rendering:inherit] [word-spacing:inherit]';

// 按下鼠标那一刻编辑框就失焦了：等松开（点击落定）再换回排版视图，免得这一段变高变矮、点的那一段在鼠标底下挪走
let pointerHeld = false;
let pointerTracked = false;
function trackPointer() {
  if (pointerTracked || typeof window === 'undefined') return;
  pointerTracked = true;
  window.addEventListener('pointerdown', () => { pointerHeld = true; }, true);
  const release = () => { pointerHeld = false; };
  window.addEventListener('pointerup', release, true);
  window.addEventListener('pointercancel', release, true);
}
function afterPointerRelease(callback: () => void) {
  if (!pointerHeld) {
    callback();
    return;
  }
  const done = () => {
    window.removeEventListener('pointerup', done, true);
    window.removeEventListener('pointercancel', done, true);
    setTimeout(callback, 0); // 等 click 派发完
  };
  window.addEventListener('pointerup', done, true);
  window.addEventListener('pointercancel', done, true);
}

/** 点在排版好的文字上：取浏览器放下的光标或选区，换算成第几个字（null = 不在这一段里） */
function renderedSelection(box: HTMLElement, event: MouseEvent): { start: number; end: number } | 'outside' | null {
  const offsetOf = (node: Node, offset: number) => {
    const range = document.createRange();
    range.setStart(box, 0);
    range.setEnd(node, offset);
    return range.toString().length;
  };
  const selection = window.getSelection();
  if (selection && selection.rangeCount > 0) {
    const range = selection.getRangeAt(0);
    const inside = box.contains(range.startContainer) && box.contains(range.endContainer);
    if (!range.collapsed) return inside ? { start: offsetOf(range.startContainer, range.startOffset), end: offsetOf(range.endContainer, range.endOffset) } : 'outside';
    if (inside) {
      const at = offsetOf(range.startContainer, range.startOffset);
      return { start: at, end: at };
    }
  }
  const doc = document as Document & {
    caretPositionFromPoint?: (x: number, y: number) => { offsetNode: Node; offset: number } | null;
    caretRangeFromPoint?: (x: number, y: number) => Range | null;
  };
  const caret = doc.caretPositionFromPoint?.(event.clientX, event.clientY);
  if (caret && box.contains(caret.offsetNode)) {
    const at = offsetOf(caret.offsetNode, caret.offset);
    return { start: at, end: at };
  }
  const range = doc.caretRangeFromPoint?.(event.clientX, event.clientY);
  if (range && box.contains(range.startContainer)) {
    const at = offsetOf(range.startContainer, range.startOffset);
    return { start: at, end: at };
  }
  return null;
}

function editKind(inputType: string | undefined): EditKind {
  if (inputType === 'insertText' || inputType === 'insertCompositionText') return 'type';
  if (inputType?.startsWith('delete') && inputType !== 'deleteByCut' && inputType !== 'deleteByDrag') return 'delete';
  return 'other';
}

/**
 * 平时显示排好版的文字（链接、加粗渲染出来），点哪里就在哪里出现光标、直接改（显示原始 Markdown），
 * 停顿约 1 秒或离开时自动保存——类似 Obsidian 的实时预览。保存状态汇总到栏头（见 lib/edits），
 * 这里只在保存失败时标红、给重试。撤销记录见 lib/history。
 */
export function EditableText({ ref: editorRef, id, historyKey = id, value, placeholder, ariaLabel, onSave, onProtectionChange, className, inline = false, readOnly = false }: EditableTextProps) {
  const [text, setText] = useState(value ?? '');
  const [state, setState] = useState<SaveState>('idle');
  const [editing, setEditing] = useState(false);
  const [prevValue, setPrevValue] = useState(value);
  const ref = useRef<HTMLTextAreaElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  // 最新输入，给定时器和失焦时用（不在渲染里读）
  const latest = useRef(value ?? '');
  const serverValue = useRef(value);
  /** 下一次渲染后要放的光标/选区；reveal = 滚到看得见（在别处按撤销时） */
  const pendingSelection = useRef<(Snapshot & { reveal?: boolean }) | null>(null);
  const beforeInput = useRef<{ start: number; end: number } | null>(null);
  const composing = useRef(false);
  const freshComposition = useRef(false);

  // 后台轮询带回新译文时同步进来；正在改或还没存下时不覆盖（编辑优先）
  if (value !== prevValue) {
    setPrevValue(value);
    if (!editing && (state === 'idle' || state === 'saved')) setText(value ?? '');
  }

  useEffect(() => trackPointer(), []);

  // 别处来的新译文（不是自己刚存的）：撤销记录作废，免得撤回到别的版本上
  useEffect(() => {
    serverValue.current = value;
    if ((value ?? '').trim() === latest.current.trim()) return;
    if (editing || state === 'dirty' || state === 'saving' || state === 'error') return;
    latest.current = value ?? '';
    editHistory.reset(historyKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 只看 value 变没变
  }, [value]);

  // 进入编辑、撤销之后放光标；获得焦点时不让浏览器自己滚动
  useLayoutEffect(() => {
    const at = pendingSelection.current;
    const el = ref.current;
    if (!at || !el) return;
    pendingSelection.current = null;
    if (document.activeElement !== el) el.focus({ preventScroll: true });
    el.setSelectionRange(Math.min(at.start, el.value.length), Math.min(at.end, el.value.length));
    if (at.reveal) el.scrollIntoView?.({ block: 'nearest' });
  });

  const save = useCallback(async (next: string) => {
    clearTimeout(timer.current);
    if (!next.trim()) {
      // 原本就没有译文、改了又删光（比如撤销回去）：没有要存的
      if (!serverValue.current?.trim()) {
        unsavedEdits.remove(id);
        setState('idle');
        return;
      }
      unsavedEdits.set(id, 'error');
      setState('error');
      return;
    }
    setState('saving');
    unsavedEdits.set(id, 'saving');
    try {
      await onSave(next.trim());
      if (latest.current === next) {
        unsavedEdits.saved(id);
        setState('saved');
      }
    } catch {
      unsavedEdits.set(id, 'error');
      setState('error');
    }
  }, [id, onSave]);

  // 这一版变成只读（重翻开始）：离开编辑状态，没存下的修改立刻存掉，不留定时器
  const [prevReadOnly, setPrevReadOnly] = useState(readOnly);
  if (readOnly !== prevReadOnly) {
    setPrevReadOnly(readOnly);
    if (readOnly) setEditing(false);
  }
  useEffect(() => {
    if (!readOnly) return;
    clearTimeout(timer.current);
    if (state === 'dirty') void Promise.resolve().then(() => save(latest.current));
    // eslint-disable-next-line react-hooks/exhaustive-deps -- 只在刚变只读时存一次
  }, [readOnly]);

  const protectedDraft = editing || state === 'dirty' || state === 'saving' || state === 'error';
  useEffect(() => {
    onProtectionChange?.(id, protectedDraft);
  }, [id, protectedDraft, onProtectionChange]);

  /** 改文字：标记未保存，停顿后自动存（撤销记录由调用方先记） */
  const change = useCallback((next: string) => {
    setText(next);
    latest.current = next;
    unsavedEdits.set(id, 'dirty');
    setState('dirty');
    clearTimeout(timer.current);
    timer.current = setTimeout(() => void save(next), SAVE_DELAY_MS);
  }, [id, save]);

  const currentSnapshot = useCallback((): Snapshot => {
    const el = ref.current;
    const length = latest.current.length;
    return el && document.activeElement === el
      ? { text: latest.current, start: el.selectionStart, end: el.selectionEnd }
      : { text: latest.current, start: length, end: length };
  }, []);

  /** 撤销或重做到某一步：进入编辑，光标放回当时的位置 */
  const step = useCallback((direction: 'undo' | 'redo') => {
    if (readOnly) return false;
    const current = currentSnapshot();
    const target = direction === 'undo' ? editHistory.undo(historyKey, current) : editHistory.redo(historyKey, current);
    if (!target) return false;
    pendingSelection.current = { ...target, reveal: document.activeElement !== ref.current };
    setEditing(true);
    change(target.text);
    return true;
  }, [readOnly, currentSnapshot, historyKey, change]);

  useEffect(() => {
    if (readOnly) return;
    return editHistory.register(historyKey, { undo: () => step('undo'), redo: () => step('redo') });
  }, [readOnly, historyKey, step]);

  // 整段采用仍通过各片段自己的保存流程，保留失败重试和栏头保存状态；采用也能撤销。
  useImperativeHandle(editorRef, () => ({
    isProtected: () => protectedDraft,
    adopt: async (next, group) => {
      if (protectedDraft || readOnly) return;
      editHistory.record(historyKey, currentSnapshot(), 'other', { group });
      setText(next);
      latest.current = next;
      await save(next);
    },
  }), [protectedDraft, readOnly, save, historyKey, currentSnapshot]);

  useEffect(() => () => {
    clearTimeout(timer.current);
    unsavedEdits.remove(id);
  }, [id]);

  // 浏览器菜单里的「撤销」也走这里；记下每次输入前的选区，撤销时光标放回去
  useEffect(() => {
    const el = ref.current;
    if (!editing || !el) return;
    const onBeforeInput = (event: InputEvent) => {
      if (event.inputType === 'historyUndo' || event.inputType === 'historyRedo') {
        event.preventDefault();
        step(event.inputType === 'historyUndo' ? 'undo' : 'redo');
        return;
      }
      if (!beforeInput.current) beforeInput.current = { start: el.selectionStart, end: el.selectionEnd };
    };
    el.addEventListener('beforeinput', onBeforeInput);
    return () => el.removeEventListener('beforeinput', onBeforeInput);
  }, [editing, step]);

  const onInput = (next: string, inputType: string | undefined) => {
    const before = { text: latest.current, ...(beforeInput.current ?? { start: latest.current.length, end: latest.current.length }) };
    beforeInput.current = null;
    if (!composing.current) editHistory.record(historyKey, before, editKind(inputType));
    else if (freshComposition.current) {
      // 输入法：一次上屏单独算一步；拼写途中的拼音不记，撤销不会退回到半截拼音
      freshComposition.current = false;
      editHistory.record(historyKey, before, 'other');
    }
    change(next);
  };

  const enter = (event: MouseEvent<HTMLElement>) => {
    const picked = renderedSelection(event.currentTarget, event);
    // 跨段选中，或在带链接的段落里选中了字：是在复制，留在排版视图
    if (picked === 'outside' || (picked && picked.start !== picked.end && hasInlineMarkup(text))) return;
    const start = picked ? renderedToRaw(text, picked.start) : text.length;
    const end = picked ? renderedToRaw(text, picked.end) : text.length;
    pendingSelection.current = { text, start, end };
    setEditing(true);
  };

  const leave = () => {
    editHistory.close(historyKey);
    if (state === 'dirty') void save(latest.current);
    afterPointerRelease(() => {
      if (document.activeElement !== ref.current) setEditing(false);
    });
  };

  const Container = inline ? 'span' : 'div';
  // 重翻期间这一版只读：翻完会整篇替换，期间改了也留不住
  if (readOnly) {
    // 没有待存的修改时显示最新的译文（重翻完成后换成新版）
    const shown = state === 'idle' || state === 'saved' ? value ?? '' : text;
    return (
      <Container className={cn('group/edit relative', className)}>
        <Container className={cn(inline ? 'rounded' : BOX, SAME_TEXT, 'border-transparent text-text-secondary/80')}>
          {shown ? <InlineMarkdown text={shown} /> : <span className="text-text-disabled">{placeholder}</span>}
        </Container>
      </Container>
    );
  }
  return (
    <Container className={cn('group/edit relative', className)}>
      {editing ? (
        // 高度靠下面那层看不见的同样文字撑开，不用每次输入先把高度清零再量（那样会让整栏滚动位置跳）
        <Container className={cn(BOX_OUTER, 'grid grid-cols-1')}>
          <Container aria-hidden className={cn(BOX_INNER, SAME_TEXT, 'invisible border-transparent [grid-area:1/1]')}>
            {text}{'\u200b'}
          </Container>
          <textarea
            ref={ref}
            rows={1}
            value={text}
            aria-label={ariaLabel}
            placeholder={placeholder}
            spellCheck={false}
            onChange={event => onInput(event.target.value, (event.nativeEvent as InputEvent).inputType)}
            onCompositionStart={() => { composing.current = true; freshComposition.current = true; }}
            onCompositionEnd={() => { composing.current = false; }}
            onMouseDown={() => editHistory.close(historyKey)}
            onBlur={leave}
            onKeyDown={event => {
              const shortcut = composing.current ? null : undoShortcut(event.nativeEvent);
              if (shortcut) {
                event.preventDefault();
                step(shortcut);
                return;
              }
              if (event.key === 'Escape') event.currentTarget.blur();
              else if (/^(Arrow|Home|End|Page)/.test(event.key)) editHistory.close(historyKey);
            }}
            className={cn(
              BOX_INNER, SAME_TEXT,
              'block h-full w-full min-w-0 resize-none overflow-hidden border-primary-200 bg-white text-inherit leading-[inherit] [grid-area:1/1] placeholder:text-text-disabled focus:outline-none',
              state === 'error' && 'border-error/40 bg-error/5'
            )}
          />
        </Container>
      ) : (
        <Container
          role="button"
          tabIndex={0}
          aria-label={`编辑：${ariaLabel}`}
          onClick={enter}
          onKeyDown={event => {
            if (event.key === 'Enter') {
              event.preventDefault();
              pendingSelection.current = { text, start: text.length, end: text.length };
              setEditing(true);
            }
          }}
          className={cn(
            inline ? 'rounded border border-transparent' : BOX,
            SAME_TEXT, 'cursor-text border-transparent transition-colors hover:bg-bg-hover/60',
            state === 'error' && 'border-error/40 bg-error/5'
          )}
        >
          {text ? <InlineMarkdown text={text} /> : <span className="text-text-disabled">{placeholder}</span>}
        </Container>
      )}
      {state === 'error' && (
        <span className="pointer-events-none absolute -bottom-1 right-0 flex items-center gap-2 text-[11px]">
          <button
            type="button"
            onClick={() => void save(text)}
            className="pointer-events-auto rounded bg-white px-1.5 text-error shadow-sm"
          >
            {text.trim() ? '保存失败，点此重试' : '译文不能为空'}
          </button>
        </span>
      )}
    </Container>
  );
}
