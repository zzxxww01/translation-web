import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useDocumentStore } from '../../../shared/stores';
import { DEFAULT_MODEL, ParagraphStatus } from '../../../shared/constants';
import { useToast } from '../../../components/ui';
import type { Paragraph } from '../../../shared/types';
import { documentApi } from '../api';

const AUTO_SAVE_DELAY_MS = 800;
const MAX_PARALLEL_RETRANSLATE = 3;

type BooleanStateMap = Record<string, boolean>;
type ErrorStateMap = Record<string, string | null>;

interface RetranslateTask {
  paragraphId: string;
  model?: string;
  instruction?: string;
}

interface UseImmersiveEditorOptions {
  projectId: string;
  sectionId: string;
  paragraphs: Paragraph[];
}

function toErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return '操作失败，请稍后重试';
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
  const updateParagraphInSection = useDocumentStore(state => state.updateParagraphInSection);

  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [dirtyMap, setDirtyMap] = useState<BooleanStateMap>({});
  const [savingMap, setSavingMap] = useState<BooleanStateMap>({});
  const [saveErrorMap, setSaveErrorMap] = useState<ErrorStateMap>({});
  const [retranslatingMap, setRetranslatingMap] = useState<BooleanStateMap>({});
  const [retranslateErrorMap, setRetranslateErrorMap] = useState<ErrorStateMap>({});

  const saveTimersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const retranslateQueueRef = useRef<RetranslateTask[]>([]);
  const activeRetranslateRef = useRef(0);
  const processRetranslateQueueRef = useRef<() => void>(() => {});
  const saveParagraphRef = useRef<(paragraphId: string) => Promise<void>>(async () => {});

  const draftsRef = useRef(drafts);
  const dirtyMapRef = useRef(dirtyMap);
  const retranslatingMapRef = useRef(retranslatingMap);
  const paragraphsByIdRef = useRef<Record<string, Paragraph>>({});

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
    paragraphs.forEach(paragraph => {
      paragraphMap[paragraph.id] = paragraph;
    });
    paragraphsByIdRef.current = paragraphMap;

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
    setSaveErrorMap(previous => pruneMapByIds(previous, paragraphIds));
    setRetranslatingMap(previous => pruneMapByIds(previous, paragraphIds));
    setRetranslateErrorMap(previous => pruneMapByIds(previous, paragraphIds));
  }, [paragraphIds, paragraphs]);

  useEffect(() => {
    return () => {
      Object.values(saveTimersRef.current).forEach(timerId => clearTimeout(timerId));
    };
  }, []);

  const scheduleAutoSave = useCallback((paragraphId: string) => {
    const existingTimer = saveTimersRef.current[paragraphId];
    if (existingTimer) {
      clearTimeout(existingTimer);
    }
    saveTimersRef.current[paragraphId] = setTimeout(() => {
      void saveParagraphRef.current(paragraphId);
    }, AUTO_SAVE_DELAY_MS);
  }, []);

  const saveParagraph = useCallback(
    async (paragraphId: string) => {
      if (!projectId || !sectionId) return;
      if (!dirtyMapRef.current[paragraphId]) return;

      const paragraph = paragraphsByIdRef.current[paragraphId];
      if (!paragraph) return;

      const translation = draftsRef.current[paragraphId] ?? '';
      const status =
        paragraph.status === ParagraphStatus.PENDING && translation.trim()
          ? ParagraphStatus.TRANSLATED
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
        updateParagraphInSection(sectionId, paragraphId, {
          translation: persistedTranslation,
          status: persistedStatus,
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
    [projectId, scheduleAutoSave, sectionId, updateParagraphInSection]
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
      const existingTimer = saveTimersRef.current[paragraphId];
      if (existingTimer) {
        clearTimeout(existingTimer);
        delete saveTimersRef.current[paragraphId];
      }
      await saveParagraph(paragraphId);
    },
    [saveParagraph]
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

      const { paragraphId, instruction, model } = task;
      const paragraph = paragraphsByIdRef.current[paragraphId];
      if (!paragraph) continue;

      activeRetranslateRef.current += 1;
      setRetranslatingMap(previous => ({ ...previous, [paragraphId]: true }));
      setRetranslateErrorMap(previous => {
        const next = { ...previous };
        delete next[paragraphId];
        return next;
      });

      const wasDirty = dirtyMapRef.current[paragraphId];
      const previousDraft = draftsRef.current[paragraphId] ?? '';

      void documentApi
        .translateParagraph(projectId, sectionId, paragraphId, instruction, model)
        .then(result => {
          const translation = result.translation ?? '';
          const existingTimer = saveTimersRef.current[paragraphId];
          if (existingTimer) {
            clearTimeout(existingTimer);
            delete saveTimersRef.current[paragraphId];
          }

          setDrafts(previous => ({ ...previous, [paragraphId]: translation }));
          setDirtyMap(previous => ({ ...previous, [paragraphId]: false }));
          setSaveErrorMap(previous => {
            const next = { ...previous };
            delete next[paragraphId];
            return next;
          });

          updateParagraphInSection(sectionId, paragraphId, {
            translation,
            status: ParagraphStatus.TRANSLATED,
          });

          if (wasDirty && previousDraft !== translation) {
            showToast(`段落 #${paragraph.index} 已使用重译结果覆盖当前编辑`, 'info');
          }
        })
        .catch(error => {
          setRetranslateErrorMap(previous => ({
            ...previous,
            [paragraphId]: toErrorMessage(error),
          }));
          showToast('重新翻译失败，请稍后重试', 'error');
        })
        .finally(() => {
          activeRetranslateRef.current -= 1;
          setRetranslatingMap(previous => ({ ...previous, [paragraphId]: false }));
          processRetranslateQueueRef.current();
        });
    }
  }, [projectId, sectionId, showToast, updateParagraphInSection]);

  useEffect(() => {
    processRetranslateQueueRef.current = processRetranslateQueue;
  }, [processRetranslateQueue]);

  const queueRetranslate = useCallback(
    (paragraphId: string, model = DEFAULT_MODEL, instruction?: string) => {
      const isAlreadyQueued = retranslateQueueRef.current.some(
        task => task.paragraphId === paragraphId
      );
      if (isAlreadyQueued || retranslatingMapRef.current[paragraphId]) {
        return;
      }

      retranslateQueueRef.current.push({ paragraphId, model, instruction });
      processRetranslateQueueRef.current();
    },
    []
  );

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
  };
}
