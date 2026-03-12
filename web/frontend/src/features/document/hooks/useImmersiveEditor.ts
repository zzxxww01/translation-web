import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useToast } from '../../../components/ui';
import { ParagraphStatus } from '../../../shared/constants';
import { useDocumentStore } from '../../../shared/stores';
import type { Paragraph, Section } from '../../../shared/types';
import { documentApi } from '../api';

const AUTO_SAVE_DELAY_MS = 800;
const MAX_PARALLEL_RETRANSLATE = 3;
const MAX_BATCH_SELECTION = 50;

type BooleanStateMap = Record<string, boolean>;
type ErrorStateMap = Record<string, string | null>;

interface RetranslateTask {
  paragraphId: string;
  instruction?: string;
}

interface UseImmersiveEditorOptions {
  projectId: string;
  sectionId: string;
  paragraphs: Paragraph[];
}

interface ParagraphSnapshot {
  translation: string;
  confirmed: string;
  status: ParagraphStatus;
}

function toErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return 'Request failed. Please retry.';
}

function pruneMapByIds<T>(input: Record<string, T>, validIds: Set<string>): Record<string, T> {
  const next: Record<string, T> = {};
  Object.entries(input).forEach(([key, value]) => {
    if (validIds.has(key)) {
      next[key] = value;
    }
  });
  return next;
}

