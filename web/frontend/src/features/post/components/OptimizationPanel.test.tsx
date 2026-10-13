// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { OptimizationPanel } from './OptimizationPanel';

let host: HTMLDivElement;
let root: Root;

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  host = document.createElement('div');
  document.body.appendChild(host);
  root = createRoot(host);
});

afterEach(async () => {
  await act(async () => root.unmount());
  host.remove();
  vi.unstubAllGlobals();
});

describe('OptimizationPanel', () => {
  it('exposes the coherence shortcut and sends its stable option id', async () => {
    const onOptimize = vi.fn().mockResolvedValue(true);
    await act(async () => {
      root.render(
        <OptimizationPanel
          onOptimize={onOptimize}
          isLoading={false}
          isOptimizing={false}
          hasVersions
          hasOriginal
          customInstruction=""
          onCustomInstructionChange={vi.fn()}
        />,
      );
    });

    const coherence = Array.from(host.querySelectorAll('button')).find(button =>
      button.textContent?.includes('更连贯'),
    );
    expect(coherence).toBeDefined();
    await act(async () => coherence!.click());
    expect(onOptimize).toHaveBeenCalledWith({ optionId: 'coherence' });
  });
});
