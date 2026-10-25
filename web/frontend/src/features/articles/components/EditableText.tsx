import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { SAVE_DELAY_MS, unsavedEdits } from '../lib/edits';

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
}

/** 看起来就是一段文字，点进去直接改；停顿约 1 秒或离开格子时自动保存。 */
export function EditableText({ id, value, placeholder, ariaLabel, onSave, adopt, className }: EditableTextProps) {
  const [text, setText] = useState(value ?? '');
  const [state, setState] = useState<SaveState>('idle');
  const [focused, setFocused] = useState(false);
  const [prevValue, setPrevValue] = useState(value);
  const ref = useRef<HTMLTextAreaElement>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  // 最新输入，给定时器和失焦时用（不在渲染里读）
  const latest = useRef(value ?? '');

  // 后台轮询带回新译文时同步进来；正在改或还没存下时不覆盖（编辑优先）
  if (value !== prevValue) {
    setPrevValue(value);
    if (!focused && (state === 'idle' || state === 'saved')) setText(value ?? '');
  }

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = '0px';
    el.style.height = `${el.scrollHeight}px`;
  }, [text]);

  const save = useCallback(async (next: string) => {
    clearTimeout(timer.current);
    if (!next.trim()) {
      setState('error');
      return;
    }
    setState('saving');
    try {
      await onSave(next.trim());
      if (latest.current === next) {
        unsavedEdits.remove(id);
        setState('saved');
      }
    } catch {
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
    unsavedEdits.add(id);
    setState('dirty');
    clearTimeout(timer.current);
    if (immediately) void save(next);
    else timer.current = setTimeout(() => void save(next), SAVE_DELAY_MS);
  };

  const label = state === 'saving' ? '保存中…' : state === 'saved' ? '已保存' : '';

  return (
    <div className={cn('group/edit relative', className)}>
      <textarea
        ref={ref}
        rows={1}
        value={text}
        aria-label={ariaLabel}
        placeholder={placeholder}
        spellCheck={false}
        onChange={event => change(event.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => {
          setFocused(false);
          if (state === 'dirty') void save(latest.current);
        }}
        className={cn(
          '-mx-2 block w-[calc(100%+1rem)] resize-none overflow-hidden rounded-md border border-transparent bg-transparent px-2 py-1',
          'text-inherit leading-[inherit] placeholder:text-text-disabled',
          'transition-colors hover:bg-bg-hover/60 focus:border-primary-200 focus:bg-white focus:outline-none',
          state === 'error' && 'border-error/40 bg-error/5'
        )}
      />
      <div className="pointer-events-none absolute -bottom-1 right-0 flex items-center gap-2 text-[11px]">
        {state === 'error' ? (
          <button
            type="button"
            onClick={() => void save(text)}
            className="pointer-events-auto rounded bg-white px-1.5 text-error shadow-sm"
          >
            {text.trim() ? '保存失败，点此重试' : '译文不能为空'}
          </button>
        ) : (
          label && <span className="rounded bg-white/80 px-1 text-text-muted">{label}</span>
        )}
      </div>
      {adopt && adopt.text !== text && (
        <button
          type="button"
          onClick={() => change(adopt.text, true)}
          className="absolute -top-2 right-0 hidden rounded-md border border-border-subtle bg-white px-2 py-0.5 text-[11px] text-text-secondary shadow-sm hover:border-primary-200 hover:text-primary-700 group-hover/edit:block"
        >
          用{adopt.label}这段
        </button>
      )}
    </div>
  );
}
