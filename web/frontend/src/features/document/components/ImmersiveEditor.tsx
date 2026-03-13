import { Check, CheckSquare, RotateCw, X } from 'lucide-react';
import { type UIEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button } from '../../../components/ui';
import { ParagraphStatus } from '../../../shared/constants';
import { useDocumentStore } from '../../../shared/stores';
import type { Paragraph, Section } from '../../../shared/types';
import { confirmationApi } from '../../confirmation/api/confirmationApi';
import { useImmersiveEditor } from '../hooks/useImmersiveEditor';
import { ImmersiveRow } from './ImmersiveRow';

const CHUNK_THRESHOLD = 300;
const INITIAL_CHUNK_SIZE = 80;
const CHUNK_SIZE = 40;
const MAX_BATCH_SELECTION = 50;
const EMPTY_PARAGRAPHS: Paragraph[] = [];

type FilterMode = 'all' | 'translated' | 'approved' | 'modified';

export interface RetranslateOption {
  id: string;
  label: string;
  description: string;
  instruction: string;
}

interface ImmersiveEditorProps {
  projectId: string;
  section: Section;
  initialParagraphId?: string | null;
  onClose: () => void;
}

function matchesFilter(mode: FilterMode, paragraph: Paragraph, isDirty: boolean): boolean {
  if (mode === 'all') return true;
  if (mode === 'translated') return paragraph.status === ParagraphStatus.TRANSLATED;
  if (mode === 'approved') return paragraph.status === ParagraphStatus.APPROVED;
  return paragraph.status === ParagraphStatus.MODIFIED || isDirty;
}

