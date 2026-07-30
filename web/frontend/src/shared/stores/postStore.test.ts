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

  it('appends a version without stealing focus or clearing edits when makeCurrent is false', () => {
    const store = usePostStore.getState();
    store.setOriginalText('source A');
    const baseId = usePostStore
      .getState()
      .addVersion('translation A', TranslationVersionType.TRANSLATION);

    usePostStore.getState().setEditedContent('用户正在手改的内容');
    expect(usePostStore.getState().isEdited).toBe(true);

    const lateId = usePostStore
      .getState()
      .addVersion('迟到的优化结果', TranslationVersionType.OPTIMIZATION, '按可读性优化', {
        makeCurrent: false,
        parentVersionId: baseId,
      });

    const state = usePostStore.getState();
    // 结果已落库，但当前版本与未保存的编辑都不受影响
    expect(state.versions.map(v => v.id)).toContain(lateId);
    expect(state.currentVersionId).toBe(baseId);
    expect(state.isEdited).toBe(true);
    expect(state.editedContent).toBe('用户正在手改的内容');
  });

  it('keeps pendingAction and isLoading in sync and resets them on clear', () => {
    usePostStore.getState().setPendingAction('optimize');
    expect(usePostStore.getState().isLoading).toBe(true);
    expect(usePostStore.getState().pendingStartedAt).not.toBeNull();

    usePostStore.getState().clear();
    expect(usePostStore.getState().pendingAction).toBeNull();
    expect(usePostStore.getState().isLoading).toBe(false);
    expect(usePostStore.getState().pendingStartedAt).toBeNull();
  });
});
