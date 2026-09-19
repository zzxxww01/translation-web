import { afterEach, describe, expect, it, vi } from 'vitest';
import { documentApi } from './api';

afterEach(() => vi.unstubAllGlobals());

describe('document export query parameters', () => {
  it('defaults to QA enabled and scopes override to a single POST', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({
      content: 'translation', path: 'out.md', filename: 'out.md', format: 'zh',
    }), { status: 200 })));
    vi.stubGlobal('fetch', fetchMock);
    await documentApi.exportProject('project-a');
    await documentApi.exportProject('project-a', 'zh', true);
    await documentApi.exportProject('project-a', 'en');
    expect(fetchMock).toHaveBeenCalledTimes(3);
    const urls = fetchMock.mock.calls.map(call => new URL(String(call[0]), 'http://localhost'));
    expect(urls.map(url => url.searchParams.get('allow_qa_override'))).toEqual(['false', 'true', 'false']);
    expect(urls.map(url => url.searchParams.get('format'))).toEqual(['zh', 'zh', 'en']);
    for (const [url, options] of fetchMock.mock.calls) {
      expect(String(url)).toContain('/projects/project-a/export?');
      expect(options.method).toBe('POST');
    }
  });
});
