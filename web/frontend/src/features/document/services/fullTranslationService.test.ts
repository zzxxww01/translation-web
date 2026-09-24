import { afterEach, describe, expect, it, vi } from 'vitest';

import { FullTranslationService } from './fullTranslationService';


function streamResponse(
  signal: AbortSignal,
  events: string[],
  keepOpen: boolean
): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(`data: ${event}\n\n`));
      }
      if (keepOpen) {
        signal.addEventListener(
          'abort',
          () => controller.close(),
          { once: true }
        );
      } else {
        controller.close();
      }
    },
  });
  return new Response(stream, { status: 200 });
}


describe('FullTranslationService project switching', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('detaches the previous stream without cancelling its server task', async () => {
    const service = new FullTranslationService();
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        const signal = init?.signal;
        if (!signal) {
          throw new Error('expected an AbortSignal');
        }
        if (url.includes('project-a')) {
          return streamResponse(
            signal,
            [JSON.stringify({ type: 'start', total: 2 })],
            true
          );
        }
        return streamResponse(
          signal,
          [
            JSON.stringify({ type: 'start', total: 1 }),
            JSON.stringify({ type: 'complete', translated_count: 1, total: 1 }),
          ],
          false
        );
      }
    );
    vi.stubGlobal('fetch', fetchMock);

    const firstRun = service.startTranslation(
      'project-a',
      vi.fn(),
      vi.fn()
    );
    await vi.waitFor(() => {
      expect(service.getProjectId()).toBe('project-a');
    });

    const secondComplete = vi.fn();
    await service.startTranslation(
      'project-b',
      vi.fn(),
      secondComplete
    );
    await firstRun;

    const requestedUrls = fetchMock.mock.calls.map(call => String(call[0]));
    expect(requestedUrls).toEqual([
      '/api/projects/project-a/translate-four-step',
      '/api/projects/project-b/translate-four-step',
    ]);
    expect(requestedUrls.some(url => url.endsWith('/stop'))).toBe(false);
    expect(secondComplete).toHaveBeenCalledOnce();
    expect(service.isTranslating()).toBe(false);
  });

  it('detaches only the expected project without sending a stop request', async () => {
    const service = new FullTranslationService();
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        if (!init?.signal) {
          throw new Error('expected an AbortSignal');
        }
        return streamResponse(
          init.signal,
          [JSON.stringify({ type: 'start', total: 2 })],
          true
        );
      }
    );
    vi.stubGlobal('fetch', fetchMock);

    const run = service.startTranslation(
      'project-a',
      vi.fn(),
      vi.fn()
    );
    await vi.waitFor(() => {
      expect(service.getProjectId()).toBe('project-a');
    });

    expect(service.detachTranslation('project-b')).toBe(false);
    expect(service.isTranslating()).toBe(true);
    expect(service.detachTranslation('project-a')).toBe(true);
    await run;

    expect(service.isTranslating()).toBe(false);
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(String(fetchMock.mock.calls[0][0])).toBe(
      '/api/projects/project-a/translate-four-step'
    );
  });

  it('explicitly stops a normal translation on the server', async () => {
    const service = new FullTranslationService();
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith('/translation-cancel')) {
          return new Response(JSON.stringify({ status: 'cancelling' }), {
            status: 200,
          });
        }
        if (!init?.signal) {
          throw new Error('expected an AbortSignal');
        }
        return streamResponse(
          init.signal,
          [JSON.stringify({ type: 'start', total: 2 })],
          true
        );
      }
    );
    vi.stubGlobal('fetch', fetchMock);

    const run = service.startTranslation(
      'project-a',
      vi.fn(),
      vi.fn(),
      'normal'
    );
    await vi.waitFor(() => {
      expect(service.getProjectId()).toBe('project-a');
    });

    await service.stopTranslation();
    await run;

    expect(fetchMock.mock.calls.map(call => String(call[0]))).toEqual([
      '/api/projects/project-a/translate-stream',
      '/api/projects/project-a/translation-cancel',
    ]);
    expect(service.isTranslating()).toBe(false);
  });

  it('rejects fatal SSE errors and notifies completion once', async () => {
    const service = new FullTranslationService();
    const onComplete = vi.fn();
    vi.stubGlobal(
      'fetch',
      vi.fn(async (_input: string | URL | Request, init?: RequestInit) => {
        if (!init?.signal) {
          throw new Error('expected an AbortSignal');
        }
        return streamResponse(
          init.signal,
          [
            JSON.stringify({ type: 'start', total: 1 }),
            JSON.stringify({ type: 'error', error: 'model unavailable' }),
          ],
          false
        );
      })
    );

    await expect(
      service.startTranslation('project-a', vi.fn(), onComplete)
    ).rejects.toThrow('model unavailable');

    expect(onComplete).toHaveBeenCalledOnce();
    expect(service.isTranslating()).toBe(false);
  });

  it('keeps observing the run when server cancellation is rejected', async () => {
    const service = new FullTranslationService();
    const fetchMock = vi.fn(
      async (input: string | URL | Request, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith('/translation-cancel')) {
          return new Response('failed', { status: 500 });
        }
        if (!init?.signal) {
          throw new Error('expected an AbortSignal');
        }
        return streamResponse(
          init.signal,
          [JSON.stringify({ type: 'start', total: 2 })],
          true
        );
      }
    );
    vi.stubGlobal('fetch', fetchMock);

    const run = service.startTranslation(
      'project-a',
      vi.fn(),
      vi.fn(),
      'normal'
    );
    await vi.waitFor(() => {
      expect(service.getProjectId()).toBe('project-a');
    });

    await expect(service.stopTranslation()).rejects.toThrow(
      'server-side cancellation: 500'
    );
    expect(service.isTranslating()).toBe(true);

    service.detachTranslation('project-a');
    await run;
  });
});

