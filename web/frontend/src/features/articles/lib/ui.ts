import type { KeyboardEvent } from 'react';

/** 工作台里所有 lucide 图标的描边（设计文档 5.3） */
export const STROKE = 1.75;

/** 键盘聚焦时的描边：主题的 ring 色，跟着圆角走，不会被父元素的 overflow 裁掉一半 */
export const FOCUS_RING = 'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring';

/** 栏头和顶栏的图标按钮：32×32，圆角 8，悬停有浅底 */
export const ICON_BUTTON = `inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-text-muted transition-colors hover:bg-ink-wash hover:text-text-primary disabled:opacity-40 ${FOCUS_RING}`;

/** 正文和栏头共用的版心：栏变宽（旁边的栏收起）时两者一起居中，左边缘始终对齐 */
export const MEASURE = 'mx-auto w-full max-w-[38rem]';

/** 梅红实心胶囊按钮（导出主译本、弹框里的确认） */
export const PRIMARY_BUTTON = `inline-flex items-center gap-1.5 rounded-full bg-primary-500 font-medium text-white shadow-plum transition-colors hover:bg-primary-600 disabled:opacity-60 ${FOCUS_RING}`;

/**
 * 标签组的方向键（WAI-ARIA tabs，自动激活）：←/→ 循环，Home/End 到头尾。
 * 标签要带 data-tab-id；只有选中的那个 tabIndex=0，其余 -1。
 */
export function onTabKeys(event: KeyboardEvent<HTMLElement>, ids: string[], current: string, select: (id: string) => void) {
  const index = ids.indexOf(current);
  const target = event.key === 'ArrowRight' ? index + 1
    : event.key === 'ArrowLeft' ? index - 1
    : event.key === 'Home' ? 0
    : event.key === 'End' ? ids.length - 1
    : null;
  if (target === null || !ids.length) return;
  event.preventDefault();
  const id = ids[(target + ids.length) % ids.length];
  const list = event.currentTarget.closest('[role="tablist"]') ?? event.currentTarget;
  const tab = Array.from(list.querySelectorAll<HTMLElement>('[data-tab-id]')).find(element => element.dataset.tabId === id);
  tab?.focus();
  if (id !== current) select(id);
}
