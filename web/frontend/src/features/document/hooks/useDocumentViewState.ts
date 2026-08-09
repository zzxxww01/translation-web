import { useCallback, useMemo } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import type { Section } from '@/shared/types';

export type DocumentView = 'glossary' | 'term-review' | null;
export type DocumentMode = 'immersive' | null;

interface UseDocumentViewStateOptions {
  sections: Section[];
}

interface RouteUpdate {
  projectId?: string | null;
  sectionId?: string | null;
  paragraphId?: string | null;
  mode?: DocumentMode;
  view?: DocumentView;
}

interface RouteUpdateOptions {
  replace?: boolean;
}

function documentPath(projectId?: string | null, sectionId?: string | null): string {
  if (!projectId) return '/document';
  if (!sectionId) return `/document/${encodeURIComponent(projectId)}`;
  return `/document/${encodeURIComponent(projectId)}/${encodeURIComponent(sectionId)}`;
}

export function useDocumentViewState({ sections }: UseDocumentViewStateOptions) {
  const navigate = useNavigate();
  const params = useParams<{ projectId?: string; sectionId?: string }>();
  const [searchParams] = useSearchParams();

  const activeProjectId = params.projectId ?? null;
  const requestedSectionId = params.sectionId ?? null;
  const requestedParagraphId = searchParams.get('paragraph');
  const activeView = (searchParams.get('view') as DocumentView) || null;
  const mode = searchParams.get('mode');
  const isImmersiveMode = mode === 'immersive' || searchParams.get('immersive') === '1';

  const activeSectionId = useMemo(() => {
    if (!requestedSectionId) return null;
    if (sections.length === 0) return requestedSectionId;
    return sections.some(section => section.section_id === requestedSectionId)
      ? requestedSectionId
      : null;
  }, [requestedSectionId, sections]);

  const updateRouteParams = useCallback(
    (updates: RouteUpdate, options: RouteUpdateOptions = {}) => {
      const nextProjectId =
        updates.projectId !== undefined ? updates.projectId : activeProjectId;
      const projectChanged =
        updates.projectId !== undefined && updates.projectId !== activeProjectId;
      const nextSectionId = projectChanged
        ? updates.sectionId ?? null
        : updates.sectionId !== undefined
          ? updates.sectionId
          : requestedSectionId;
      const next = new URLSearchParams(searchParams);

      if (updates.paragraphId !== undefined || projectChanged || updates.sectionId !== undefined) {
        const nextParagraphId =
          projectChanged || updates.sectionId !== undefined
            ? updates.paragraphId ?? null
            : updates.paragraphId;
        if (nextParagraphId) {
          next.set('paragraph', nextParagraphId);
        } else {
          next.delete('paragraph');
        }
      }

      if (updates.mode !== undefined || projectChanged) {
        const nextMode = projectChanged ? updates.mode ?? null : updates.mode;
        if (nextMode === 'immersive') {
          next.set('mode', 'immersive');
        } else {
          next.delete('mode');
        }
        next.delete('immersive');
      }

      if (updates.view !== undefined || projectChanged) {
        const nextView = projectChanged ? updates.view ?? null : updates.view;
        if (nextView) {
          next.set('view', nextView);
        } else {
          next.delete('view');
        }
      }

      const query = next.toString();
      void navigate(
        {
          pathname: documentPath(nextProjectId, nextSectionId),
          search: query ? `?${query}` : '',
        },
        { replace: options.replace }
      );
    },
    [activeProjectId, navigate, requestedSectionId, searchParams]
  );

  const setView = useCallback(
    (view: DocumentView) => {
      updateRouteParams({ view });
    },
    [updateRouteParams]
  );

  return {
    activeProjectId,
    activeSectionId,
    activeParagraphId: requestedParagraphId,
    requestedSectionId,
    activeView,
    isImmersiveMode,
    searchParams,
    setView,
    updateRouteParams,
  };
}
