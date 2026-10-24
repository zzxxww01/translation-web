import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface PageHeaderProps {
  title: ReactNode;
  /** 右侧操作区（按钮、模型选择器、进行中的状态等） */
  actions?: ReactNode;
  className?: string;
}

/**
 * 各功能页统一的顶栏：标题和右侧操作压在一行。顶部导航已经标出当前页面，
 * 这里只需一个小标题定位，把纵向空间留给正文，不再放说明文字。
 */
export function PageHeader({ title, actions, className }: PageHeaderProps) {
  return (
    <header
      className={cn(
        'flex min-h-10 flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-border-subtle pb-3',
        className
      )}
    >
      <h1 className="min-w-0 text-lg leading-tight text-text-primary sm:text-xl">{title}</h1>
      {actions && <div className="flex min-w-0 flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}
