// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
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

  const render = (onDelete: (id: string) => Promise<void>) => act(() => root.render(
    <RunList runs={[run('20261028-000000-aaaaaa', 'idle'), run('20261028-000001-bbbbbb', 'running')]}
      catalog={normalizeCatalog([])} selectedId={null} onSelect={vi.fn()} onNew={vi.fn()} onDelete={onDelete} />,
  ));
  const deleteButtons = () => Array.from(host.querySelectorAll<HTMLButtonElement>('button[aria-label^="删除对话"]'));

  it('confirms before deleting and passes the run id', async () => {
    const onDelete = vi.fn(async () => undefined);
    render(onDelete);
    const [idle] = deleteButtons();
    await act(async () => { idle.click(); });
    expect(document.body.textContent).toContain('服务器上会保留存档');
    const confirm = Array.from(document.querySelectorAll('button')).find(b => b.textContent === '删除')!;
    await act(async () => { confirm.click(); });
    expect(onDelete).toHaveBeenCalledWith('20261028-000000-aaaaaa');
  });

  it('does not let a running conversation be deleted', () => {
    render(vi.fn());
    const [, running] = deleteButtons();
    expect(running.disabled).toBe(true);
    expect(running.title).toBe('先停止再删除');
  });
});
