import { describe, expect, it } from 'vitest';

import { isTranslationRunActive } from './translationStatus';


describe('isTranslationRunActive', () => {
  it('treats a claimed starting slot as active', () => {
    expect(
      isTranslationRunActive(
        {
          status: 'starting',
          active_project_id: 'project-a',
          active_run_id: null,
        },
        'project-a'
      )
    ).toBe(true);
  });

  it('does not attach another project active run to the current project', () => {
    expect(
      isTranslationRunActive(
        {
          status: 'processing',
          active_project_id: 'project-a',
        },
        'project-b'
      )
    ).toBe(false);
  });
});
