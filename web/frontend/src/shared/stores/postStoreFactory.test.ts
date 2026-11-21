import { expect, it } from 'vitest';
import { createPostStore, postSnapshot } from './postStore';
import { TranslationVersionType } from '../constants';

it('each Slack post gets its own store with the same version logic, and snapshots round-trip', () => {
  const a = createPostStore();
  const b = createPostStore();
  a.getState().setOriginalText('AI racks are heavy');
  const v1 = a.getState().addVersion('AI 机柜太重了', TranslationVersionType.TRANSLATION);
  expect(a.getState().currentVersionId).toBe(v1);
  expect(b.getState().versions).toEqual([]);  // 互不影响

  const snapshot = postSnapshot(a.getState());
  b.getState().loadSnapshot(JSON.parse(JSON.stringify(snapshot)), 's_C1_1_2', 3);
  const loaded = b.getState();
  expect(loaded.originalText).toBe('AI racks are heavy');
  expect(loaded.versions[0].createdAt).toBeInstanceOf(Date);
  expect([loaded.draftId, loaded.draftRev]).toEqual(['s_C1_1_2', 3]);
  b.getState().clear();
  expect([b.getState().draftId, b.getState().versions.length]).toEqual([null, 0]);
});
