import {
  Cpu,
  Filter,
  Minimize2,
  Save,
} from 'lucide-react';
import { type UIEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { Button } from '../../../components/ui';
import {
  DEFAULT_MODEL,
  MODEL_OPTIONS,
  ParagraphStatus,
} from '../../../shared/constants';
import type { Paragraph, Section } from '../../../shared/types';
import { useImmersiveEditor } from '../hooks/useImmersiveEditor';
import { ImmersiveRow } from './ImmersiveRow';

const CHUNK_THRESHOLD = 300;
const INITIAL_CHUNK_SIZE = 80;
const CHUNK_SIZE = 40;

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
  const paragraphs = section.paragraphs ?? [];
  const [filterMode, setFilterMode] = useState<FilterMode>('all');
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL);
  const [visibleCount, setVisibleCount] = useState(INITIAL_CHUNK_SIZE);

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
    saveNow,
    saveAllNow,
    queueRetranslate,
  } = useImmersiveEditor({
    projectId,
    sectionId: section.section_id,
    paragraphs,
  });

  const filteredParagraphs = useMemo(() => {
    return paragraphs.filter(paragraph => {
      const matchesStatus = matchesFilter(filterMode, paragraph, Boolean(dirtyMap[paragraph.id]));
      return matchesStatus;
    });
  }, [dirtyMap, filterMode, paragraphs]);

  const isChunkMode = filteredParagraphs.length > CHUNK_THRESHOLD;

  useEffect(() => {
    setVisibleCount(isChunkMode ? INITIAL_CHUNK_SIZE : filteredParagraphs.length);
  }, [filteredParagraphs.length, isChunkMode]);

  const displayedParagraphs = useMemo(
    () => (isChunkMode ? filteredParagraphs.slice(0, visibleCount) : filteredParagraphs),
    [filteredParagraphs, isChunkMode, visibleCount]
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

  return (
    <div className="fixed inset-0 z-[70] flex flex-col bg-bg-primary">
      <div className="border-b border-border-subtle bg-bg-primary/95 px-6 py-3 backdrop-blur">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-4">
            <h2 className="text-lg font-semibold text-text-primary">沉浸编辑 · {section.title}</h2>
            <span className="text-sm text-text-muted">
              共 {paragraphs.length} 段 · 未保存 {dirtyCount} · 保存中 {savingCount} · 重译中 {retranslatingCount}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 rounded-lg border border-border-subtle bg-bg-secondary px-3 py-1.5">
              <Filter className="h-4 w-4 text-text-muted" />
              <select
                value={filterMode}
                onChange={event => setFilterMode(event.target.value as FilterMode)}
                className="bg-transparent text-sm text-text-primary outline-none"
              >
                <option value="all">全部</option>
                <option value="translated">已翻译</option>
                <option value="approved">已确认</option>
                <option value="modified">已修改</option>
              </select>
            </label>

            <label className="flex items-center gap-2 rounded-lg border border-border-subtle bg-bg-secondary px-3 py-1.5">
              <Cpu className="h-4 w-4 text-text-muted" />
              <select
                value={selectedModel}
                onChange={event => setSelectedModel(event.target.value)}
                className="bg-transparent text-sm text-text-primary outline-none"
              >
                {MODEL_OPTIONS.map(model => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </label>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => void saveAllNow()}
              disabled={dirtyCount === 0}
              leftIcon={<Save className="h-4 w-4" />}
            >
              保存全部
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleClose}
              leftIcon={<Minimize2 className="h-4 w-4" />}
            >
              退出沉浸
            </Button>
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
              isDirty={Boolean(dirtyMap[paragraph.id])}
              isSaving={Boolean(savingMap[paragraph.id])}
              saveError={saveErrorMap[paragraph.id]}
              isRetranslating={Boolean(retranslatingMap[paragraph.id])}
              retranslateError={retranslateErrorMap[paragraph.id]}
              onChange={value => updateDraft(paragraph.id, value)}
              onSaveNow={() => void saveNow(paragraph.id)}
              onRetranslate={(instruction?: string) => queueRetranslate(paragraph.id, selectedModel, instruction)}
              selectedModel={selectedModel}
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
    </div>
  );
}
