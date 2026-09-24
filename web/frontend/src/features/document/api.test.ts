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


describe('longform cost options', () => {
  it('sends explicit phase scope and compact review without changing retranslation scope', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({
      status: 'started', project_id: 'project-a',
    }), { status: 200 })));
    vi.stubGlobal('fetch', fetchMock);
    await documentApi.startLongformWorkflow('project-a', 'four-step', 'my-model', undefined, {
      model_scope: 'draft', efficiency: { compact_review: true, max_stage_calls: 10 },
    });
    const request = JSON.parse(fetchMock.mock.calls[0][1].body);
    expect(request.model).toBe('my-model');
    expect(request.model_scope).toBe('draft');
    expect(request.efficiency).toEqual({ compact_review: true, max_stage_calls: 10 });
    expect(request.retranslate_scope).not.toBe('all');
  });
});

describe('longform efficiency controls', () => {
  it('sends explicit controls without changing retranslation scope', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ status: 'started' }), { status: 202 }));
    vi.stubGlobal('fetch', fetchMock);
    await documentApi.startLongformWorkflow('project-a', 'four-step', 'chosen',
      { scope: 'section', sectionIds: ['s1'] },
      { model_scope: 'draft', compact_review: true, prescan_concurrency: 2, max_run_calls: 50 });
    const [, options] = fetchMock.mock.calls[0];
    const body = JSON.parse(options.body);
    expect(body.efficiency).toEqual({ model_scope: 'draft', compact_review: true, prescan_concurrency: 2, max_run_calls: 50 });
    expect(body.model).toBe('chosen');
    expect(body.retranslate_scope).toBe('section');
    expect(body.retranslate_section_ids).toEqual(['s1']);
  });

  it('does not reuse controls from a previous request', async () => {
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({ status: 'started' }), { status: 202 })));
    vi.stubGlobal('fetch', fetchMock);
    await documentApi.startLongformWorkflow('project-a', 'four-step', undefined, undefined, { compact_review: true });
    await documentApi.startLongformWorkflow('project-b', 'four-step');
    const body = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(body).not.toHaveProperty('efficiency');
    expect(body.retranslate_scope).toBe('resume');
  });
});
