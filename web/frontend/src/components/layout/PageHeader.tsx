import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  /** 右侧操作区（按钮、模型选择器等） */
  actions?: ReactNode;
  className?: string;
}

/** 各功能页统一的刊头：宋体大标题 + 说明 + 右侧操作。 */
export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <header
      className={cn(
        'flex flex-col gap-5 border-b border-border-subtle pb-7 sm:flex-row sm:items-end sm:justify-between',
        className
      )}
    >
      <div className="min-w-0">
        <h1 className="text-[28px] leading-tight text-text-primary sm:text-[34px]">{title}</h1>
        {description && (
          <p className="mt-2.5 max-w-2xl text-sm leading-relaxed text-text-muted">{description}</p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  );
}
