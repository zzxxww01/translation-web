import { RotateCw, Save, ChevronDown, Zap, MessageCircle, Briefcase } from 'lucide-react';
import { Button } from '../../../components/ui';
import {
  PARAGRAPH_STATUS_CLASSES,
  PARAGRAPH_STATUS_LABELS,
  ParagraphStatus,
} from '../../../shared/constants';
import { cn } from '../../../shared/utils';
import type { Paragraph } from '../../../shared/types';
import { useState, useMemo } from 'react';

interface ImmersiveRowProps {
  paragraph: Paragraph;
  draft: string;
  isDirty: boolean;
  isSaving: boolean;
  saveError?: string | null;
  isRetranslating: boolean;
  retranslateError?: string | null;
  onChange: (value: string) => void;
  onSaveNow: () => void;
  onRetranslate: (instruction?: string) => void;
  selectedModel: string;
}

function renderSource(paragraph: Paragraph) {
  const elementType = paragraph.element_type ?? 'p';

  if (elementType === 'image') {
    return (
      <img
        src={paragraph.source}
        alt="source"
        className="max-h-72 w-auto rounded border border-border-subtle bg-bg-tertiary object-contain"
        loading="lazy"
      />
    );
  }

  if (elementType === 'table' && paragraph.source_html) {
    return (
      <div
        className="max-h-72 overflow-auto rounded border border-border-subtle bg-bg-tertiary p-3 text-sm"
        dangerouslySetInnerHTML={{ __html: paragraph.source_html }}
      />
    );
  }

  if (elementType === 'code') {
    return (
      <pre className="whitespace-pre-wrap rounded border border-border-subtle bg-bg-tertiary p-3 text-sm leading-6">
        {paragraph.source}
      </pre>
    );
  }

  return <p className="whitespace-pre-wrap text-base leading-7 text-text-primary">{paragraph.source}</p>;
}

export function ImmersiveRow({
  paragraph,
  draft,
  isDirty,
  isSaving,
  saveError,
  isRetranslating,
  retranslateError,
  onChange,
  onSaveNow,
  onRetranslate,
  selectedModel,
}: ImmersiveRowProps) {
  const status = paragraph.status ?? ParagraphStatus.PENDING;
  const statusClass = PARAGRAPH_STATUS_CLASSES[status] ?? 'text-text-muted';
  const statusLabel = PARAGRAPH_STATUS_LABELS[status] ?? status;
  const hasError = Boolean(saveError || retranslateError);

  const [showRetranslateMenu, setShowRetranslateMenu] = useState(false);
  const [customInstruction, setCustomInstruction] = useState('');

  const quickInstructions = [
    {
      id: 'readable',
      label: '可读性',
      icon: <Zap className="h-3 w-3" />,
      instruction: '请提升可读性：拆分过长句，优化语序，减少冗余连接词，保持信息完整和逻辑清晰。',
    },
    {
      id: 'professional',
      label: '专业化',
      icon: <Briefcase className="h-3 w-3" />,
      instruction: '请提升专业表达：术语更准确、行业表述更规范，保留技术细节和判断力度。',
    },
    {
      id: 'idiomatic',
      label: '更地道',
      icon: <MessageCircle className="h-3 w-3" />,
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

  const calculateRows = (text: string) => {
    const lines = text.split('\n').length;
    return Math.max(3, Math.min(lines + 1, 20));
  };

  return (
    <div
      className={cn(
        'border-b border-border-subtle bg-bg-card p-2',
        hasError && 'border-error/60'
      )}
    >
      <div className="mb-2 flex items-center justify-between gap-3 py-1">
        <div className="flex items-center gap-2 text-xs">
          <span className={cn('font-medium', statusClass)}>{statusLabel}</span>
          {isDirty && <span className="text-warning">未保存</span>}
          {isSaving && <span className="text-info">保存中</span>}
        </div>
        <div className="flex items-center gap-2">
          {/* 重译下拉菜单 */}
          <div className="relative">
            {showRetranslateMenu && (
              <div className="absolute bottom-full right-0 mb-2 w-80 rounded-lg border border-border bg-bg-primary shadow-lg z-10">
                <div className="p-2 space-y-2">
                  <div className="px-3 py-1.5 text-xs text-text-muted font-medium">快捷指令</div>
                  {quickInstructions.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleQuickRetranslate(item.instruction)}
                      disabled={isRetranslating}
                      className="flex w-full items-center gap-2 rounded px-3 py-2 text-sm text-text-primary hover:bg-bg-tertiary disabled:opacity-50"
                    >
                      {item.icon}
                      <span>{item.label}</span>
                    </button>
                  ))}
                  <div className="border-t border-border-subtle pt-2">
                    <div className="px-3 py-1 text-xs text-text-muted font-medium">自定义</div>
                    <textarea
                      value={customInstruction}
                      onChange={event => setCustomInstruction(event.target.value)}
                      placeholder="输入重译要求"
                      className="h-16 w-full resize-none rounded border border-border-subtle bg-bg-secondary px-2 py-1.5 text-sm text-text-primary outline-none focus:border-primary-500"
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
                onClick={() => setShowRetranslateMenu(!showRetranslateMenu)}
                disabled={isRetranslating}
                className="flex items-center justify-center px-2 rounded-r-lg border border-border bg-bg-secondary hover:bg-bg-tertiary disabled:opacity-50"
              >
                <ChevronDown className={`h-4 w-4 transition-transform ${showRetranslateMenu ? 'rotate-180' : ''}`} />
              </button>
            </div>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={onSaveNow}
            disabled={!isDirty || isSaving}
            leftIcon={<Save className="h-4 w-4" />}
          >
            保存
          </Button>
        </div>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <div className="min-h-20 overflow-auto rounded bg-bg-secondary p-2">{renderSource(paragraph)}</div>

        <textarea
          value={draft}
          onChange={event => onChange(event.target.value)}
          rows={calculateRows(draft)}
          className="min-h-20 w-full resize-y rounded border border-border bg-bg-secondary p-2 text-base leading-7 text-text-primary placeholder:text-text-muted focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          placeholder="输入或修改译文..."
        />
      </div>

      {(saveError || retranslateError) && (
        <div className="mt-2 rounded bg-error/10 px-3 py-2 text-sm text-error">
          {saveError || retranslateError}
        </div>
      )}
    </div>
  );
}
