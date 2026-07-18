import { describe, expect, it } from 'vitest';

import { TranslationVersionType } from '@/shared/constants';
import type { TranslationVersion } from '@/shared/types';
import { getOptimizationHistory } from './versionLineage';


function version(
  id: string,
  options: Partial<TranslationVersion> = {}
): TranslationVersion {
  return {
    id,
    versionNumber: 1,
    content: id,
    type: TranslationVersionType.OPTIMIZATION,
    sourceRevision: 1,
    sourceText: 'source A',
    isCurrent: false,
    createdAt: new Date(0),
    ...options,
  };
}


describe('getOptimizationHistory', () => {
  it('uses only ancestors from the selected source revision and branch', () => {
    const versions = [
      version('a-root', {
        type: TranslationVersionType.TRANSLATION,
      }),
      version('a-one', {
        parentVersionId: 'a-root',
        instruction: 'A first',
      }),
      version('a-other-branch', {
        parentVersionId: 'a-one',
        instruction: 'A other branch',
      }),
      version('a-selected', {
        parentVersionId: 'a-one',
        instruction: 'A selected branch',
      }),
      version('b-root', {
        type: TranslationVersionType.TRANSLATION,
        sourceRevision: 2,
        sourceText: 'source B',
      }),
      version('b-one', {
        parentVersionId: 'b-root',
        sourceRevision: 2,
        sourceText: 'source B',
        instruction: 'B first',
      }),
    ];

    expect(getOptimizationHistory(versions, 'a-selected')).toEqual([
      { role: 'user', content: 'A first' },
      { role: 'user', content: 'A selected branch' },
    ]);
    expect(getOptimizationHistory(versions, 'b-one')).toEqual([
      { role: 'user', content: 'B first' },
    ]);
  });

  it('keeps only the latest requested number of ancestor instructions', () => {
    const versions = [
      version('root', { type: TranslationVersionType.TRANSLATION }),
      version('one', { parentVersionId: 'root', instruction: 'one' }),
      version('two', { parentVersionId: 'one', instruction: 'two' }),
      version('three', { parentVersionId: 'two', instruction: 'three' }),
      version('four', { parentVersionId: 'three', instruction: 'four' }),
    ];

    expect(getOptimizationHistory(versions, 'four', 3)).toEqual([
      { role: 'user', content: 'two' },
      { role: 'user', content: 'three' },
      { role: 'user', content: 'four' },
    ]);
  });
});
