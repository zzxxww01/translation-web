import { useId } from 'react';
import { cn } from '@/lib/utils';
import type { Harness } from '@/features/skills/harness';
import { ARTICLE_HARNESSES } from '../lib/agentOptions';

export function ArticleAgentChoice({ value, onChange, disabled = false }: {
  value: Harness;
  onChange: (value: Harness) => void;
  disabled?: boolean;
}) {
  const name = useId();
  return (
    <div role="radiogroup" aria-label="译本 2 Agent" className="flex flex-wrap items-center gap-2">
      {ARTICLE_HARNESSES.map(item => (
        <label key={item.id} className={cn(
          'flex cursor-pointer items-center gap-1.5 rounded-md border px-2.5 py-1 text-sm',
          value === item.id ? 'border-primary-300 bg-primary-50 text-primary-700' : 'border-border-subtle bg-white text-text-secondary',
          disabled && 'cursor-default opacity-50',
        )}>
          <input type="radio" name={name} value={item.id} checked={value === item.id} disabled={disabled}
            onChange={() => onChange(item.id)} className="accent-[var(--color-primary-500)]" />
          {item.label}
        </label>
      ))}
    </div>
  );
}
