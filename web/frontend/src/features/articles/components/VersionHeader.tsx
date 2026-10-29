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
 * 栏头（设计文档 6.2，10-29 起方案 A）：一行写完——小标题、版本名（或对照栏的标签）、状态行，操作靠右。
 * 状态行放不下时只截断说明文字。stacked（手机，一栏占满屏宽）：状态行单独第二行。
 * 和正文共用版心，栏变宽时左边缘仍和正文对齐。collapse 是 PaneGrid 给的「收起」按钮，放在操作最后。
 */
export function VersionHeader({ eyebrow, primary = false, title, line, actions, collapse, stacked = false }: VersionHeaderProps & { collapse?: ReactNode; stacked?: boolean }) {
  const label = (
    <span className={cn('flex shrink-0 items-center gap-1 whitespace-nowrap text-[11px] font-medium leading-none tracking-[0.14em]',
      primary ? 'text-primary-500' : 'text-text-muted')}>
      {primary && <Star aria-hidden className="h-3 w-3 shrink-0 fill-current" strokeWidth={1.75} />}
      {eyebrow}
    </span>
  );
  const tools = (actions || collapse) && <div className="-mr-2 ml-auto flex shrink-0 items-center gap-0.5">{actions}{collapse}</div>;
  if (stacked) {
    return (
      <div className={MEASURE}>
        <div className="flex min-h-8 min-w-0 items-center gap-2.5">{label}<div className="flex min-w-0 items-center">{title}</div>{tools}</div>
        <div className="mt-0.5 min-w-0">{line}</div>
      </div>
    );
  }
  return (
    <div className={cn(MEASURE, 'flex min-w-0 items-center gap-2.5')}>
      {label}
      <div className="flex min-w-0 shrink-0 items-center">{title}</div>
      <div className="min-w-0 flex-1">{line}</div>
      {tools}
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
