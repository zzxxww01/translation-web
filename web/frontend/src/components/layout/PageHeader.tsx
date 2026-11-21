import { useContext, type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { PageActions } from './HeaderSlot';
import { HeaderSlotContext } from './headerSlotContext';

interface PageHeaderProps {
  title: ReactNode;
  /** 右侧操作区（按钮、模型选择器、进行中的状态等）：放进全站顶栏右侧 */
  actions?: ReactNode;
  className?: string;
}

/**
 * 各功能页的「头部」：顶部导航已经标出当前页面，页面不再另占一行标题栏（2026-11-22 用户反馈头部太多、正文太小）。
 * 标题只留给读屏；操作按钮放进全站顶栏右侧。没有顶栏时（单独渲染、测试）退回原来的一行标题栏。
 */
export function PageHeader({ title, actions, className }: PageHeaderProps) {
  const slot = useContext(HeaderSlotContext);
  if (!slot) {
    return (
      <header className={cn('flex min-h-10 flex-wrap items-center justify-between gap-x-4 gap-y-2 border-b border-border-subtle pb-3', className)}>
        <h1 className="min-w-0 text-lg leading-tight text-text-primary">{title}</h1>
        {actions && <div className="flex min-w-0 flex-wrap items-center gap-2">{actions}</div>}
      </header>
    );
  }
  return (
    <>
      <h1 className="sr-only">{title}</h1>
      {actions && (
        <PageActions>
          <div className="flex min-w-0 items-center gap-2">{actions}</div>
        </PageActions>
      )}
    </>
  );
}
