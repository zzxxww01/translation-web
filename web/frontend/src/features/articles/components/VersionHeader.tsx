import type { ComponentProps, ReactNode } from 'react';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';

/** 栏头的三行排版块：小标题、版本名（或对照栏的标签）、状态行；右上角放操作。 */
export function VersionHeader({ eyebrow, primary = false, title, line, actions }: {
  eyebrow: string;
  primary?: boolean;
  title: ReactNode;
  line: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-start gap-2">
      <div className="min-w-0 flex-1">
        <div className={cn('mb-1.5 flex items-center gap-1 text-[11px] tracking-[0.14em]', primary ? 'text-primary-500' : 'text-text-muted/70')}>
          {primary && <Star className="h-3 w-3 fill-current" />}
          {eyebrow}
        </div>
        <div className="flex min-h-[26px] items-center">{title}</div>
        {line}
      </div>
      {actions && <div className="-mr-1 -mt-1 flex shrink-0 items-center gap-0.5">{actions}</div>}
    </div>
  );
}

/** 版本名：宋体 16px */
export function VersionName({ children, english = false }: { children: ReactNode; english?: boolean }) {
  return (
    <span className={cn('truncate text-[16px] font-semibold leading-snug text-text-primary',
      english ? '[font-family:var(--font-source)]' : '[font-family:var(--font-display)]')}>
      {children}
    </span>
  );
}

export const ICON_BUTTON = 'inline-flex h-8 w-8 items-center justify-center rounded-lg text-text-muted transition-colors hover:bg-[rgba(43,39,48,0.05)] hover:text-text-primary disabled:opacity-40';

/** 只有图标的按钮；能被 Radix 的 asChild 包（ref 和其余属性都传下去） */
export function IconAction({ label, className, children, ...props }: ComponentProps<'button'> & { label: string }) {
  return (
    <button type="button" aria-label={label} title={label} className={cn(ICON_BUTTON, className)} {...props}>
      {children}
    </button>
  );
}