describe('FullTranslationService race and stream cleanup', () => {
  afterEach(() => { vi.unstubAllGlobals(); });
  it('a delayed cancel response for A does not detach a newly started B', async () => {
    const service = new FullTranslationService();
    let cancelDone!: (response: Response) => void;
    vi.stubGlobal('fetch', vi.fn(async (input: string, init?: RequestInit) => {
      if (input.endsWith('/translation-cancel')) return new Promise<Response>(resolve => { cancelDone = resolve; });
      return streamResponse(init!.signal!, [JSON.stringify({ type: 'start', total: 2 })], true);
    }));
    const first = service.startTranslation('A', vi.fn(), vi.fn());
    await vi.waitFor(() => expect(service.getProgress()?.total).toBe(2));
    const cancellation = service.stopTranslation();
    const second = service.startTranslation('B', vi.fn(), vi.fn());
    await vi.waitFor(() => expect(service.getProjectId()).toBe('B'));
    cancelDone(Response.json({ status: 'cancelling' }));
    await cancellation;
    expect(service.isTranslating()).toBe(true);
    expect(service.getProjectId()).toBe('B');
    service.detachTranslation('B');
    await Promise.all([first, second]);
  });
  it('rejects EOF without a terminal event', async () => {
    vi.stubGlobal('fetch', vi.fn(async (_: string, init?: RequestInit) => streamResponse(init!.signal!, ['{"type":"start","total":1}'], false)));
    const done = vi.fn();
    await expect(new FullTranslationService().startTranslation('A', vi.fn(), done)).rejects.toThrow('before a terminal event');
    expect(done).toHaveBeenCalledOnce();
  });
  it('cancels a still-open stream after the terminal event', async () => {
    const cancel = vi.fn();
    const stream = new ReadableStream<Uint8Array>({
      start(controller) { controller.enqueue(new TextEncoder().encode('data: {"type":"complete"}\n\n')); }, cancel,
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(stream)));
    await new FullTranslationService().startTranslation('A', vi.fn(), vi.fn());
    expect(cancel).toHaveBeenCalledOnce();
    expect(stream.locked).toBe(false);
  });
  it('accepts zero progress and fails malformed data instead of silently discarding it', async () => {
    const service = new FullTranslationService();
    const progress: number[] = [];
    vi.stubGlobal('fetch', vi.fn(async (_: string, init?: RequestInit) => streamResponse(init!.signal!, [
      '{"type":"progress","current":9,"total":10}', '{"type":"progress","current":0,"total":10}', 'not-json',
    ], false)));
    await expect(service.startTranslation('A', () => progress.push(service.getProgress()!.current), vi.fn())).rejects.toThrow();
    expect(progress).toEqual([9, 0]);
  });
});
