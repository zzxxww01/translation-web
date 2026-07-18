import { beforeEach, describe, expect, it } from 'vitest';

import { ParagraphStatus } from '../constants';
import type { Section } from '../types';
import { useDocumentStore } from './documentStore';

const sectionB: Section = {
  section_id: 'shared-section',
  title: 'Project B section',
  is_complete: false,
  total_paragraphs: 1,
  approved_count: 0,
  paragraphs: [
    {
      id: 'shared-paragraph',
      index: 0,
      source: 'Project B source',
      translation: 'Project B translation',
      status: ParagraphStatus.TRANSLATED,
    },
  ],
};

describe('documentStore project-scoped translation state', () => {
  beforeEach(() => {
    useDocumentStore.getState().reset();
  });

  it('ignores late progress and completion from a replaced project run', () => {
    const store = useDocumentStore.getState();
    store.startFullTranslate('project-a', 10);
    store.setFullTranslateProgressForProject('project-a', {
      current: 3,
      total: 10,
    });

    useDocumentStore.getState().startFullTranslate('project-b', 5);
    useDocumentStore
      .getState()
      .setFullTranslateProgressForProject('project-a', {
        current: 9,
        total: 10,
      });
    useDocumentStore.getState().endFullTranslate('project-a');

    expect(useDocumentStore.getState()).toMatchObject({
      isFullTranslating: true,
      fullTranslateProjectId: 'project-b',
      fullTranslateProgress: { current: 0, total: 5 },
    });

    useDocumentStore.getState().endFullTranslate('project-b');
    expect(useDocumentStore.getState()).toMatchObject({
      isFullTranslating: false,
      fullTranslateProjectId: null,
      fullTranslateProgress: null,
    });
  });

  it('does not apply a translated paragraph to a different current project', () => {
    const store = useDocumentStore.getState();
    store.setCurrentProject({ id: 'project-b', title: 'Project B' });
    store.setSections([sectionB]);
    store.setCurrentSection(sectionB);

    const staleWriteApplied = useDocumentStore
      .getState()
      .updateParagraphInProject(
        'project-a',
        'shared-section',
        'shared-paragraph',
        { translation: 'Project A translation' }
      );

    expect(staleWriteApplied).toBe(false);
    expect(
      useDocumentStore.getState().currentSection?.paragraphs?.[0].translation
    ).toBe('Project B translation');

    const currentWriteApplied = useDocumentStore
      .getState()
      .updateParagraphInProject(
        'project-b',
        'shared-section',
        'shared-paragraph',
        { translation: 'Updated Project B translation' }
      );

    expect(currentWriteApplied).toBe(true);
    expect(
      useDocumentStore.getState().currentSection?.paragraphs?.[0].translation
    ).toBe('Updated Project B translation');
  });
});
