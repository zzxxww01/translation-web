import type { HTMLAttributes } from 'react';
import { cn } from '../../../shared/utils';

export type CardProps = HTMLAttributes<HTMLDivElement>;

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-border-subtle bg-bg-card shadow-sm',
        className
      )}
      {...props}
    />
  );
}
