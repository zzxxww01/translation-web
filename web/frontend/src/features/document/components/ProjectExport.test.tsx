// @vitest-environment jsdom
import { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { documentApi } from '../api';
import { ProjectExport } from './ProjectExport';
import { toast } from 'sonner';

vi.mock('@/shared/hooks/useErrorHandler', () => ({ useErrorHandler: () => ({ handleError: vi.fn() }) }));
vi.mock('sonner', () => ({ toast: { success: vi.fn(), warning: vi.fn() } }));

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
  vi.spyOn(documentApi, 'getProject').mockResolvedValue({ id: 'project-a', title: 'Demo' });
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
  it('shows missing counts before export and keeps the incomplete warning after override download', async () => {
    const report = {
      is_complete: false, missing_count: 3, missing_title_count: 1,
      missing_body_count: 2, missing_document_title_count: 0,
      items: [{ kind: 'section_title' as const, section_id: 's1', section_title: 'Market', source_preview: 'Market' }],
    };
    vi.mocked(documentApi.getProject).mockResolvedValue({ id: 'project-a', title: 'Demo', translation_completeness: report });
    vi.spyOn(documentApi, 'exportProject')
      .mockRejectedValueOnce(new Error('导出被 QA 阻断：中文稿未完成，章节标题 1，正文 2'))
      .mockResolvedValueOnce({ content: '# Market', path: 'out.md', filename: 'out.md', format: 'zh', translation_completeness: report, is_incomplete: true });
    await render();
    await settle();
    expect(host.textContent).toContain('中文稿未完成');
    expect(host.textContent).toContain('章节标题 1');
    expect(host.textContent).toContain('正文 2');
    await click('导出');
    await settle();
    await click(overrideLabel);
    await settle();
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('未完成稿'));
    expect(download).toHaveBeenCalledTimes(1);
    expect(host.textContent).toContain('已下载未完成稿');
    expect(host.textContent).toContain('缺译 3 处');
    expect(toast.warning).toHaveBeenCalledWith(expect.stringContaining('未完成稿'));
  });
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
