import { CheckSquare, RotateCw, Save, X } from 'lucide-react';
import { type UIEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '../../../components/ui';
import { DEFAULT_MODEL, MODEL_OPTIONS, ParagraphStatus } from '../../../shared/constants';
import { useDocumentStore } from '../../../shared/stores';
import type { Paragraph, Section } from '../../../shared/types';
import { useImmersiveEditor } from '../hooks/useImmersiveEditor';
import { ImmersiveRow } from './ImmersiveRow';

const CHUNK_THRESHOLD = 300;
const INITIAL_CHUNK_SIZE = 80;
const CHUNK_SIZE = 40;
const MAX_BATCH_SELECTION = 50;

type FilterMode = 'all' | 'translated' | 'approved' | 'modified';
type RetranslateTemplate = 'none' | 'readable' | 'professional' | 'idiomatic';

const RETRANSLATE_TEMPLATES: Array<{
  id: RetranslateTemplate;
  label: string;
  instruction?: string;
}> = [
  { id: 'none', label: '仅重译（无额外要求）' },
  {
    id: 'readable',
    label: '可读性',
    instruction: '请提升可读性：拆分过长句，优化语序，减少冗余连接词，保持信息完整和逻辑清晰。',
  },
  {
    id: 'professional',
    label: '专业化',
    instruction: '请提升专业表达：术语更准确、行业表述更规范，保留技术细节和判断力度。',
  },
  {
    id: 'idiomatic',
    label: '更地道',
    instruction: '请使中文更地道自然：避免翻译腔，改为符合中文读者习惯的表达，但不改变原意。',
  },
];

interface ImmersiveEditorProps {
  projectId: string;
  section: Section;
  onClose: () => void;
}

function matchesFilter(mode: FilterMode, paragraph: Paragraph, isDirty: boolean): boolean {
  if (mode === 'all') return true;
  if (mode === 'translated') return paragraph.status === ParagraphStatus.TRANSLATED;
  if (mode === 'approved') return paragraph.status === ParagraphStatus.APPROVED;
  return paragraph.status === ParagraphStatus.MODIFIED || isDirty;
}

export function ImmersiveEditor({ projectId, section, onClose }: ImmersiveEditorProps) {
  const sections = useDocumentStore(state => state.sections);
  const latestSection = useMemo(() => {
    const storeSection = sections.find(item => item.section_id === section.section_id);
    if (storeSection?.paragraphs?.length) {
      return storeSection;
    }
    return section;
  }, [sections, section]);
  const paragraphs = latestSection.paragraphs ?? [];

  const [filterMode] = useState<FilterMode>('all');
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL);
  const [visibleCount, setVisibleCount] = useState(INITIAL_CHUNK_SIZE);
  const [showBatchRetranslateDialog, setShowBatchRetranslateDialog] = useState(false);

  const {
    drafts,
    dirtyMap,
    savingMap,
    saveErrorMap,
    retranslatingMap,
    retranslateErrorMap,
    dirtyCount,
    savingCount,
    retranslatingCount,
    hasPendingWork,
    updateDraft,
    saveAllNow,
    queueRetranslate,
    confirmParagraph,
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

  const isChunkMode = filteredParagraphs.length > CHUNK_THRESHOLD;

  useEffect(() => {
    setVisibleCount(isChunkMode ? INITIAL_CHUNK_SIZE : filteredParagraphs.length);
  }, [filteredParagraphs.length, isChunkMode]);

  const displayedParagraphs = useMemo(
    () => (isChunkMode ? filteredParagraphs.slice(0, visibleCount) : filteredParagraphs),
    [filteredParagraphs, isChunkMode, visibleCount]
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
      if (container.scrollTop + container.clientHeight >= container.scrollHeight - 240) {
        setVisibleCount(current => Math.min(filteredParagraphs.length, current + CHUNK_SIZE));
      }
    },
    [filteredParagraphs.length, isChunkMode]
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
      const isSaveShortcut = (event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's';
      if (isSaveShortcut) {
        event.preventDefault();
        void saveAllNow();
        return;
      }

      if (event.key === 'Escape') {
        event.preventDefault();
        handleClose();
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [handleClose, saveAllNow]);

  const handleBatchRetranslate = useCallback(
    (template: RetranslateTemplate) => {
      const templateData = RETRANSLATE_TEMPLATES.find(item => item.id === template);
      const instruction = templateData?.instruction;
      void batchRetranslate(selectedModel, instruction);
      setShowBatchRetranslateDialog(false);
    },
    [batchRetranslate, selectedModel]
  );

  return (
    <div className="fixed inset-0 z-[70] flex flex-col bg-bg-primary">
      <div className="border-b border-border-subtle bg-bg-primary/95 px-6 py-3 backdrop-blur">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-medium text-text-primary">{latestSection.title}</h2>
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
              onClick={() => void saveAllNow()}
              disabled={dirtyCount === 0}
              className="flex items-center justify-center rounded-lg border border-border bg-bg-secondary p-2 text-text-primary hover:bg-bg-tertiary disabled:cursor-not-allowed disabled:opacity-50"
              title="保存全部"
            >
              <Save className="h-5 w-5" />
            </button>

            <select
              value={selectedModel}
              onChange={event => setSelectedModel(event.target.value)}
              className="rounded-lg border border-border bg-bg-secondary px-3 py-2 text-sm text-text-primary outline-none hover:bg-bg-tertiary"
              title="选择模型"
            >
              {MODEL_OPTIONS.map(model => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>

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

      <div className="flex-1 overflow-auto px-6 py-2" onScroll={handleListScroll}>
        <div className="space-y-1">
          {displayedParagraphs.map(paragraph => (
            <ImmersiveRow
              key={paragraph.id}
              paragraph={paragraph}
              draft={drafts[paragraph.id] ?? paragraph.translation ?? ''}
              isSaving={Boolean(savingMap[paragraph.id])}
              saveError={saveErrorMap[paragraph.id]}
              isRetranslating={Boolean(retranslatingMap[paragraph.id])}
              retranslateError={retranslateErrorMap[paragraph.id]}
              onChange={value => updateDraft(paragraph.id, value)}
              onRetranslate={(instruction?: string) =>
                queueRetranslate(paragraph.id, selectedModel, instruction)
              }
              onConfirm={() => void confirmParagraph(paragraph.id)}
              isSelectionMode={isSelectionMode}
              isSelected={selectedIds.has(paragraph.id)}
              onToggleSelection={() => toggleSelection(paragraph.id)}
            />
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
              {RETRANSLATE_TEMPLATES.map(template => (
                <button
                  key={template.id}
                  onClick={() => handleBatchRetranslate(template.id)}
                  disabled={retranslatingCount > 0}
                  className="w-full rounded-lg border border-border bg-bg-secondary px-4 py-3 text-left text-sm text-text-primary hover:bg-bg-tertiary disabled:opacity-50"
                >
                  <div className="font-medium">{template.label}</div>
                  {template.instruction && (
                    <div className="mt-1 text-xs text-text-muted">{template.instruction}</div>
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