export function ImmersiveEditor({
  projectId,
  section,
  initialParagraphId = null,
  onClose,
}: ImmersiveEditorProps) {
  const sections = useDocumentStore(state => state.sections);
  const latestSection = useMemo(() => {
    const storeSection = sections.find(item => item.section_id === section.section_id);
    if (storeSection?.paragraphs?.length) {
      return storeSection;
    }
    return section;
  }, [sections, section]);
  const paragraphs = latestSection.paragraphs ?? EMPTY_PARAGRAPHS;

  const [filterMode] = useState<FilterMode>('all');
  const [chunkState, setChunkState] = useState({ key: '', extra: 0 });
  const [showBatchRetranslateDialog, setShowBatchRetranslateDialog] = useState(false);
  const [retranslateOptions, setRetranslateOptions] = useState<RetranslateOption[]>([]);
  const listContainerRef = useRef<HTMLDivElement>(null);
  const targetParagraphRef = useRef<HTMLDivElement | null>(null);
  const hasAutoScrolledRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    confirmationApi.getRetranslateOptions(projectId).then(data => {
      if (!cancelled) {
        setRetranslateOptions(data.options);
      }
    }).catch(() => {
      // Silently ignore
    });
    return () => { cancelled = true; };
  }, [projectId]);

  const {
    drafts,
    dirtyMap,
    savingMap,
    saveErrorMap,
    retranslatingMap,
    retranslateErrorMap,
    savingCount,
    retranslatingCount,
    hasPendingWork,
    updateDraft,
    queueRetranslate,
    confirmParagraph,
    batchConfirmSelected,
    selectedIds,
    isSelectionMode,
    toggleSelectionMode,
    toggleSelection,
    toggleSelectAll,
    batchRetranslate,
  } = useImmersiveEditor({
    projectId,
    sectionId: section.section_id,
    paragraphs,
  });

  const filteredParagraphs = useMemo(
    () =>
      paragraphs.filter(paragraph =>
        matchesFilter(filterMode, paragraph, Boolean(dirtyMap[paragraph.id]))
      ),
    [dirtyMap, filterMode, paragraphs]
  );
  const targetParagraphIndex = useMemo(
    () =>
      initialParagraphId
        ? filteredParagraphs.findIndex(paragraph => paragraph.id === initialParagraphId)
        : -1,
    [filteredParagraphs, initialParagraphId]
  );

  const isChunkMode = filteredParagraphs.length > CHUNK_THRESHOLD;
  const chunkResetKey = `${section.section_id}:${filterMode}:${initialParagraphId ?? ''}:${filteredParagraphs.length}:${targetParagraphIndex}:${Number(isChunkMode)}`;
  const baseVisibleCount = useMemo(
    () =>
      isChunkMode
        ? Math.min(
            filteredParagraphs.length,
            Math.max(INITIAL_CHUNK_SIZE, targetParagraphIndex >= 0 ? targetParagraphIndex + 1 : 0)
          )
        : filteredParagraphs.length,
    [filteredParagraphs.length, isChunkMode, targetParagraphIndex]
  );

  useEffect(() => {
    hasAutoScrolledRef.current = false;
  }, [chunkResetKey]);

  const visibleCount = useMemo(() => {
    const extraVisibleCount = chunkState.key === chunkResetKey ? chunkState.extra : 0;
    return isChunkMode
      ? Math.min(filteredParagraphs.length, baseVisibleCount + extraVisibleCount)
      : filteredParagraphs.length;
  }, [
    baseVisibleCount,
    chunkResetKey,
    chunkState.extra,
    chunkState.key,
    filteredParagraphs.length,
    isChunkMode,
  ]);

  const displayedParagraphs = useMemo(
    () => (isChunkMode ? filteredParagraphs.slice(0, visibleCount) : filteredParagraphs),
    [filteredParagraphs, isChunkMode, visibleCount]
  );

  useEffect(() => {
    if (!initialParagraphId || hasAutoScrolledRef.current) {
      return;
    }
    if (!displayedParagraphs.some(paragraph => paragraph.id === initialParagraphId)) {
      return;
    }
    if (!targetParagraphRef.current || !listContainerRef.current) {
      return;
    }

    targetParagraphRef.current.scrollIntoView({
      block: 'center',
      behavior: 'smooth',
    });
    hasAutoScrolledRef.current = true;
  }, [displayedParagraphs, initialParagraphId]);

  const approvedCount = useMemo(
    () =>
      paragraphs.filter(
        paragraph => paragraph.status === ParagraphStatus.APPROVED || Boolean(paragraph.confirmed)
      ).length,
    [paragraphs]
  );

  const selectableFilteredIds = useMemo(
    () => filteredParagraphs.slice(0, MAX_BATCH_SELECTION).map(paragraph => paragraph.id),
    [filteredParagraphs]
  );
  const isAllFilteredSelected = useMemo(
    () =>
      selectableFilteredIds.length > 0 &&
      selectableFilteredIds.every(paragraphId => selectedIds.has(paragraphId)),
    [selectableFilteredIds, selectedIds]
  );

  const handleListScroll = useCallback(
    (event: UIEvent<HTMLDivElement>) => {
      if (!isChunkMode) return;
      const container = event.currentTarget;
      if (container.scrollTop + container.clientHeight < container.scrollHeight - 240) return;

      setChunkState(current => {
        const currentExtra = current.key === chunkResetKey ? current.extra : 0;
        const nextExtra = Math.min(
          Math.max(0, filteredParagraphs.length - baseVisibleCount),
          currentExtra + CHUNK_SIZE
        );
        if (current.key === chunkResetKey && nextExtra === currentExtra) {
          return current;
        }
        return { key: chunkResetKey, extra: nextExtra };
      });
    },
    [baseVisibleCount, chunkResetKey, filteredParagraphs.length, isChunkMode]
  );

  const handleClose = useCallback(() => {
    if (hasPendingWork) {
      const shouldClose = window.confirm('仍有未完成的保存或重译任务，确定强制退出沉浸编辑吗？');
      if (!shouldClose) return;
    }
    onClose();
  }, [hasPendingWork, onClose]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        handleClose();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [handleClose]);

  const batchRetranslateMenuOptions = useMemo(() => {
    const noneOption = { id: 'none', label: '仅重译（无额外要求）', description: '', instruction: '' };
    return [noneOption, ...retranslateOptions];
  }, [retranslateOptions]);

  const handleBatchRetranslate = useCallback(
    (optionId: string) => {
      const instruction = optionId === 'none' ? undefined : undefined;
      const effectiveOptionId = optionId === 'none' ? undefined : optionId;
      void batchRetranslate(instruction, effectiveOptionId);
      setShowBatchRetranslateDialog(false);
    },
    [batchRetranslate]
  );

  return (
    <div className="fixed inset-0 z-[70] flex flex-col bg-bg-primary">
      <div className="border-b border-border-subtle bg-bg-primary/95 px-6 py-3 backdrop-blur">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-medium text-text-primary">{latestSection.title}</h2>
            <span className="text-sm text-text-muted">已确认 {approvedCount}/{paragraphs.length} 段</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={toggleSelectionMode}
              className={`flex items-center justify-center rounded-lg border p-2 transition-colors ${
                isSelectionMode
                  ? 'border-primary-500 bg-primary-500 text-white hover:bg-primary-600'
                  : 'border-border bg-bg-secondary text-text-primary hover:bg-bg-tertiary'
              }`}
              title={isSelectionMode ? '退出选择' : '批量选择'}
            >
              <CheckSquare className="h-5 w-5" />
            </button>

            {isSelectionMode && (
              <div className="flex items-center gap-2 border-l border-border-subtle pl-2">
                <span className="text-sm text-text-muted">
                  已选 {selectedIds.size}/{MAX_BATCH_SELECTION}
                </span>
                <button
                  onClick={() => toggleSelectAll(filteredParagraphs.map(paragraph => paragraph.id))}
                  className="rounded-lg border border-border bg-bg-secondary px-3 py-1.5 text-sm text-text-primary hover:bg-bg-tertiary"
                  title={isAllFilteredSelected ? '取消全选' : '全选'}
                >
                  {isAllFilteredSelected ? '取消全选' : '全选'}
                </button>
                <button
                  onClick={() => void batchConfirmSelected()}
                  disabled={selectedIds.size === 0 || retranslatingCount > 0 || savingCount > 0}
                  className="flex items-center justify-center rounded-lg border border-border bg-bg-secondary p-2 text-text-primary hover:bg-bg-tertiary disabled:cursor-not-allowed disabled:opacity-50"
                  title="批量确认"
                >
                  <Check className="h-5 w-5" />
                </button>
                <button
                  onClick={() => setShowBatchRetranslateDialog(true)}
                  disabled={selectedIds.size === 0 || retranslatingCount > 0}
                  className="flex items-center justify-center rounded-lg border border-border bg-bg-secondary p-2 text-text-primary hover:bg-bg-tertiary disabled:cursor-not-allowed disabled:opacity-50"
                  title="批量重译"
                >
                  <RotateCw className="h-5 w-5" />
                </button>
              </div>
            )}

            <button
              onClick={handleClose}
              className="flex items-center justify-center rounded-lg border border-border bg-bg-secondary p-2 text-text-primary hover:bg-bg-tertiary"
              title="退出沉浸编辑"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>

      <div ref={listContainerRef} className="flex-1 overflow-auto px-6 py-2" onScroll={handleListScroll}>
        <div className="space-y-1">
          {displayedParagraphs.map(paragraph => (
            <div
              key={paragraph.id}
              ref={node => {
                if (paragraph.id === initialParagraphId) {
                  targetParagraphRef.current = node;
                }
              }}
            >
              <ImmersiveRow
                paragraph={paragraph}
                draft={drafts[paragraph.id] ?? paragraph.translation ?? ''}
                isSaving={Boolean(savingMap[paragraph.id])}
                saveError={saveErrorMap[paragraph.id]}
                isRetranslating={Boolean(retranslatingMap[paragraph.id])}
                retranslateError={retranslateErrorMap[paragraph.id]}
                onChange={value => updateDraft(paragraph.id, value)}
                onRetranslate={(instruction?: string, optionId?: string) =>
                  queueRetranslate(paragraph.id, instruction, optionId)
                }
                onConfirm={() => void confirmParagraph(paragraph.id)}
                isSelectionMode={isSelectionMode}
                isSelected={selectedIds.has(paragraph.id)}
                onToggleSelection={() => toggleSelection(paragraph.id)}
                retranslateOptions={retranslateOptions}
              />
            </div>
          ))}
        </div>

        {displayedParagraphs.length === 0 && (
          <div className="mt-10 text-center text-sm text-text-muted">当前筛选条件下没有段落</div>
        )}

        {isChunkMode && displayedParagraphs.length < filteredParagraphs.length && (
          <div className="py-4 text-center text-sm text-text-muted">
            已加载 {displayedParagraphs.length}/{filteredParagraphs.length} 段，下拉继续加载
          </div>
        )}
      </div>

      {showBatchRetranslateDialog && (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md rounded-lg border border-border bg-bg-primary p-6 shadow-xl">
            <h3 className="mb-4 text-lg font-semibold text-text-primary">
              批量重译 {selectedIds.size} 个段落
            </h3>
            <div className="space-y-3">
              {batchRetranslateMenuOptions.map(option => (
                <button
                  key={option.id}
                  onClick={() => handleBatchRetranslate(option.id)}
                  disabled={retranslatingCount > 0}
                  className="w-full rounded-lg border border-border bg-bg-secondary px-4 py-3 text-left text-sm text-text-primary hover:bg-bg-tertiary disabled:opacity-50"
                >
                  <div className="font-medium">{option.label}</div>
                  {option.description && (
                    <div className="mt-1 text-xs text-text-muted">{option.description}</div>
                  )}
                </button>
              ))}
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="secondary" size="sm" onClick={() => setShowBatchRetranslateDialog(false)}>
                取消
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
