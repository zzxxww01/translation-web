import { afterEach, describe, expect, it, vi } from 'vitest';

import { ApiClient, ApiErrorWrapper } from './client';


describe('ApiClient retry safety', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('retries a transient GET response', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'temporary' }), { status: 503 })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 })
      );
    vi.stubGlobal('fetch', fetchMock);
    const client = new ApiClient('/api', { retryCount: 1, retryDelay: 0 });

    await expect(client.get<{ ok: boolean }>('/health')).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('does not replay a failed mutation unless the caller opts in', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'temporary' }), { status: 503 })
    );
    vi.stubGlobal('fetch', fetchMock);
    const client = new ApiClient('/api', { retryCount: 2, retryDelay: 0 });

    await expect(client.post('/projects', { name: 'Demo' })).rejects.toBeInstanceOf(
      ApiErrorWrapper
    );
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it('allows an explicitly retryable mutation', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: 'temporary' }), { status: 503 })
      )
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), { status: 200 })
      );
    vi.stubGlobal('fetch', fetchMock);
    const client = new ApiClient('/api', { retryCount: 1, retryDelay: 0 });

    await expect(
      client.post<{ ok: boolean }>('/idempotent-action', {}, { retry: true })
    ).resolves.toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
