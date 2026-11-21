import { useContext, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { HeaderSlotContext } from './headerSlotContext';

/** 顶栏右侧的「页面操作位」：各页面把自己的按钮放进顶栏，不再另占一行标题栏 */
export function PageActions({ children }: { children: ReactNode }) {
  const slot = useContext(HeaderSlotContext);
  if (!slot) return null;
  return createPortal(children, slot);
}
