// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'sonner';
import { RunList } from './components/RunList';
import { normalizeCatalog } from './agents';
import type { RunMeta } from './types';

vi.mock('sonner', () => ({ toast: { error: vi.fn() } }));

const run = (id: string, status: RunMeta['status']): RunMeta => ({
  id, skill: 'four-step-translate', title: `对话 ${id}`, status, created_at: 1_793_000_000, updated_at: 1_793_000_000,
  session_id: null, error: null, harness: 'codex', awaiting_reply: false,
} as RunMeta);

describe('RunList delete', () => {
  let root: Root;
  let host: HTMLDivElement;
  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    host = document.createElement('div');
    document.body.appendChild(host);
    root = createRoot(host);
  });
  afterEach(() => {
    act(() => root.unmount());
    host.remove();
    document.body.innerHTML = '';
  });

  const render = (onDelete: (id: string) => Promise<void>, onPin = vi.fn(async () => undefined),
    runs = [run('20261028-000000-aaaaaa', 'idle'), run('20261028-000001-bbbbbb', 'running')]) => act(() => root.render(
    <RunList runs={runs}
      catalog={normalizeCatalog([])} selectedId={null} onSelect={vi.fn()} onNew={vi.fn()} onDelete={onDelete} onPin={onPin} />,
  ));
  const deleteButtons = () => Array.from(host.querySelectorAll<HTMLButtonElement>('button[aria-label^="删除对话"]'));

  it('confirms before deleting and passes the run id', async () => {
    const onDelete = vi.fn(async () => undefined);
    render(onDelete);
    const [idle] = deleteButtons();
    await act(async () => { idle.click(); });
    expect(document.body.textContent).toContain('删除这个对话？');
    const confirm = Array.from(document.querySelectorAll('button')).find(b => b.textContent === '删除')!;
    await act(async () => { confirm.click(); });
    expect(onDelete).toHaveBeenCalledWith('20261028-000000-aaaaaa');
  });

  it('pins and unpins, and marks pinned conversations', async () => {
    const onPin = vi.fn(async () => undefined);
    render(vi.fn(), onPin, [{ ...run('20261028-000000-aaaaaa', 'idle'), pinned_at: 1_793_000_100 }, run('20261028-000001-bbbbbb', 'running')]);
    const unpin = host.querySelector<HTMLButtonElement>('button[aria-label^="取消置顶"]')!;
    const pin = host.querySelector<HTMLButtonElement>('button[aria-label^="置顶"]')!;
    expect(host.querySelectorAll('[aria-label="已置顶"]')).toHaveLength(1);
    await act(async () => { unpin.click(); });
    await act(async () => { pin.click(); });
    expect(onPin).toHaveBeenNthCalledWith(1, '20261028-000000-aaaaaa', false);
    expect(onPin).toHaveBeenNthCalledWith(2, '20261028-000001-bbbbbb', true);
  });

  it('does not let a running conversation be deleted', () => {
    render(vi.fn());
    const [, running] = deleteButtons();
    expect(running.disabled).toBe(true);
    expect(running.title).toBe('先停止再删除');
  });

  const open = async () => { await act(async () => { deleteButtons()[0].click(); }); };
  const button = (label: string) => Array.from(document.querySelectorAll('button')).find(b => b.textContent === label)!;

  it('does not delete just by opening the dialog', async () => {
    const onDelete = vi.fn(async () => undefined);
    render(onDelete);
    await open();
    expect(document.body.textContent).toContain('删除这个对话？');
    expect(onDelete).not.toHaveBeenCalled();
  });

  it('cancel closes without deleting', async () => {
    const onDelete = vi.fn(async () => undefined);
    render(onDelete);
    await open();
    await act(async () => { button('取消').click(); });
    expect(onDelete).not.toHaveBeenCalled();
    expect(document.body.textContent).not.toContain('删除这个对话？');
  });

  it('keeps the dialog open and shows the error when deleting fails', async () => {
    const onDelete = vi.fn(async () => { throw new Error('服务器拒绝'); });
    render(onDelete);
    await open();
    await act(async () => { button('删除').click(); });
    expect(toast.error).toHaveBeenCalledWith('服务器拒绝');
    expect(document.body.textContent).toContain('删除这个对话？');
  });
});
