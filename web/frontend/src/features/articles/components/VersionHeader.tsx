import type { ComponentProps, ReactNode } from 'react';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ICON_BUTTON, MEASURE } from '../lib/ui';

export interface VersionHeaderProps {
  eyebrow: string;
  primary?: boolean;
  title: ReactNode;
  line: ReactNode;
  actions?: ReactNode;
}

/**
 * 栏头的三行排版块（设计文档 6.2）：小标题和右上角操作同一行，版本名（或对照栏的标签）、状态行各占整行宽。
 * 和正文共用版心，栏变宽时左边缘仍和正文对齐。collapse 是 PaneGrid 给的「收起」按钮，放在操作最后。
 */
export function VersionHeader({ eyebrow, primary = false, title, line, actions, collapse }: VersionHeaderProps & { collapse?: ReactNode }) {
  return (
    <div className={MEASURE}>
      <div className="flex h-6 items-center gap-2">
        <span className={cn('flex min-w-0 items-center gap-1 text-[11px] font-medium leading-none tracking-[0.14em]',
          primary ? 'text-primary-500' : 'text-text-muted')}>
          {primary && <Star aria-hidden className="h-3 w-3 shrink-0 fill-current" strokeWidth={1.75} />}
          {eyebrow}
        </span>
        {(actions || collapse) && (
          <div className="-my-1 -mr-2 ml-auto flex shrink-0 items-center gap-0.5">{actions}{collapse}</div>
        )}
      </div>
      <div className="mt-1.5 flex min-h-8 min-w-0 items-center">{title}</div>
      <div className="mt-1 min-w-0">{line}</div>
    </div>
  );
}

/** 版本名：宋体 16px（原文栏的 English 用衬线体） */
export function VersionName({ children, english = false }: { children: ReactNode; english?: boolean }) {
  return (
    <span className={cn('min-w-0 truncate text-[16px] font-semibold leading-snug text-text-primary',
      english ? '[font-family:var(--font-source)]' : '[font-family:var(--font-display)]')}>
      {children}
    </span>
  );
}

/** 版本名下面那一行的纯文字版（原文栏的词数、对照栏空着时的说明） */
export function PlainLine({ children }: { children: ReactNode }) {
  return <p className="truncate text-[12px] leading-5 text-text-muted">{children}</p>;
}

/** 只有图标的按钮；能被 Radix 的 asChild 包（ref 和其余属性都传下去） */
export function IconAction({ label, className, children, ...props }: ComponentProps<'button'> & { label: string }) {
  return (
    <button type="button" aria-label={label} title={label} className={cn(ICON_BUTTON, className)} {...props}>
      {children}
    </button>
  );
}
