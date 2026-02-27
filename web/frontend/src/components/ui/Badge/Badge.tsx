import type { HTMLAttributes } from 'react';
import { cn } from '../../../shared/utils';

export type BadgeVariant = 'default' | 'secondary' | 'outline' | 'destructive';

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-primary-100 text-primary-700 border border-primary-200',
  secondary: 'bg-bg-tertiary text-text-secondary border border-border-subtle',
  outline: 'border border-border text-text-secondary',
  destructive: 'bg-error/10 text-error border border-error/20',
};

export function Badge({ variant = 'default', className, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        variantStyles[variant],
        className
      )}
      {...props}
    />
  );
}
