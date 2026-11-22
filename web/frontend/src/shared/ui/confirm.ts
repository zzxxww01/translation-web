import { create } from 'zustand';

export interface ConfirmOptions {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** 删除、覆盖这类找不回来的操作：确认按钮用红色 */
  destructive?: boolean;
}

export interface ConfirmState {
  hosted: boolean;
  request: (ConfirmOptions & { resolve: (ok: boolean) => void }) | null;
}

export const useConfirmStore = create<ConfirmState>(() => ({ hosted: false, request: null }));

/**
 * 站内确认框，替代浏览器原生 window.confirm（样式和全站一致，手机上也好按）。
 * 页面上没挂 <ConfirmHost />（比如单测里单独渲染组件）时退回 window.confirm。
 */
export function confirmAction(options: ConfirmOptions): Promise<boolean> {
  const state = useConfirmStore.getState();
  if (!state.hosted) {
    const text = options.description ? `${options.title}\n\n${options.description}` : options.title;
    return Promise.resolve(window.confirm(text));
  }
  // 上一个还没答就来了新的：旧的按取消处理
  state.request?.resolve(false);
  return new Promise(resolve => useConfirmStore.setState({ request: { ...options, resolve } }));
}
