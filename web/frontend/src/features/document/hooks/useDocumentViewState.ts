import { useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import type { Section } from '@/shared/types';

export type DocumentView = 'glossary' | 'term-review' | null;

interface UseDocumentViewStateOptions {
  currentSectionId?: string | null;
  sections: Section[];
  selectedSectionId: string | null;
}

export function useDocumentViewState({
  currentSectionId,
  sections,
  selectedSectionId,
}: UseDocumentViewStateOptions) {
  const [searchParams, setSearchParams] = useSearchParams();
  const isImmersiveMode = searchParams.get('immersive') === '1';
  const activeView = (searchParams.get('view') as DocumentView) || null;

  const setView = useCallback(
    (view: DocumentView) => {
      const next = new URLSearchParams(searchParams);
      if (view) {
        next.set('view', view);
      } else {
        next.delete('view');
      }
      setSearchParams(next);
    },
    [searchParams, setSearchParams]
  );

  const updateRouteParams = useCallback(
    ({
      view,
      immersive,
    }: {
      view?: DocumentView;
      immersive?: boolean;
    }) => {
      const next = new URLSearchParams(searchParams);
      if (view !== undefined) {
        if (view) {
          next.set('view', view);
        } else {
          next.delete('view');
        }
      }

      if (immersive !== undefined) {
        if (immersive) {
          next.set('immersive', '1');
        } else {
          next.delete('immersive');
        }
      }

      setSearchParams(next);
    },
    [searchParams, setSearchParams]
  );

  const activeSectionId = useMemo(() => {
    const fallbackSectionId = isImmersiveMode ? currentSectionId ?? null : null;
    const candidateSectionId = selectedSectionId ?? fallbackSectionId;
    if (!candidateSectionId) {
      return null;
    }
    return sections.some(section => section.section_id === candidateSectionId) ||
      candidateSectionId === currentSectionId
      ? candidateSectionId
      : null;
  }, [currentSectionId, isImmersiveMode, sections, selectedSectionId]);

  return {
    activeSectionId,
    activeView,
    isImmersiveMode,
    searchParams,
    setView,
    updateRouteParams,
  };
}
