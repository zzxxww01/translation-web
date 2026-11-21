// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, expect, it, vi } from 'vitest';
import { UNAUTHORIZED_EVENT } from '@/shared/api/client';
import { AuthGate } from './AuthGate';

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

async function renderGate(fetchMock: ReturnType<typeof vi.fn>) {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  vi.stubGlobal('fetch', fetchMock);
  const host = document.createElement('div');
  const root = createRoot(host);
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  await act(async () => root.render(
    <QueryClientProvider client={client}><AuthGate><p>站内内容</p></AuthGate></QueryClientProvider>
  ));
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
  return { host, root };
}

afterEach(() => vi.unstubAllGlobals());

it('shows only the password form until signed in', async () => {
  const fetchMock = vi.fn(async () => jsonResponse(401, { detail: '请先登录' }));
  const { host, root } = await renderGate(fetchMock);
  expect(host.textContent).toContain('口令');
  expect(host.textContent).not.toContain('站内内容');
  // 没登录时 /me 自己的 401 不会触发重查循环
  const calls = fetchMock.mock.calls.length;
  await act(async () => { window.dispatchEvent(new Event(UNAUTHORIZED_EVENT)); });
  expect(fetchMock.mock.calls.length).toBe(calls);
  act(() => root.unmount());
});

it('renders the site when signed in and falls back to login after a 401', async () => {
  let signedIn = true;
  const fetchMock = vi.fn(async () => signedIn
    ? jsonResponse(200, { ok: true, max_active: 2, max_upload_mb: 95 })
    : jsonResponse(401, { detail: '请先登录' }));
  const { host, root } = await renderGate(fetchMock);
  expect(host.textContent).toContain('站内内容');

  signedIn = false;
  await act(async () => { window.dispatchEvent(new Event(UNAUTHORIZED_EVENT)); });
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
  expect(host.textContent).toContain('口令');
  expect(host.textContent).not.toContain('站内内容');
  act(() => root.unmount());
});
