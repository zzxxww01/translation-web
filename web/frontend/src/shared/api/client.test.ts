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

describe('ApiClient lifecycle and serialization', () => {
  afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });
  it('times out a stalled response body, not only response headers', async () => {
    vi.useFakeTimers();
    const fetchMock = vi.fn().mockResolvedValue(new Response(new ReadableStream()));
    vi.stubGlobal('fetch', fetchMock);
    const promise = new ApiClient('/api', { timeout: 20 }).get('/slow');
    const assertion = expect(promise).rejects.toMatchObject({ status: 408 });
    await vi.advanceTimersByTimeAsync(21);
    await assertion;
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(fetchMock.mock.calls[0][1].signal.aborted).toBe(true);
  });
  it('preserves cancellation while consuming a stalled body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new ReadableStream())));
    const controller = new AbortController();
    const promise = new ApiClient('/api').get('/slow', { signal: controller.signal });
    const assertion = expect(promise).rejects.toMatchObject({ name: 'AbortError' });
    await Promise.resolve();
    controller.abort();
    await assertion;
  });
  it('does not start a request for an already cancelled signal', async () => {
    const fetchMock = vi.fn(); vi.stubGlobal('fetch', fetchMock);
    const controller = new AbortController(); controller.abort();
    await expect(new ApiClient().get('/slow', { signal: controller.signal })).rejects.toMatchObject({ name: 'AbortError' });
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it('merges existing query parameters and Headers and preserves credentials', async () => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ ok: true })); vi.stubGlobal('fetch', fetchMock);
    await new ApiClient('/api').post('/edit?existing=1#anchor', {}, {
      params: { next: 'A B' }, headers: new Headers({ 'X-Request': 'yes' }), credentials: 'include',
    });
    expect(fetchMock.mock.calls[0][0]).toBe('/api/edit?existing=1&next=A+B#anchor');
    expect(new Headers(fetchMock.mock.calls[0][1].headers).get('x-request')).toBe('yes');
    expect(fetchMock.mock.calls[0][1].credentials).toBe('include');
  });
  it('normalizes non-Error transport failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(null));
    await expect(new ApiClient().get('/broken')).rejects.toThrow('请求失败');
  });
  it('formats structured validation details', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ detail: [{ msg: 'field required' }] }, { status: 422 })));
    await expect(new ApiClient().post('/x', {})).rejects.toThrow('field required');
  });
});

describe('ApiClient upload lifecycle', () => {
  class FakeXHR extends EventTarget {
    static last: FakeXHR;
    upload = new EventTarget(); status = 200; responseText = '{}';
    timeout = 0; withCredentials = false; headers = new Headers();
    constructor() { super(); FakeXHR.last = this; }
    open = vi.fn(); send = vi.fn();
    setRequestHeader(key: string, value: string) { this.headers.set(key,value); }
    abort() { this.dispatchEvent(new Event('abort')); }
  }
  afterEach(() => vi.unstubAllGlobals());
  it('cancels uploads without reporting timeout or accepting a late response', async () => {
    vi.stubGlobal('XMLHttpRequest',FakeXHR);
    const controller=new AbortController();
    const result=new ApiClient().upload('/file', new File(['x'],'a.txt'), {signal:controller.signal});
    const rejected=expect(result).rejects.toMatchObject({name:'AbortError'});
    controller.abort();
    FakeXHR.last.dispatchEvent(new Event('load'));
    await rejected;
  });
  it('rejects malformed successful upload responses', async () => {
    vi.stubGlobal('XMLHttpRequest',FakeXHR);
    const result=new ApiClient().upload('/file',new File(['x'],'a.txt'));
    const rejected=expect(result).rejects.toThrow('数据格式无效');
    FakeXHR.last.responseText='not JSON';FakeXHR.last.dispatchEvent(new Event('load'));
    await rejected;
  });
  it('supports no-content responses and lets the browser set multipart boundaries', async () => {
    vi.stubGlobal('XMLHttpRequest',FakeXHR);
    const result=new ApiClient().upload('/file',new File(['x'],'a.txt'),{credentials:'include',headers:new Headers({'X-Trace':'1','Content-Type':'wrong'})});
    FakeXHR.last.status=204;FakeXHR.last.responseText='';FakeXHR.last.dispatchEvent(new Event('load'));
    await expect(result).resolves.toBeUndefined();
    expect(FakeXHR.last.withCredentials).toBe(true);
    expect(FakeXHR.last.headers.get('x-trace')).toBe('1');
    expect(FakeXHR.last.headers.has('content-type')).toBe(false);
  });
});
