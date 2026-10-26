// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { RuntimeUpdatesPanel } from './components/RuntimeUpdatesPanel';

const api = vi.hoisted(() => ({ runtimeStatus: vi.fn(), checkUpdates: vi.fn(), updateRuntime: vi.fn() }));
vi.mock('./api', () => ({ skillsApi: api }));
const snapshot = (active = false) => ({ active, checking: false, checked_at: 1, runtimes: [
  { harness: 'codex', label: 'Codex', current: '0.1.0', latest: '0.2.0', update_available: true, can_update: true,
    reason: null, error: null, status: active ? 'updating' : 'ready', message: null, updated_at: null },
  { harness: 'claude', label: 'Claude Code', current: '2.0.0', latest: '2.0.0', update_available: false, can_update: true,
    reason: null, error: null, status: 'ready', message: null, updated_at: null },
] });
let root: Root;
let host: HTMLDivElement;
const click = async (el: HTMLButtonElement) => act(async () => {
  el.click();
  await new Promise(resolve => setTimeout(resolve, 30));
});
const buttons = () => Array.from(host.querySelectorAll('button'));

beforeEach(async () => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  api.runtimeStatus.mockReset().mockResolvedValue(snapshot());
  api.checkUpdates.mockReset().mockResolvedValue(snapshot());
  api.updateRuntime.mockReset().mockResolvedValue(snapshot(true));
  host = document.createElement('div');
  document.body.appendChild(host);
  root = createRoot(host);
  await act(async () => {
    root.render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <RuntimeUpdatesPanel />
    </QueryClientProvider>);
  });
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 30)); });
});
afterEach(() => { act(() => root.unmount()); host.remove(); });

it('checks versions and updates only the chosen runtime, disabling controls during upgrade', async () => {
  expect(host.textContent).toContain('0.1.0');
  expect(host.textContent).toContain('0.2.0');
  await click(buttons().find(button => button.textContent === '检查更新')!);
  expect(api.checkUpdates).toHaveBeenCalledOnce();
  await click(buttons().find(button => button.getAttribute('aria-label') === '更新 Codex')!);
  expect(api.updateRuntime).toHaveBeenCalledWith('codex');
  expect(buttons().filter(button => button.getAttribute('aria-label')?.startsWith('更新')).every(button => button.disabled)).toBe(true);
});

it('shows a server refusal without claiming the upgrade succeeded', async () => {
  api.updateRuntime.mockRejectedValueOnce(new Error('还有对话正在运行'));
  await click(buttons().find(button => button.getAttribute('aria-label') === '更新 Codex')!);
  expect(host.textContent).toContain('还有对话正在运行');
  expect(host.textContent).not.toContain('更新完成');
});
