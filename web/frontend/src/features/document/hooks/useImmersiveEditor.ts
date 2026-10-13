import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { SetStateAction } from 'react';
import { toast } from 'sonner';
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
  optionId?: string;
  editVersion: number;
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
  return '请求失败，请重试';
}

// 草稿本地快照：防抖窗口内刷新/关页时服务端还没收到改动，靠 sessionStorage 兜底
const DRAFT_STORAGE_PREFIX = 'immersive-draft';

function draftStorageKey(projectId: string, sectionId: string, paragraphId: string): string {
  return `${DRAFT_STORAGE_PREFIX}:${projectId}:${sectionId}:${paragraphId}`;
}

interface StoredDraft { text: string; base?: string; source?: string; }
function readStoredDraft(key: string): StoredDraft | null {
  try {
    const raw = window.sessionStorage.getItem(key);
    if (raw === null) return null;
    try {
      const value = JSON.parse(raw);
      if (value?.schema === 1 && typeof value.text === 'string') return value;
    } catch { /* legacy plain-text snapshot */ }
    return { text: raw }; // no known baseline: recover for manual review only
  } catch { return null; }
}

function writeStoredDraft(key: string, value: StoredDraft): void {
  try { window.sessionStorage.setItem(key, JSON.stringify({ schema: 1, ...value })); }
  catch { /* private browsing or storage quota: server save remains available */ }
}

