import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { SAVE_DELAY_MS, unsavedEdits } from '../lib/edits';
import { InlineMarkdown } from './InlineMarkdown';

type SaveState = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';

interface EditableTextProps {
  id: string;
  value: string | null;
  placeholder: string;
  ariaLabel: string;
  onSave: (text: string) => Promise<void>;
  /** 另一版这一段的译文，有就显示「用另一版这段」 */
  adopt?: { label: string; text: string } | null;
  className?: string;
  inline?: boolean;
}

const BOX = '-mx-2 block w-[calc(100%+1rem)] rounded-md border px-2 py-1';

/**
 * 平时显示排好版的文字（链接、加粗渲染出来），点一下变成编辑框（显示原始 Markdown），
 * 停顿约 1 秒或离开时自动保存——类似 Obsidian 的实时预览。保存状态汇总到栏头（见 lib/edits），
 * 这里只在保存失败时标红、给重试。
 */
export function EditableText({ id, value, placeholder, ariaLabel, onSave, adopt, className, inline = false }: EditableTextProps) {
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

  useEffect(() => () => {
    clearTimeout(timer.current);
    unsavedEdits.remove(id);
  }, [id]);

  const change = (next: string, immediately = false) => {
    setText(next);
    latest.current = next;
    unsavedEdits.set(id, 'dirty');
    setState('dirty');
    clearTimeout(timer.current);
    if (immediately) void save(next);
    else timer.current = setTimeout(() => void save(next), SAVE_DELAY_MS);
  };

  const Container = inline ? 'span' : 'div';
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
      {adopt && adopt.text !== text && (
        <button
          type="button"
          onMouseDown={event => event.preventDefault()}
          onClick={() => change(adopt.text, true)}
          className="absolute -top-2 right-0 hidden rounded-md border border-border-subtle bg-white px-2 py-0.5 text-[11px] text-text-secondary shadow-sm hover:border-primary-200 hover:text-primary-700 group-hover/edit:block"
        >
          用{adopt.label}这段
        </button>
      )}
    </Container>
  );
}