export function useImmersiveEditor({ projectId, sectionId, paragraphs }: UseImmersiveEditorOptions) {
  const { showToast } = useToast();
  const queryClient = useQueryClient();
  const updateParagraphInSection = useDocumentStore(state => state.updateParagraphInSection);

  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [dirtyMap, setDirtyMap] = useState<BooleanStateMap>({});
  const [savingMap, setSavingMap] = useState<BooleanStateMap>({});
  const [saveErrorMap, setSaveErrorMap] = useState<ErrorStateMap>({});
  const [retranslatingMap, setRetranslatingMap] = useState<BooleanStateMap>({});
  const [retranslateErrorMap, setRetranslateErrorMap] = useState<ErrorStateMap>({});
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);

  const saveTimersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const retranslateQueueRef = useRef<RetranslateTask[]>([]);
  const activeRetranslateRef = useRef(0);
  const processRetranslateQueueRef = useRef<() => void>(() => {});
  const saveParagraphRef = useRef<(paragraphId: string) => Promise<void>>(async () => {});
  const paragraphOperationRef = useRef<Record<string, Promise<unknown>>>({});

  const draftsRef = useRef(drafts);
  const dirtyMapRef = useRef(dirtyMap);
  const retranslatingMapRef = useRef(retranslatingMap);
  const paragraphsByIdRef = useRef<Record<string, Paragraph>>({});
  const paragraphSnapshotsRef = useRef<Record<string, ParagraphSnapshot>>({});

  const paragraphIds = useMemo(() => new Set(paragraphs.map(paragraph => paragraph.id)), [paragraphs]);

  useEffect(() => {
    draftsRef.current = drafts;
  }, [drafts]);

  useEffect(() => {
    dirtyMapRef.current = dirtyMap;
  }, [dirtyMap]);

  useEffect(() => {
    retranslatingMapRef.current = retranslatingMap;
  }, [retranslatingMap]);

  useEffect(() => {
    const paragraphMap: Record<string, Paragraph> = {};
    const nextSnapshots: Record<string, ParagraphSnapshot> = {};
    const changedParagraphIds = new Set<string>();

    paragraphs.forEach(paragraph => {
      paragraphMap[paragraph.id] = paragraph;

      const nextSnapshot: ParagraphSnapshot = {
        translation: paragraph.translation ?? '',
        confirmed: paragraph.confirmed ?? '',
        status: paragraph.status,
      };
      const previousSnapshot = paragraphSnapshotsRef.current[paragraph.id];
      if (
        previousSnapshot &&
        (
          previousSnapshot.translation !== nextSnapshot.translation ||
          previousSnapshot.confirmed !== nextSnapshot.confirmed ||
          previousSnapshot.status !== nextSnapshot.status
        )
      ) {
        changedParagraphIds.add(paragraph.id);
      }
      nextSnapshots[paragraph.id] = nextSnapshot;
    });
    paragraphsByIdRef.current = paragraphMap;
    paragraphSnapshotsRef.current = nextSnapshots;

    setDrafts(previous => {
      const next = { ...previous };
      paragraphs.forEach(paragraph => {
        if (!dirtyMapRef.current[paragraph.id]) {
          next[paragraph.id] = paragraph.translation ?? '';
        } else if (next[paragraph.id] === undefined) {
          next[paragraph.id] = paragraph.translation ?? '';
        }
      });
      return pruneMapByIds(next, paragraphIds);
    });

    setDirtyMap(previous => pruneMapByIds(previous, paragraphIds));
    setSavingMap(previous => pruneMapByIds(previous, paragraphIds));
    setSaveErrorMap(previous => {
      const next = pruneMapByIds(previous, paragraphIds);
      changedParagraphIds.forEach(paragraphId => {
        delete next[paragraphId];
      });
      return next;
    });
    setRetranslatingMap(previous => pruneMapByIds(previous, paragraphIds));
    setRetranslateErrorMap(previous => {
      const next = pruneMapByIds(previous, paragraphIds);
      changedParagraphIds.forEach(paragraphId => {
        delete next[paragraphId];
      });
      return next;
    });
  }, [paragraphIds, paragraphs]);

  useEffect(() => {
    const saveTimers = saveTimersRef.current;
    return () => {
      Object.values(saveTimers).forEach(timerId => clearTimeout(timerId));
    };
  }, []);

  const updateSectionQueryCache = useCallback(
    (paragraphId: string, updates: Partial<Paragraph>) => {
      if (!projectId || !sectionId) return;
      queryClient.setQueryData<Section | undefined>(
        ['section', projectId, sectionId],
        previous => {
          if (!previous?.paragraphs) return previous;
          return {
            ...previous,
            paragraphs: previous.paragraphs.map(paragraph =>
              paragraph.id === paragraphId ? { ...paragraph, ...updates } : paragraph
            ),
          };
        }
      );
    },
    [projectId, queryClient, sectionId]
  );

  const applyParagraphUpdate = useCallback(
    (paragraphId: string, updates: Partial<Paragraph>) => {
      updateParagraphInSection(sectionId, paragraphId, updates);
      updateSectionQueryCache(paragraphId, updates);
    },
    [sectionId, updateParagraphInSection, updateSectionQueryCache]
  );

  const cancelPendingSave = useCallback((paragraphId: string) => {
    const existingTimer = saveTimersRef.current[paragraphId];
    if (!existingTimer) return;
    clearTimeout(existingTimer);
    delete saveTimersRef.current[paragraphId];
  }, []);

  const runParagraphOperation = useCallback(
    <T,>(paragraphId: string, operation: () => Promise<T>): Promise<T> => {
      const previous = paragraphOperationRef.current[paragraphId] ?? Promise.resolve();
      const next = previous.catch(() => undefined).then(() => operation());

      const tracked: Promise<unknown> = next.finally(() => {
        if (paragraphOperationRef.current[paragraphId] === tracked) {
          delete paragraphOperationRef.current[paragraphId];
        }
      });

      paragraphOperationRef.current[paragraphId] = tracked;
      return next;
    },
    []
  );

  const scheduleAutoSave = useCallback((paragraphId: string) => {
    const existingTimer = saveTimersRef.current[paragraphId];
    if (existingTimer) {
      clearTimeout(existingTimer);
    }
    saveTimersRef.current[paragraphId] = setTimeout(() => {
      void saveParagraphRef.current(paragraphId);
    }, AUTO_SAVE_DELAY_MS);
  }, []);

  const performSaveParagraph = useCallback(
    async (paragraphId: string) => {
      if (!projectId || !sectionId) return;
      if (!dirtyMapRef.current[paragraphId]) return;

      const paragraph = paragraphsByIdRef.current[paragraphId];
      if (!paragraph) return;

      const translation = draftsRef.current[paragraphId] ?? '';
      const currentTranslation = paragraph.confirmed ?? paragraph.translation ?? '';
      const status =
        paragraph.status === ParagraphStatus.PENDING && translation.trim()
          ? ParagraphStatus.TRANSLATED
          : translation !== currentTranslation &&
              (paragraph.status === ParagraphStatus.APPROVED || Boolean(paragraph.confirmed))
            ? ParagraphStatus.MODIFIED
          : undefined;

      setSavingMap(previous => ({ ...previous, [paragraphId]: true }));

      try {
        const result = await documentApi.updateParagraph(projectId, sectionId, paragraphId, {
          translation,
          status,
          edit_source: 'immersive_auto_save',
          source_text: paragraph.source,
        });

        const persistedTranslation = result.translation ?? translation;
        const persistedStatus = result.status ?? paragraph.status;
        applyParagraphUpdate(paragraphId, {
          translation: persistedTranslation,
          status: persistedStatus,
          confirmed: result.confirmed ?? (persistedStatus === ParagraphStatus.APPROVED ? persistedTranslation : undefined),
        });

        setSaveErrorMap(previous => {
          const next = { ...previous };
          delete next[paragraphId];
          return next;
        });

        const latestDraft = draftsRef.current[paragraphId] ?? '';
        if (latestDraft === translation) {
          setDirtyMap(previous => ({ ...previous, [paragraphId]: false }));
        } else {
          scheduleAutoSave(paragraphId);
        }
      } catch (error) {
        setSaveErrorMap(previous => ({
          ...previous,
          [paragraphId]: toErrorMessage(error),
        }));
      } finally {
        setSavingMap(previous => ({ ...previous, [paragraphId]: false }));
      }
    },
    [applyParagraphUpdate, projectId, scheduleAutoSave, sectionId]
  );

  const saveParagraph = useCallback(
    async (paragraphId: string) =>
      runParagraphOperation(paragraphId, () => performSaveParagraph(paragraphId)),
    [performSaveParagraph, runParagraphOperation]
  );

  useEffect(() => {
    saveParagraphRef.current = saveParagraph;
  }, [saveParagraph]);

  const updateDraft = useCallback(
    (paragraphId: string, value: string) => {
      setDrafts(previous => ({ ...previous, [paragraphId]: value }));
      setDirtyMap(previous => ({ ...previous, [paragraphId]: true }));
      setSaveErrorMap(previous => {
        const next = { ...previous };
        delete next[paragraphId];
        return next;
      });

      scheduleAutoSave(paragraphId);
    },
    [scheduleAutoSave]
  );

  const saveNow = useCallback(
    async (paragraphId: string) => {
      cancelPendingSave(paragraphId);
      await saveParagraph(paragraphId);
    },
    [cancelPendingSave, saveParagraph]
  );

  const saveAllNow = useCallback(async () => {
    const pendingIds = Object.entries(dirtyMapRef.current)
      .filter(([, isDirty]) => isDirty)
      .map(([paragraphId]) => paragraphId);

    await Promise.all(pendingIds.map(paragraphId => saveNow(paragraphId)));
  }, [saveNow]);

  const processRetranslateQueue = useCallback(() => {
    if (!projectId || !sectionId) return;

    while (
      activeRetranslateRef.current < MAX_PARALLEL_RETRANSLATE &&
      retranslateQueueRef.current.length > 0
    ) {
      const task = retranslateQueueRef.current.shift();
      if (!task) break;

      const { paragraphId, instruction } = task;
      const paragraph = paragraphsByIdRef.current[paragraphId];
      if (!paragraph) continue;

      activeRetranslateRef.current += 1;
      cancelPendingSave(paragraphId);
      setRetranslatingMap(previous => ({ ...previous, [paragraphId]: true }));
      setRetranslateErrorMap(previous => {
        const next = { ...previous };
        delete next[paragraphId];
        return next;
      });

      const wasDirty = dirtyMapRef.current[paragraphId];
      const previousDraft = draftsRef.current[paragraphId] ?? '';

      void runParagraphOperation(paragraphId, async () => {
        const result = await documentApi.translateParagraph(
          projectId,
          sectionId,
          paragraphId,
          instruction
        );
        const translation = result.translation ?? '';
        const persistedStatus = result.status ?? ParagraphStatus.TRANSLATED;

        setDrafts(previous => ({ ...previous, [paragraphId]: translation }));
        setDirtyMap(previous => ({ ...previous, [paragraphId]: false }));
        setSaveErrorMap(previous => {
          const next = { ...previous };
          delete next[paragraphId];
          return next;
        });

        applyParagraphUpdate(paragraphId, {
          translation,
          status: persistedStatus,
          confirmed: result.confirmed ?? (persistedStatus === ParagraphStatus.APPROVED ? translation : undefined),
        });

        if (wasDirty && previousDraft !== translation) {
          showToast(`Paragraph #${paragraph.index} was replaced by retranslation`, 'info');
        }
      })
        .catch(error => {
          setRetranslateErrorMap(previous => ({
            ...previous,
            [paragraphId]: toErrorMessage(error),
          }));
          showToast('Retranslate failed. Please retry.', 'error');
        })
        .finally(() => {
          activeRetranslateRef.current -= 1;
          setRetranslatingMap(previous => ({ ...previous, [paragraphId]: false }));
          processRetranslateQueueRef.current();
        });
    }
  }, [
    applyParagraphUpdate,
    cancelPendingSave,
    projectId,
    runParagraphOperation,
    sectionId,
    showToast,
  ]);

  useEffect(() => {
    processRetranslateQueueRef.current = processRetranslateQueue;
  }, [processRetranslateQueue]);

  const queueRetranslate = useCallback(
    (paragraphId: string, instruction?: string) => {
      const isAlreadyQueued = retranslateQueueRef.current.some(task => task.paragraphId === paragraphId);
      if (isAlreadyQueued || retranslatingMapRef.current[paragraphId]) {
        return;
      }

      cancelPendingSave(paragraphId);
      retranslateQueueRef.current.push({ paragraphId, instruction });
      processRetranslateQueueRef.current();
    },
    [cancelPendingSave]
  );

  const toggleSelectionMode = useCallback(() => {
    setIsSelectionMode(previous => {
      if (previous) {
        setSelectedIds(new Set());
      }
      return !previous;
    });
  }, []);

  const toggleSelection = useCallback((paragraphId: string) => {
    setSelectedIds(previous => {
      const next = new Set(previous);
      if (next.has(paragraphId)) {
        next.delete(paragraphId);
      } else {
        if (next.size >= MAX_BATCH_SELECTION) {
          return previous;
        }
        next.add(paragraphId);
      }
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(
    (candidateIds?: string[]) => {
      const baseIds = candidateIds ?? paragraphs.map(paragraph => paragraph.id);
      const idsToSelect = baseIds.slice(0, MAX_BATCH_SELECTION);
      const hasSelectedAll = idsToSelect.length > 0 && idsToSelect.every(id => selectedIds.has(id));
      setSelectedIds(hasSelectedAll ? new Set() : new Set(idsToSelect));
    },
    [paragraphs, selectedIds]
  );

  const batchRetranslate = useCallback(
    async (instruction?: string) => {
      if (selectedIds.size === 0) return;

      const ids = Array.from(selectedIds);
      ids.forEach(cancelPendingSave);
      setRetranslatingMap(previous => {
        const next = { ...previous };
        ids.forEach(id => {
          next[id] = true;
        });
        return next;
      });
      setRetranslateErrorMap(previous => {
        const next = { ...previous };
        ids.forEach(id => {
          delete next[id];
        });
        return next;
      });

      try {
        const result = await documentApi.batchTranslateParagraphs(
          projectId,
          sectionId,
          ids,
          instruction
        );

        result.translations.forEach(({ id, translation, status, confirmed }) => {
          setDrafts(previous => ({ ...previous, [id]: translation }));
          setDirtyMap(previous => ({ ...previous, [id]: false }));
          setSaveErrorMap(previous => {
            const next = { ...previous };
            delete next[id];
            return next;
          });

          applyParagraphUpdate(id, {
            translation,
            status,
            confirmed: confirmed ?? (status === ParagraphStatus.APPROVED ? translation : undefined),
          });
        });

        showToast(`Batch translated ${result.success_count} paragraphs`, 'success');

        if (result.error_count > 0) {
          showToast(`${result.error_count} paragraphs failed`, 'error');
        }

        setSelectedIds(new Set());
      } catch (_error) {
        showToast('Batch retranslate failed', 'error');
      } finally {
        setRetranslatingMap(previous => {
          const next = { ...previous };
          ids.forEach(id => {
            next[id] = false;
          });
          return next;
        });
      }
    },
    [
      applyParagraphUpdate,
      cancelPendingSave,
      projectId,
      sectionId,
      selectedIds,
      showToast,
    ]
  );

  const confirmParagraph = useCallback(
    async (paragraphId: string) => {
      if (!projectId || !sectionId) return;

      cancelPendingSave(paragraphId);

      const paragraph = paragraphsByIdRef.current[paragraphId];
      if (!paragraph) return;

      const translation = draftsRef.current[paragraphId] ?? paragraph.translation ?? '';
      if (!translation.trim()) {
        showToast('Translation cannot be empty', 'error');
        return;
      }

      await runParagraphOperation(paragraphId, async () => {
        setSavingMap(previous => ({ ...previous, [paragraphId]: true }));

        try {
          await documentApi.confirmParagraph(projectId, sectionId, paragraphId, translation);

          applyParagraphUpdate(paragraphId, {
            translation,
            status: ParagraphStatus.APPROVED,
            confirmed: translation,
          });

          setDirtyMap(previous => ({ ...previous, [paragraphId]: false }));
          setSaveErrorMap(previous => {
            const next = { ...previous };
            delete next[paragraphId];
            return next;
          });

          showToast('Paragraph confirmed', 'success');
          void queryClient.invalidateQueries({ queryKey: ['section', projectId, sectionId] });
          void queryClient.invalidateQueries({ queryKey: ['project', projectId] });
          void queryClient.invalidateQueries({ queryKey: ['projects'] });
        } catch (error) {
          setSaveErrorMap(previous => ({
            ...previous,
            [paragraphId]: toErrorMessage(error),
          }));
          showToast('Confirm failed', 'error');
        } finally {
          setSavingMap(previous => ({ ...previous, [paragraphId]: false }));
        }
      });
    },
    [
      applyParagraphUpdate,
      cancelPendingSave,
      projectId,
      queryClient,
      runParagraphOperation,
      sectionId,
      showToast,
    ]
  );

  const batchConfirmSelected = useCallback(async () => {
    if (!projectId || !sectionId || selectedIds.size === 0) return;

    const ids = Array.from(selectedIds);
    const failedIds = new Set<string>();
    let successCount = 0;

    setSavingMap(previous => {
      const next = { ...previous };
      ids.forEach(id => {
        next[id] = true;
      });
      return next;
    });

    try {
      for (const paragraphId of ids) {
        cancelPendingSave(paragraphId);
        const paragraph = paragraphsByIdRef.current[paragraphId];
        if (!paragraph) {
          failedIds.add(paragraphId);
          continue;
        }

        const translation = (draftsRef.current[paragraphId] ?? paragraph.translation ?? '').trim();
        if (!translation) {
          failedIds.add(paragraphId);
          setSaveErrorMap(previous => ({
            ...previous,
            [paragraphId]: 'Translation cannot be empty',
          }));
          continue;
        }

        try {
          await documentApi.confirmParagraph(projectId, sectionId, paragraphId, translation);

          applyParagraphUpdate(paragraphId, {
            translation,
            status: ParagraphStatus.APPROVED,
            confirmed: translation,
          });

          setDirtyMap(previous => ({ ...previous, [paragraphId]: false }));
          setSaveErrorMap(previous => {
            const next = { ...previous };
            delete next[paragraphId];
            return next;
          });
          successCount += 1;
        } catch (error) {
          failedIds.add(paragraphId);
          setSaveErrorMap(previous => ({
            ...previous,
            [paragraphId]: toErrorMessage(error),
          }));
        }
      }

      if (successCount > 0) {
        showToast(`Confirmed ${successCount} paragraphs`, 'success');
        void queryClient.invalidateQueries({ queryKey: ['section', projectId, sectionId] });
        void queryClient.invalidateQueries({ queryKey: ['project', projectId] });
        void queryClient.invalidateQueries({ queryKey: ['projects'] });
      }
      if (failedIds.size > 0) {
        showToast(`${failedIds.size} paragraphs failed to confirm`, 'error');
      }

      setSelectedIds(new Set(Array.from(failedIds)));
    } finally {
      setSavingMap(previous => {
        const next = { ...previous };
        ids.forEach(id => {
          next[id] = false;
        });
        return next;
      });
    }
  }, [
    applyParagraphUpdate,
    cancelPendingSave,
    projectId,
    queryClient,
    sectionId,
    selectedIds,
    showToast,
  ]);

  const dirtyCount = useMemo(() => Object.values(dirtyMap).filter(Boolean).length, [dirtyMap]);
  const savingCount = useMemo(() => Object.values(savingMap).filter(Boolean).length, [savingMap]);
  const retranslatingCount = useMemo(
    () => Object.values(retranslatingMap).filter(Boolean).length,
    [retranslatingMap]
  );

  return {
    drafts,
    dirtyMap,
    savingMap,
    saveErrorMap,
    retranslatingMap,
    retranslateErrorMap,
    dirtyCount,
    savingCount,
    retranslatingCount,
    hasPendingWork: dirtyCount > 0 || savingCount > 0 || retranslatingCount > 0,
    updateDraft,
    saveNow,
    saveAllNow,
    queueRetranslate,
    confirmParagraph,
    batchConfirmSelected,
    selectedIds,
    isSelectionMode,
    toggleSelectionMode,
    toggleSelection,
    toggleSelectAll,
    batchRetranslate,
  };
}
