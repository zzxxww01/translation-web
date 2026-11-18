// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useRunEvents } from './hooks';

class FakeEventSource {
  static CLOSED = 2;
  static instances: FakeEventSource[] = [];
  readyState = 1;
  onopen: (() => void) | null = null;
  onmessage: ((message: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  listeners = new Map<string, () => void>();
  constructor(public url: string) {
    FakeEventSource.instances.push(this);
  }
  addEventListener(name: string, fn: () => void) {
    this.listeners.set(name, fn);
  }
  close() {
    this.readyState = FakeEventSource.CLOSED;
  }
  open() {
    this.onopen?.();
  }
  send(seq: number) {
    this.onmessage?.({ data: JSON.stringify({ seq, ts: 0, type: 'text', text: `t${seq}`, parent: null }) });
  }
  emit(name: string) {
    this.listeners.get(name)?.();
  }
}

let rendered: number[] = [];
function Probe({ runId }: { runId: string }) {
  const { events } = useRunEvents(runId);
  rendered.push(events.length);
  return null;
}

describe('useRunEvents', () => {
  let root: Root;
  beforeEach(() => {
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    vi.useFakeTimers();
    vi.stubGlobal('EventSource', FakeEventSource);
    FakeEventSource.instances = [];
    rendered = [];
    root = createRoot(document.createElement('div'));
  });
  afterEach(() => {
    act(() => root.unmount());
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('renders the replayed history once, on ready', () => {
    act(() => root.render(<Probe runId="run-a" />));
    const source = FakeEventSource.instances[0];
    expect(source.url).toContain('after=0');
    act(() => {
      source.open();
      for (let seq = 1; seq <= 50; seq++) {
        source.send(seq);
        vi.advanceTimersByTime(20);
      }
    });
    // 回放中途不画
    expect(rendered.at(-1)).toBe(0);
    act(() => source.emit('ready'));
    expect(rendered.at(-1)).toBe(50);

    // 回放之后的实时事件照常小批渲染
    act(() => {
      source.send(51);
      vi.advanceTimersByTime(100);
    });
    expect(rendered.at(-1)).toBe(51);
  });

  it('falls back to rendering when the server never sends ready', () => {
    act(() => root.render(<Probe runId="run-b" />));
    const source = FakeEventSource.instances[0];
    act(() => {
      source.open();
      source.send(1);
      vi.advanceTimersByTime(3_100);
    });
    expect(rendered.at(-1)).toBe(1);
  });

  it('reopening a run starts from cache and only subscribes to newer events', () => {
    act(() => root.render(<Probe runId="run-c" />));
    act(() => {
      const source = FakeEventSource.instances[0];
      source.open();
      source.send(1);
      source.send(2);
      source.emit('ready');
    });
    act(() => root.render(<Probe key="other" runId="run-d" />));
    rendered = [];
    act(() => root.render(<Probe key="again" runId="run-c" />));
    expect(rendered[0]).toBe(2);
    expect(FakeEventSource.instances.at(-1)!.url).toContain('after=2');
  });
});
