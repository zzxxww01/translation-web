// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { documentApi } from '../api';
import { ProjectExport } from './ProjectExport';

vi.mock('@/shared/hooks/useErrorHandler', () => ({ useErrorHandler: () => ({ handleError: vi.fn() }) }));
vi.mock('sonner', () => ({ toast: { success: vi.fn() } }));

const overrideLabel = '仍然导出（忽略本次QA）';
let root: Root;
let host: HTMLDivElement;
let client: QueryClient;
let download: ReturnType<typeof vi.spyOn>;

function button(label: string) {
  return Array.from(host.querySelectorAll('button')).find(el => el.textContent === label);
}
async function click(label: string) {
  expect(button(label)).toBeDefined();
  await act(async () => { button(label)!.click(); });
}
async function settle() {
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 30)); });
}
async function render(projectId = 'project-a') {
  await act(async () => {
    root.render(<QueryClientProvider client={client}><ProjectExport key={projectId} projectId={projectId} /></QueryClientProvider>);
  });
  await click('导出文章');
}

beforeEach(() => {
  vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  vi.stubGlobal('URL', Object.assign(URL, {
    createObjectURL: vi.fn(() => 'blob:export'), revokeObjectURL: vi.fn(),
  }));
  download = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  host = document.createElement('div');
  document.body.appendChild(host);
  root = createRoot(host);
  client = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
});
afterEach(async () => {
  await act(async () => root.unmount());
  host.remove();
  client.clear();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('ProjectExport QA override', () => {
  it('requires QA blocking and confirmation, downloads once, and restores normal QA for the next export', async () => {
    const api = vi.spyOn(documentApi, 'exportProject')
      .mockRejectedValueOnce(new Error('导出被 QA 阻断：术语不一致'))
      .mockResolvedValue({ content: '# 译文', path: 'out.md', filename: 'out.md', format: 'zh' });
    await render();
    expect(button(overrideLabel)).toBeUndefined();
    await click('导出');
    await settle();
    expect(api).toHaveBeenLastCalledWith('project-a', 'zh', false);
    expect(button(overrideLabel)).toBeDefined();
    vi.mocked(window.confirm).mockReturnValueOnce(false);
    await click(overrideLabel);
    expect(api).toHaveBeenCalledTimes(1);
    await click(overrideLabel);
    await settle();
    expect(window.confirm).toHaveBeenCalledTimes(2);
    expect(api).toHaveBeenLastCalledWith('project-a', 'zh', true);
    expect(download).toHaveBeenCalledTimes(1);
    expect(button(overrideLabel)).toBeUndefined();
    await click('导出');
    await settle();
    expect(api).toHaveBeenLastCalledWith('project-a', 'zh', false);
  });

  it.each(['网络连接失败', 'Internal Server Error'])('does not offer override for %s', async message => {
    vi.spyOn(documentApi, 'exportProject').mockRejectedValue(new Error(message));
    await render();
    await click('导出');
    await settle();
    expect(button(overrideLabel)).toBeUndefined();
    expect(window.confirm).not.toHaveBeenCalled();
    expect(download).not.toHaveBeenCalled();
  });

  it('does not carry a blocked export into another project', async () => {
    vi.spyOn(documentApi, 'exportProject').mockRejectedValue(new Error('导出被 QA 阻断'));
    await render();
    await click('导出');
    await settle();
    expect(button(overrideLabel)).toBeDefined();
    await render('project-b');
    expect(button(overrideLabel)).toBeUndefined();
  });

  it('hides override and disables export while the confirmed retry is pending', async () => {
    const api = vi.spyOn(documentApi, 'exportProject')
      .mockRejectedValueOnce(new Error('导出被 QA 阻断'))
      .mockImplementationOnce(() => new Promise(() => {}));
    await render();
    await click('导出');
    await settle();
    await click(overrideLabel);
    await settle();
    expect(api).toHaveBeenCalledTimes(2);
    expect(button(overrideLabel)).toBeUndefined();
    expect(button('导出中...')?.disabled).toBe(true);
  });
});