function clearStoredDraft(key: string, expectedText?: string): void {
  try {
    if (expectedText !== undefined && readStoredDraft(key)?.text !== expectedText) return;
    window.sessionStorage.removeItem(key);
  } catch {
    // 同上，静默忽略
  }
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

// Synchronous refs protect immediate save/confirm actions in the same React
// event and async completions before the next render/effect has flushed.
function useLiveState<T>(initial: T) {
  const [state, setState] = useState(initial);
  const ref = useRef(state);
  const set = useCallback((action: SetStateAction<T>) => {
    const next = typeof action === 'function' ? (action as (value: T) => T)(ref.current) : action;
    ref.current = next;
    setState(next);
  }, []);
  return [state, set, ref] as const;
}

export function useImmersiveEditor({ projectId, sectionId, paragraphs }: UseImmersiveEditorOptions) {
  const queryClient = useQueryClient();
  const updateParagraphInProject = useDocumentStore(state => state.updateParagraphInProject);

  const [drafts, setDrafts, draftsRef] = useLiveState<Record<string, string>>({});
  const [dirtyMap, setDirtyMap, dirtyMapRef] = useLiveState<BooleanStateMap>({});
  const [savingMap, setSavingMap] = useState<BooleanStateMap>({});
  const [saveErrorMap, setSaveErrorMap] = useState<ErrorStateMap>({});
  const [retranslatingMap, setRetranslatingMap, retranslatingMapRef] = useLiveState<BooleanStateMap>({});
  const [retranslateErrorMap, setRetranslateErrorMap] = useState<ErrorStateMap>({});
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isSelectionMode, setIsSelectionMode] = useState(false);

  const saveTimersRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const retranslateQueueRef = useRef<RetranslateTask[]>([]);
  const activeRetranslateRef = useRef(0);
  const processRetranslateQueueRef = useRef<() => void>(() => {});
  const saveParagraphRef = useRef<(paragraphId: string) => Promise<void>>(async () => {});
  const paragraphOperationRef = useRef<Record<string, Promise<unknown>>>({});

  const editVersionsRef = useRef<Record<string, number>>({});
  const mountedRef = useRef(true);
  const recoveryConflictsRef = useRef(new Set<string>());
  const paragraphsByIdRef = useRef<Record<string, Paragraph>>({});
  const paragraphSnapshotsRef = useRef<Record<string, ParagraphSnapshot>>({});

  const paragraphIds = useMemo(() => new Set(paragraphs.map(paragraph => paragraph.id)), [paragraphs]);

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
        if (!recoveryConflictsRef.current.has(paragraphId)) delete next[paragraphId];
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
  }, [dirtyMapRef, paragraphIds, paragraphs, setDirtyMap, setDrafts, setRetranslatingMap]);

  useEffect(() => {
    mountedRef.current = true;
    const saveTimers = saveTimersRef.current;
    const dirtyState = dirtyMapRef;
    return () => {
      mountedRef.current = false;
      retranslateQueueRef.current = [];
      // 应用内卸载兜底：仍有未保存改动的段落先补发一次保存，再清理定时器。
      // （浏览器刷新/关页由 sessionStorage 快照 + beforeunload 负责，此处只管应用内跳转）
      // 遍历 dirty 集合而非定时器 key：从 sessionStorage 恢复出来的草稿没有
      // 定时器 key，按 key 遍历会把它们整批漏掉。
      Object.keys(dirtyState.current).forEach(paragraphId => {
        if (dirtyState.current[paragraphId]) {
          void saveParagraphRef.current(paragraphId);
        }
      });
      Object.values(saveTimers).forEach(timerId => clearTimeout(timerId));
    };
  }, [dirtyMapRef]);

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
      const current = paragraphsByIdRef.current[paragraphId];
      if (current) paragraphsByIdRef.current[paragraphId] = { ...current, ...updates };
      updateParagraphInProject(projectId, sectionId, paragraphId, updates);
      updateSectionQueryCache(paragraphId, updates);
    },
    [projectId, sectionId, updateParagraphInProject, updateSectionQueryCache]
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

      const cleanup = () => {
        if (paragraphOperationRef.current[paragraphId] === tracked) {
          delete paragraphOperationRef.current[paragraphId];
        }
      };
      // The tracker must never reject unobserved; the caller owns next.
      const tracked: Promise<unknown> = next.then(cleanup, cleanup);

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
      if (!dirtyMapRef.current[paragraphId] || recoveryConflictsRef.current.has(paragraphId)) return;

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
          clearStoredDraft(draftStorageKey(projectId, sectionId, paragraphId), translation);
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
    [applyParagraphUpdate, dirtyMapRef, draftsRef, projectId, scheduleAutoSave, sectionId, setDirtyMap]
  );

  const saveParagraph = useCallback(
    async (paragraphId: string) =>
      runParagraphOperation(paragraphId, () => performSaveParagraph(paragraphId)),
    [performSaveParagraph, runParagraphOperation]
  );

  useEffect(() => {
    saveParagraphRef.current = saveParagraph;
  }, [saveParagraph]);

  // 刷新回来后恢复本地草稿快照：同一 project/section 只尝试一次。
  // 位置必须在 scheduleAutoSave 之后——依赖数组在渲染期求值，放在它前面会撞 TDZ。
  const restoredScopeRef = useRef('');
  useEffect(() => {
    if (!projectId || !sectionId || paragraphs.length === 0) return;
    const scopeKey = `${projectId}:${sectionId}`;
    if (restoredScopeRef.current === scopeKey) return;
    restoredScopeRef.current = scopeKey;

    const recovered: Record<string, string> = {};
    paragraphs.forEach(paragraph => {
      const key = draftStorageKey(projectId, sectionId, paragraph.id);
      const stored = readStoredDraft(key);
      if (stored === null) return;
      // 与服务端译文一致说明已落库，清掉快照即可
      if (stored.text === (paragraph.translation ?? '')) {
        clearStoredDraft(key);
        return;
      }
      recovered[paragraph.id] = stored.text;
      if (stored.base !== (paragraph.confirmed ?? paragraph.translation ?? '') || stored.source !== paragraph.source) {
        recoveryConflictsRef.current.add(paragraph.id);
        setSaveErrorMap(previous => ({ ...previous, [paragraph.id]: '本地草稿与当前服务端版本不同，请核对后手动保存或确认' }));
      }
    });

    const recoveredIds = Object.keys(recovered);
    if (recoveredIds.length === 0) return;

    setDrafts(previous => ({ ...previous, ...recovered }));
    setDirtyMap(previous => {
      const next = { ...previous };
      recoveredIds.forEach(paragraphId => {
        next[paragraphId] = true;
      });
      return next;
    });
    // 恢复出来的草稿必须排进自动保存队列。否则它们没有定时器、永远停在 dirty，
    // 把 hasPendingWork 永久钉成 true——每次退出沉浸编辑都会弹「仍有未完成的
    // 保存任务」，而那些草稿其实谁也不会去保存它们。
    recoveredIds.filter(id => !recoveryConflictsRef.current.has(id)).forEach(scheduleAutoSave);
    toast.info(`已恢复 ${recoveredIds.length} 段本地草稿；版本冲突的草稿需核对后手动保存`);
  }, [paragraphs, projectId, scheduleAutoSave, sectionId, setDirtyMap, setDrafts]);

  const updateDraft = useCallback(
    (paragraphId: string, value: string) => {
      recoveryConflictsRef.current.delete(paragraphId);
      editVersionsRef.current[paragraphId] = (editVersionsRef.current[paragraphId] ?? 0) + 1;
      setDrafts(previous => ({ ...previous, [paragraphId]: value }));
      setDirtyMap(previous => ({ ...previous, [paragraphId]: true }));
      setSaveErrorMap(previous => {
        const next = { ...previous };
        delete next[paragraphId];
        return next;
      });

      if (projectId && sectionId) {
        const paragraph = paragraphsByIdRef.current[paragraphId];
        writeStoredDraft(draftStorageKey(projectId, sectionId, paragraphId), {
          text: value, base: paragraph?.confirmed ?? paragraph?.translation ?? '', source: paragraph?.source,
        });
      }

      scheduleAutoSave(paragraphId);
    },
    [projectId, scheduleAutoSave, sectionId, setDirtyMap, setDrafts]
  );

  const saveNow = useCallback(
    async (paragraphId: string) => {
      recoveryConflictsRef.current.delete(paragraphId);
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
  }, [dirtyMapRef, saveNow]);

  const acceptGeneratedDraft = useCallback((id: string, text: string, requestedVersion: number) => {
    if (!mountedRef.current) return false;
    if ((editVersionsRef.current[id] ?? 0) !== requestedVersion) {
      // Server result may be persisted, but the user's newer local draft wins.
      scheduleAutoSave(id);
      return false;
    }
    recoveryConflictsRef.current.delete(id);
    setDrafts(previous => ({ ...previous, [id]: text }));
    setDirtyMap(previous => ({ ...previous, [id]: false }));
    clearStoredDraft(draftStorageKey(projectId, sectionId, id));
    return true;
  }, [projectId, sectionId, scheduleAutoSave, setDirtyMap, setDrafts]);

  const acknowledgeSave = useCallback((id: string, sent: string, version: number) => {
    if (!mountedRef.current) return;
    if ((editVersionsRef.current[id] ?? 0) === version) {
      setDrafts(previous => ({ ...previous, [id]: sent }));
      recoveryConflictsRef.current.delete(id);
      setDirtyMap(previous => ({ ...previous, [id]: false }));
      clearStoredDraft(draftStorageKey(projectId, sectionId, id));
    } else {
      scheduleAutoSave(id);
    }
  }, [projectId, sectionId, scheduleAutoSave, setDirtyMap, setDrafts]);

  const processRetranslateQueue = useCallback(() => {
    if (!projectId || !sectionId || !mountedRef.current) return;

    while (
      activeRetranslateRef.current < MAX_PARALLEL_RETRANSLATE &&
      retranslateQueueRef.current.length > 0
    ) {
      const task = retranslateQueueRef.current.shift();
      if (!task) break;

      const { paragraphId, instruction, optionId } = task;
      const paragraph = paragraphsByIdRef.current[paragraphId];
      if (!paragraph) {
        setRetranslatingMap(previous => ({ ...previous, [paragraphId]: false }));
        continue;
      }

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
      const requestedVersion = task.editVersion;

      void runParagraphOperation(paragraphId, async () => {
        const result = await documentApi.translateParagraph(
          projectId,
          sectionId,
          paragraphId,
          instruction,
          optionId
        );
        const translation = result.translation ?? '';
        const persistedStatus = result.status ?? ParagraphStatus.TRANSLATED;

        const accepted = acceptGeneratedDraft(paragraphId, translation, requestedVersion);
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

        if (accepted && wasDirty && previousDraft !== translation) {
          toast.info(`段落 #${paragraph.index} 已被重译结果替换`);
        }
      })
        .catch(error => {
          setRetranslateErrorMap(previous => ({
            ...previous,
            [paragraphId]: toErrorMessage(error),
          }));
          toast.error('重译失败，请重试');
        })
        .finally(() => {
          activeRetranslateRef.current -= 1;
          setRetranslatingMap(previous => ({ ...previous, [paragraphId]: false }));
          processRetranslateQueueRef.current();
        });
    }
  }, [
    acceptGeneratedDraft,
    applyParagraphUpdate,
    cancelPendingSave,
    projectId,
    runParagraphOperation,
    sectionId,
    dirtyMapRef, draftsRef, setRetranslatingMap,
  ]);

  useEffect(() => {
    processRetranslateQueueRef.current = processRetranslateQueue;
  }, [processRetranslateQueue]);

  const queueRetranslate = useCallback(
    (paragraphId: string, instruction?: string, optionId?: string) => {
      const isAlreadyQueued = retranslateQueueRef.current.some(task => task.paragraphId === paragraphId);
      if (isAlreadyQueued || retranslatingMapRef.current[paragraphId]) {
        return;
      }

      cancelPendingSave(paragraphId);
      retranslateQueueRef.current.push({ paragraphId, instruction, optionId, editVersion: editVersionsRef.current[paragraphId] ?? 0 });
      setRetranslatingMap(previous => ({ ...previous, [paragraphId]: true }));
      processRetranslateQueueRef.current();
    },
    [cancelPendingSave, retranslatingMapRef, setRetranslatingMap]
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
    async (instruction?: string, optionId?: string) => {
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

      // N11: 通过 runParagraphOperation 把整个批量请求串到每个段落的操作链上，
      // 避免与在途自动保存/单段重译互相覆盖。先等待所有选中段落的在途操作完成，
      // 再发起单次批量请求，并把该批量 Promise 注册回每个段落的操作链，
      // 让随后到来的单段操作排在它后面。
      const inFlight = ids
        .map(id => paragraphOperationRef.current[id])
        .filter((promise): promise is Promise<unknown> => Boolean(promise));
      const requestedVersions = Object.fromEntries(ids.map(id => [id, editVersionsRef.current[id] ?? 0]));
      const batchPromise = Promise.allSettled(inFlight).then(() => documentApi.batchTranslateParagraphs(
        projectId,
        sectionId,
        ids,
        instruction,
        optionId
      ));

      // 将批量操作登记到每个段落的串行链上，使后续单段操作排队等待。
      ids.forEach(id => {
        const tracked: Promise<unknown> = batchPromise
          .catch(() => undefined)
          .finally(() => {
            if (paragraphOperationRef.current[id] === tracked) {
              delete paragraphOperationRef.current[id];
            }
          });
        paragraphOperationRef.current[id] = tracked;
      });

      try {
        const result = await batchPromise;

        result.translations.forEach(({ id, translation, status, confirmed }) => {
          if (!ids.includes(id)) return;
          acceptGeneratedDraft(id, translation, requestedVersions[id]);
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

        toast.success(`批量重译完成：${result.success_count} 段`);

        if (result.error_count > 0) {
          toast.error(`${result.error_count} 段重译失败`);
        }

        setSelectedIds(new Set());
      } catch (_error) {
        toast.error('批量重译失败');
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
      acceptGeneratedDraft,
      applyParagraphUpdate,
      cancelPendingSave,
      projectId,
      sectionId,
      selectedIds,
      setRetranslatingMap,
    ]
  );

  const confirmParagraph = useCallback(
    async (paragraphId: string): Promise<boolean> => {
      if (!projectId || !sectionId) return false;

      cancelPendingSave(paragraphId);

      const paragraph = paragraphsByIdRef.current[paragraphId];
      if (!paragraph) return false;

      const translation = draftsRef.current[paragraphId] ?? paragraph.translation ?? '';
      const requestedVersion = editVersionsRef.current[paragraphId] ?? 0;
      if (!translation.trim()) {
        toast.error('译文不能为空');
        return false;
      }

      let canAdvance = false;
      await runParagraphOperation(paragraphId, async () => {
        setSavingMap(previous => ({ ...previous, [paragraphId]: true }));

        try {
          await documentApi.confirmParagraph(projectId, sectionId, paragraphId, translation);

          applyParagraphUpdate(paragraphId, {
            translation,
            status: ParagraphStatus.APPROVED,
            confirmed: translation,
          });

          acknowledgeSave(paragraphId, translation, requestedVersion);
          canAdvance = (editVersionsRef.current[paragraphId] ?? 0) === requestedVersion;
          setSaveErrorMap(previous => {
            const next = { ...previous };
            delete next[paragraphId];
            return next;
          });

          toast.success('段落已确认');
          void queryClient.invalidateQueries({ queryKey: ['section', projectId, sectionId] });
          void queryClient.invalidateQueries({ queryKey: ['project', projectId] });
          void queryClient.invalidateQueries({ queryKey: ['projects'] });
        } catch (error) {
          setSaveErrorMap(previous => ({
            ...previous,
            [paragraphId]: toErrorMessage(error),
          }));
          toast.error('确认失败');
        } finally {
          setSavingMap(previous => ({ ...previous, [paragraphId]: false }));
        }
      });
      return canAdvance;
    },
    [
      applyParagraphUpdate,
      cancelPendingSave,
      projectId,
      queryClient,
      runParagraphOperation,
      sectionId,
      acknowledgeSave, draftsRef,
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

        const translation = draftsRef.current[paragraphId] ?? paragraph.translation ?? '';
        const requestedVersion = editVersionsRef.current[paragraphId] ?? 0;
        if (!translation.trim()) {
          failedIds.add(paragraphId);
          setSaveErrorMap(previous => ({
            ...previous,
            [paragraphId]: '译文不能为空',
          }));
          continue;
        }

        try {
          await runParagraphOperation(paragraphId, async () => {
          await documentApi.confirmParagraph(projectId, sectionId, paragraphId, translation);

          applyParagraphUpdate(paragraphId, {
            translation,
            status: ParagraphStatus.APPROVED,
            confirmed: translation,
          });

          acknowledgeSave(paragraphId, translation, requestedVersion);
          setSaveErrorMap(previous => {
            const next = { ...previous };
            delete next[paragraphId];
            return next;
          });
          successCount += 1;
          });
        } catch (error) {
          failedIds.add(paragraphId);
          setSaveErrorMap(previous => ({
            ...previous,
            [paragraphId]: toErrorMessage(error),
          }));
        }
      }

      if (successCount > 0) {
        toast.success(`已确认 ${successCount} 段`);
        void queryClient.invalidateQueries({ queryKey: ['section', projectId, sectionId] });
        void queryClient.invalidateQueries({ queryKey: ['project', projectId] });
        void queryClient.invalidateQueries({ queryKey: ['projects'] });
      }
      if (failedIds.size > 0) {
        toast.error(`${failedIds.size} 段确认失败`);
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
    acknowledgeSave, draftsRef, runParagraphOperation,
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
