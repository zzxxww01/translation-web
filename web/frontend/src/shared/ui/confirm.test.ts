// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { confirmAction, useConfirmStore } from './confirm';

afterEach(() => {
  useConfirmStore.setState({ hosted: false, request: null });
  vi.restoreAllMocks();
});

describe('confirmAction', () => {
  it('falls back to window.confirm when no ConfirmHost is mounted', async () => {
    const native = vi.spyOn(window, 'confirm').mockReturnValue(true);
    await expect(confirmAction({ title: '删除？', description: '找不回来' })).resolves.toBe(true);
    expect(native).toHaveBeenCalledWith('删除？\n\n找不回来');
  });

  it('opens the in-page dialog when hosted and resolves with the answer', async () => {
    const native = vi.spyOn(window, 'confirm');
    useConfirmStore.setState({ hosted: true });
    const answer = confirmAction({ title: '仍然导出？' });
    const request = useConfirmStore.getState().request;
    expect(request?.title).toBe('仍然导出？');
    request?.resolve(true);
    await expect(answer).resolves.toBe(true);
    expect(native).not.toHaveBeenCalled();
  });

  it('cancels a pending question when a new one arrives', async () => {
    useConfirmStore.setState({ hosted: true });
    const first = confirmAction({ title: '第一个' });
    const second = confirmAction({ title: '第二个' });
    await expect(first).resolves.toBe(false);
    useConfirmStore.getState().request?.resolve(true);
    await expect(second).resolves.toBe(true);
  });
});
