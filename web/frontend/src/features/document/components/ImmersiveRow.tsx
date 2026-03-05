import { Check, ChevronDown, RotateCw } from 'lucide-react';
import { useRef, useState } from 'react';
import { Button } from '../../../components/ui';
import { ParagraphStatus } from '../../../shared/constants';
import type { Paragraph } from '../../../shared/types';
import { cn } from '../../../shared/utils';

interface ImmersiveRowProps {
  paragraph: Paragraph;
  draft: string;
  isSaving: boolean;
  saveError?: string | null;
  isRetranslating: boolean;
  retranslateError?: string | null;
  onChange: (value: string) => void;
  onRetranslate: (instruction?: string) => void;
  onConfirm: () => void;
  isSelectionMode: boolean;
  isSelected: boolean;
  onToggleSelection: () => void;
}

function renderSource(paragraph: Paragraph, isApproved: boolean) {
  const elementType = paragraph.element_type ?? 'p';
  const bgClass = isApproved ? 'bg-green-50' : 'bg-bg-secondary';

  if (elementType === 'image') {
    return (
      <img
        src={paragraph.source}
        alt="source"
        className={`max-h-72 w-auto rounded border border-border-subtle object-contain ${bgClass}`}
        loading="lazy"
      />
    );
  }

  if (elementType === 'table' && paragraph.source_html) {
    return (
      <div
        className={`max-h-72 overflow-auto rounded border border-border-subtle p-3 text-sm ${bgClass}`}
        dangerouslySetInnerHTML={{ __html: paragraph.source_html }}
      />
    );
  }

  if (elementType === 'code') {
    return (
      <pre className={`whitespace-pre-wrap rounded border border-border-subtle p-3 text-sm leading-6 ${bgClass}`}>
        {paragraph.source}
      </pre>
    );
  }

  return <p className="whitespace-pre-wrap text-base leading-7 text-text-primary">{paragraph.source}</p>;
}

export function ImmersiveRow({
  paragraph,
  draft,
  isSaving,
  saveError,
  isRetranslating,
  retranslateError,
  onChange,
  onRetranslate,
  onConfirm,
  isSelectionMode,
  isSelected,
  onToggleSelection,
}: ImmersiveRowProps) {
  const status = paragraph.status ?? ParagraphStatus.PENDING;
  const isApproved = status === ParagraphStatus.APPROVED;
  const hasError = Boolean(saveError || retranslateError);

  const [showRetranslateMenu, setShowRetranslateMenu] = useState(false);
  const [customInstruction, setCustomInstruction] = useState('');
  const [menuPosition, setMenuPosition] = useState<'top' | 'bottom'>('top');
  const menuButtonRef = useRef<HTMLDivElement>(null);

  const quickInstructions = [
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

  const handleQuickRetranslate = (instruction: string) => {
    setShowRetranslateMenu(false);
    onRetranslate(instruction);
  };

  const handleCustomRetranslate = () => {
    const instruction = customInstruction.trim();
    if (!instruction) return;
    setCustomInstruction('');
    setShowRetranslateMenu(false);
    onRetranslate(instruction);
  };

  const handleToggleMenu = () => {
    if (!showRetranslateMenu && menuButtonRef.current) {
      const rect = menuButtonRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      setMenuPosition(spaceBelow > 300 ? 'bottom' : 'top');
    }
    setShowRetranslateMenu(previous => !previous);
  };

  const calculateRows = (text: string) => {
    const lines = text.split('\n').length;
    return Math.max(3, Math.min(lines + 1, 20));
  };

  const handleRowClick = () => {
    if (isSelectionMode) {
      onToggleSelection();
    }
  };

  return (
    <div
      onClick={handleRowClick}
      className={cn(
        'border-b border-border-subtle p-2 transition-all',
        isApproved ? 'bg-green-50' : 'bg-bg-card',
        hasError && 'border-error/60',
        isSelectionMode && 'cursor-pointer hover:opacity-90',
        isSelectionMode && isSelected && 'ring-2 ring-primary-500'
      )}
    >
      {isSelectionMode && (
        <div className="mb-2 flex items-center gap-2" onClick={event => event.stopPropagation()}>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onToggleSelection}
            className="h-4 w-4 rounded border-border text-primary-500 focus:ring-2 focus:ring-primary-500"
          />
        </div>
      )}

      <div className="grid gap-3 lg:grid-cols-2" onClick={event => event.stopPropagation()}>
        <div className={`min-h-20 overflow-auto rounded p-2 ${isApproved ? 'bg-green-50' : 'bg-bg-secondary'}`}>
          {renderSource(paragraph, isApproved)}
        </div>

        <textarea
          value={draft}
          onChange={event => onChange(event.target.value)}
          rows={calculateRows(draft)}
          className={`min-h-20 w-full resize-y rounded border border-border p-2 text-base leading-7 text-text-primary placeholder:text-text-muted focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 ${
            isApproved ? 'bg-green-50' : 'bg-bg-secondary'
          }`}
          placeholder="输入或修改译文..."
        />
      </div>

      <div className="mt-2 flex items-center justify-end gap-2" onClick={event => event.stopPropagation()}>
        <div className="relative" ref={menuButtonRef}>
          {showRetranslateMenu && (
            <div
              className={cn(
                'absolute right-0 z-10 w-96 rounded-lg border border-border bg-bg-primary shadow-lg',
                menuPosition === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'
              )}
            >
              <div className="space-y-3 p-3">
                <div className="flex gap-2">
                  {quickInstructions.map(item => (
                    <button
                      key={item.id}
                      onClick={() => handleQuickRetranslate(item.instruction)}
                      disabled={isRetranslating}
                      className="flex-1 rounded-lg border border-border bg-bg-secondary px-3 py-2 text-sm text-text-primary transition-colors hover:bg-bg-tertiary disabled:opacity-50"
                    >
                      {item.label}
                    </button>
                  ))}
                </div>

                <div className="border-t border-border-subtle pt-3">
                  <div className="mb-2 text-xs font-medium text-text-muted">自定义指令</div>
                  <textarea
                    value={customInstruction}
                    onChange={event => setCustomInstruction(event.target.value)}
                    placeholder="输入重译要求..."
                    className="h-20 w-full resize-none rounded border border-border-subtle bg-bg-secondary px-3 py-2 text-sm text-text-primary outline-none focus:border-primary-500"
                    disabled={isRetranslating}
                  />
                  <div className="mt-2 flex justify-end">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleCustomRetranslate}
                      disabled={!customInstruction.trim() || isRetranslating}
                    >
                      重译
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="flex">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onRetranslate()}
              isLoading={isRetranslating}
              leftIcon={<RotateCw className="h-4 w-4" />}
              className="rounded-r-none border-r-0"
            >
              重译
            </Button>
            <button
              onClick={handleToggleMenu}
              disabled={isRetranslating}
              className="flex items-center justify-center rounded-r-lg border border-border bg-bg-secondary px-2 hover:bg-bg-tertiary disabled:opacity-50"
            >
              <ChevronDown className={`h-4 w-4 transition-transform ${showRetranslateMenu ? 'rotate-180' : ''}`} />
            </button>
          </div>
        </div>

        <Button
          variant="primary"
          size="sm"
          onClick={onConfirm}
          isLoading={isSaving}
          disabled={isRetranslating}
          leftIcon={<Check className="h-4 w-4" />}
        >
          确认
        </Button>
      </div>

      {(saveError || retranslateError) && (
        <div className="mt-2 rounded bg-error/10 px-3 py-2 text-sm text-error">
          {saveError || retranslateError}
        </div>
      )}
    </div>
  );
}
