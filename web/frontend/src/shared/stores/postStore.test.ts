import { beforeEach, describe, expect, it } from 'vitest';

import { TranslationVersionType } from '../constants';
import { usePostStore } from './postStore';


describe('postStore version lineage', () => {
  beforeEach(() => {
    usePostStore.getState().clear();
  });

  it('increments the source revision only when source text changes', () => {
    const store = usePostStore.getState();

    store.setOriginalText('source A');
    expect(usePostStore.getState().sourceRevision).toBe(1);

    usePostStore.getState().setOriginalText('source A');
    expect(usePostStore.getState().sourceRevision).toBe(1);

    usePostStore.getState().setOriginalText('source B');
    expect(usePostStore.getState().sourceRevision).toBe(2);
  });

  it('records the source revision and text on generated versions', () => {
    const store = usePostStore.getState();
    store.setOriginalText('source A');

    const versionId = usePostStore
      .getState()
      .addVersion('translation A', TranslationVersionType.TRANSLATION);
    const version = usePostStore
      .getState()
      .versions.find(item => item.id === versionId);

    expect(version).toMatchObject({
      sourceRevision: 1,
      sourceText: 'source A',
      content: 'translation A',
    });

    usePostStore.getState().setOriginalText('source B');
    expect(version?.sourceRevision).toBeLessThan(
      usePostStore.getState().sourceRevision
    );
  });

  it('saves an edited translation as a child version', () => {
    const store = usePostStore.getState();
    store.setOriginalText('source A');
    const parentId = usePostStore
      .getState()
      .addVersion('translation A', TranslationVersionType.TRANSLATION);

    usePostStore.getState().setEditedContent('manual revision');
    const childId = usePostStore.getState().saveEdit();
    const child = usePostStore
      .getState()
      .versions.find(item => item.id === childId);

    expect(child).toMatchObject({
      parentVersionId: parentId,
      sourceRevision: 1,
      sourceText: 'source A',
      content: 'manual revision',
      type: TranslationVersionType.MANUAL,
    });
    expect(usePostStore.getState().isEdited).toBe(false);
  });
});
