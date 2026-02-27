import { forwardRef, useId, type TextareaHTMLAttributes } from 'react';
import { cn } from '../../../shared/utils';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
  showCharCount?: boolean;
  maxLength?: number;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      label,
      error,
      helperText,
      showCharCount = false,
      maxLength,
      className,
      id,
      value,
      ...props
    },
    ref
  ) => {
    const fallbackId = useId();
    const inputId = id ?? fallbackId;
    const charCount = typeof value === 'string' ? value.length : 0;

    return (
      <div className="w-full">
        <div className="flex items-center justify-between">
          {label && (
            <label
              htmlFor={inputId}
              className="mb-1.5 block text-sm font-medium text-text-primary"
            >
              {label}
            </label>
          )}
          {showCharCount && maxLength && (
            <span className="mb-1.5 text-xs text-text-muted">
              {charCount}/{maxLength}
            </span>
          )}
        </div>
        <textarea
          ref={ref}
          id={inputId}
          value={value}
          maxLength={maxLength}
          className={cn(
            'w-full rounded-lg border border-border px-4 py-3 text-base leading-relaxed',
            'placeholder:text-text-muted',
            'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'transition-colors duration-200',
            error && 'border-error focus:ring-error',
            className
          )}
          {...props}
        />
        {error && <p className="mt-1 text-sm text-error">{error}</p>}
        {helperText && !error && (
          <p className="mt-1 text-sm text-text-muted">{helperText}</p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
