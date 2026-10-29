import { useCallback, useEffect, useImperativeHandle, useLayoutEffect, useRef, useState, type Ref } from 'react';
import { cn } from '@/lib/utils';
import { SAVE_DELAY_MS, unsavedEdits } from '../lib/edits';
import { InlineMarkdown } from './InlineMarkdown';

type SaveState = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

export interface EditableTextHandle {
  isProtected: () => boolean;
  adopt: (text: string) => Promise<void>;
}

interface EditableTextProps {
  ref?: Ref<EditableTextHandle>;
  id: string;
  value: string | null;
  placeholder: string;
  ariaLabel: string;
  onSave: (text: string) => Promise<void>;
  onProtectionChange?: (id: string, protectedDraft: boolean) => void;
  className?: string;
  inline?: boolean;
  readOnly?: boolean;
}

const BOX = '-mx-2 block w-[calc(100%+1rem)] rounded-md border px-2 py-1';

/**
 * 平时显示排好版的文字（链接、加粗渲染出来），点一下变成编辑框（显示原始 Markdown），
 * 停顿约 1 秒或离开时自动保存——类似 Obsidian 的实时预览。保存状态汇总到栏头（见 lib/edits），
 * 这里只在保存失败时标红、给重试。
 */
export function EditableText({ ref: editorRef, id, value, placeholder, ariaLabel, onSave, onProtectionChange, className, inline = false, readOnly = false }: EditableTextProps) {
  const [text, setText] = useState(value ?? '');
  const [state, setState] = useState<SaveState>('idle');
  const [editing, setEditing] = useState(false);
  const [prevValue, setPrevValue] = useState(value);
  const ref = useRef<HTMLTextAreaElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  // 最新输入，给定时器和失焦时用（不在渲染里读）
  const latest = useRef(value ?? '');

  // 后台轮询带回新译文时同步进来；正在改或还没存下时不覆盖（编辑优先）
  if (value !== prevValue) {
    setPrevValue(value);
    if (!editing && (state === 'idle' || state === 'saved')) setText(value ?? '');
  }

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = '0px';
    el.style.height = `${el.scrollHeight}px`;
  }, [text, editing]);

  useEffect(() => {
    if (!editing) return;
    const el = ref.current;
    el?.focus();
    el?.setSelectionRange(el.value.length, el.value.length);
  }, [editing]);

  const save = useCallback(async (next: string) => {
    clearTimeout(timer.current);
    if (!next.trim()) {
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

  // 整段采用仍通过各片段自己的保存流程，保留失败重试和栏头保存状态。
  useImperativeHandle(editorRef, () => ({
    isProtected: () => protectedDraft,
    adopt: async next => {
      if (protectedDraft || readOnly) return;
      setText(next);
      latest.current = next;
      await save(next);
    },
  }), [protectedDraft, readOnly, save]);

  useEffect(() => () => {
    clearTimeout(timer.current);
    unsavedEdits.remove(id);
  }, [id]);

  const change = (next: string) => {
    setText(next);
    latest.current = next;
    unsavedEdits.set(id, 'dirty');
    setState('dirty');
    clearTimeout(timer.current);
    timer.current = setTimeout(() => void save(next), SAVE_DELAY_MS);
  };

  const Container = inline ? 'span' : 'div';
  // 重翻期间这一版只读：翻完会整篇替换，期间改了也留不住
  if (readOnly) {
    // 没有待存的修改时显示最新的译文（重翻完成后换成新版）
    const shown = state === 'idle' || state === 'saved' ? value ?? '' : text;
    return (
      <Container className={cn('group/edit relative', className)}>
        <Container className={cn(inline ? 'rounded' : BOX, 'whitespace-pre-wrap border-transparent text-text-secondary/80')}>
          {shown ? <InlineMarkdown text={shown} /> : <span className="text-text-disabled">{placeholder}</span>}
        </Container>
      </Container>
    );
  }
  return (
    <Container className={cn('group/edit relative', className)}>
      {editing ? (
        <textarea
          ref={ref}
          rows={1}
          value={text}
          aria-label={ariaLabel}
          placeholder={placeholder}
          spellCheck={false}
          onChange={event => change(event.target.value)}
          onBlur={() => {
            setEditing(false);
            if (state === 'dirty') void save(latest.current);
          }}
          onKeyDown={event => {
            if (event.key === 'Escape') event.currentTarget.blur();
          }}
          className={cn(
            BOX,
            'resize-none overflow-hidden border-primary-200 bg-white text-inherit leading-[inherit] placeholder:text-text-disabled focus:outline-none',
            state === 'error' && 'border-error/40 bg-error/5'
          )}
        />
      ) : (
        <Container
          role="button"
          tabIndex={0}
          aria-label={`编辑：${ariaLabel}`}
          onClick={() => setEditing(true)}
          onKeyDown={event => {
            if (event.key === 'Enter') {
              event.preventDefault();
              setEditing(true);
            }
          }}
          className={cn(
            inline ? 'rounded border border-transparent' : BOX,
            'cursor-text whitespace-pre-wrap border-transparent transition-colors hover:bg-bg-hover/60',
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
