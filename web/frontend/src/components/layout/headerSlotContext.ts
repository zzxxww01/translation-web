import { createContext } from 'react';

/** 顶栏右侧「页面操作位」的 DOM 节点；AppLayout 提供，PageActions 往里放按钮 */
export const HeaderSlotContext = createContext<HTMLElement | null>(null);
