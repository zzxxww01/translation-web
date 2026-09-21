// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, useLayoutEffect } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useImmersiveEditor } from './useImmersiveEditor';
import { documentApi } from '../api';
import { useDocumentStore } from '../../../shared/stores';
import { ParagraphStatus } from '../../../shared/constants';
import type { Paragraph, Section } from '../../../shared/types';

vi.mock('../api', () => ({ documentApi: {
  updateParagraph: vi.fn(), translateParagraph: vi.fn(), confirmParagraph: vi.fn(), batchTranslateParagraphs: vi.fn(),
} }));
vi.mock('sonner', () => ({ toast: { info: vi.fn(), success: vi.fn(), error: vi.fn() } }));

const paragraph: Paragraph = { id: 'p1', index: 0, source: 'source', translation: 'original', status: ParagraphStatus.TRANSLATED };
const section: Section = { section_id: 's1', title: 'Section', is_complete: false, approved_count: 0, total_paragraphs: 1, paragraphs: [paragraph] };
let editor: ReturnType<typeof useImmersiveEditor>;
let root: Root;
let host: HTMLElement;
let query: QueryClient;
const key = 'immersive-draft:A:s1:p1';
function Harness() {
  const value = useImmersiveEditor({ projectId: 'A', sectionId: 's1', paragraphs: section.paragraphs! });
  useLayoutEffect(() => { editor = value; });
  return null;
}
async function mount() {
  await act(async () => { root.render(<QueryClientProvider client={query}><Harness /></QueryClientProvider>); });
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: unknown) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

describe('immersive editing concurrent results', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubGlobal('IS_REACT_ACT_ENVIRONMENT', true);
    window.sessionStorage.clear();
    vi.mocked(documentApi.updateParagraph).mockImplementation(async (_p, _s, id, data) => ({ id, translation: data.translation, status: ParagraphStatus.MODIFIED }));
    vi.mocked(documentApi.confirmParagraph).mockResolvedValue({});
    useDocumentStore.setState({ currentProject: { id: 'A', title: 'A' }, currentSection: section, sections: [section] });
    query = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
    host = document.createElement('div'); document.body.append(host); root = createRoot(host);
  });
  afterEach(async () => {
    await act(async () => root.unmount());
    host.remove();query.clear();vi.clearAllMocks();vi.unstubAllGlobals();vi.useRealTimers();
  });
  it('saves text typed immediately before save in the same event', async () => {
    await mount();
    await act(async () => { editor.updateDraft('p1', 'new'); await editor.saveNow('p1'); });
    expect(documentApi.updateParagraph).toHaveBeenLastCalledWith('A','s1','p1',expect.objectContaining({ translation: 'new' }));
    expect(editor.dirtyMap.p1).toBe(false);
  });
  it('does not overwrite typing made during a retranslation', async () => {
    const pending = deferred<Awaited<ReturnType<typeof documentApi.translateParagraph>>>();
    vi.mocked(documentApi.translateParagraph).mockReturnValue(pending.promise);
    await mount();
    await act(async () => editor.queueRetranslate('p1'));
    await act(async () => editor.updateDraft('p1','typed while waiting'));
    await act(async () => pending.resolve({ id:'p1',translation:'model result',status:ParagraphStatus.TRANSLATED }));
    expect(editor.drafts.p1).toBe('typed while waiting');
    expect(editor.dirtyMap.p1).toBe(true);
    expect(window.sessionStorage.getItem(key)).toContain('typed while waiting');
  });
  it('does not clear newer edits after confirming an earlier version', async () => {
    const pending = deferred<unknown>();vi.mocked(documentApi.confirmParagraph).mockReturnValue(pending.promise);
    await mount();
    let confirmation!: ReturnType<typeof editor.confirmParagraph>;
    await act(async () => { confirmation = editor.confirmParagraph('p1'); });
    await act(async () => editor.updateDraft('p1','newer draft'));
    await act(async () => { pending.resolve({}); await confirmation; });
    expect(editor.drafts.p1).toBe('newer draft');expect(editor.dirtyMap.p1).toBe(true);
    expect(window.sessionStorage.getItem(key)).toContain('newer draft');
  });
  it('does not mutate a different project after a late save response', async () => {
    const pending=deferred<Awaited<ReturnType<typeof documentApi.updateParagraph>>>();
    vi.mocked(documentApi.updateParagraph).mockReturnValueOnce(pending.promise);
    await mount();let save!: Promise<void>;
    await act(async () => {editor.updateDraft('p1','A edit');save=editor.saveNow('p1');});
    useDocumentStore.setState({currentProject:{id:'B',title:'B'},currentSection:{...section,paragraphs:[{...paragraph,translation:'B text'}]}});
    await act(async () => {pending.resolve({id:'p1',translation:'A edit',status:ParagraphStatus.MODIFIED});await save;});
    expect(useDocumentStore.getState().currentSection?.paragraphs?.[0].translation).toBe('B text');
  });
  it('recovers unknown-baseline local drafts without automatically overwriting remote data', async () => {
    window.sessionStorage.setItem(key,'old local draft');
    await mount();
    await act(async () => vi.advanceTimersByTimeAsync(2000));
    expect(editor.drafts.p1).toBe('old local draft');
    expect(editor.saveErrorMap.p1).toContain('手动保存');
    expect(documentApi.updateParagraph).not.toHaveBeenCalled();
    await act(async () => editor.saveNow('p1'));
    expect(documentApi.updateParagraph).toHaveBeenCalledOnce();
  });
  it('does not leak a rejected tracker promise or start duplicate retranslation', async () => {
    vi.mocked(documentApi.translateParagraph).mockRejectedValue(new Error('model failed'));
    await mount();
    await act(async () => {editor.queueRetranslate('p1');editor.queueRetranslate('p1');});
    expect(documentApi.translateParagraph).toHaveBeenCalledOnce();
    expect(editor.retranslateErrorMap.p1).toBe('model failed');
  });
  it('registers a batch barrier before waiting for an in-flight save', async () => {
    const savePending=deferred<Awaited<ReturnType<typeof documentApi.updateParagraph>>>();
    const batchPending=deferred<Awaited<ReturnType<typeof documentApi.batchTranslateParagraphs>>>();
    vi.mocked(documentApi.updateParagraph).mockReturnValueOnce(savePending.promise);
    vi.mocked(documentApi.batchTranslateParagraphs).mockReturnValueOnce(batchPending.promise);
    await mount();let save!:Promise<void>;let batch!:Promise<void>;let confirmation!:ReturnType<typeof editor.confirmParagraph>;
    await act(async () => {editor.updateDraft('p1','draft');save=editor.saveNow('p1');editor.toggleSelection('p1');});
    await act(async () => {batch=editor.batchRetranslate();confirmation=editor.confirmParagraph('p1');});
    expect(documentApi.batchTranslateParagraphs).not.toHaveBeenCalled();
    await act(async () => {savePending.resolve({id:'p1',translation:'draft',status:ParagraphStatus.MODIFIED});await save;});
    expect(documentApi.batchTranslateParagraphs).toHaveBeenCalledOnce();
    expect(documentApi.confirmParagraph).not.toHaveBeenCalled();
    await act(async () => {batchPending.resolve({translations:[{id:'p1',translation:'model',status:ParagraphStatus.TRANSLATED}],success_count:1,error_count:0,errors:[]});await batch;await confirmation;});
    expect(documentApi.confirmParagraph).toHaveBeenCalledOnce();
  });
});
