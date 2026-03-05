import { RotateCw, Save } from 'lucide-react';
import { Button } from '../../../components/ui';
import {
  PARAGRAPH_STATUS_CLASSES,
  PARAGRAPH_STATUS_LABELS,
  ParagraphStatus,
} from '../../../shared/constants';
import { cn } from '../../../shared/utils';
import type { Paragraph } from '../../../shared/types';

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
  onRetranslate: () => void;
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
}: ImmersiveRowProps) {
  const status = paragraph.status ?? ParagraphStatus.PENDING;
  const statusClass = PARAGRAPH_STATUS_CLASSES[status] ?? 'text-text-muted';
  const statusLabel = PARAGRAPH_STATUS_LABELS[status] ?? status;
  const hasError = Boolean(saveError || retranslateError);

  return (
    <div
      className={cn(
        'rounded-xl border border-border-subtle bg-bg-card p-4',
        hasError && 'border-error/60'
      )}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm">
          <span className="rounded bg-bg-tertiary px-2 py-0.5 text-text-muted">#{paragraph.index}</span>
          <span className={cn('font-medium', statusClass)}>{statusLabel}</span>
          {isDirty && <span className="text-warning">未保存</span>}
          {isSaving && <span className="text-info">保存中</span>}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={onRetranslate}
            isLoading={isRetranslating}
            leftIcon={<RotateCw className="h-4 w-4" />}
          >
            重译
          </Button>
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

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wide text-text-muted">原文</div>
          <div className="max-h-80 overflow-auto rounded-lg bg-bg-secondary p-3">{renderSource(paragraph)}</div>
        </div>

        <div className="space-y-2">
          <div className="text-xs font-semibold uppercase tracking-wide text-text-muted">译文</div>
          <textarea
            value={draft}
            onChange={event => onChange(event.target.value)}
            className="h-80 w-full resize-y rounded-lg border border-border bg-bg-secondary p-3 text-base leading-7 text-text-primary placeholder:text-text-muted focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            placeholder="输入或修改译文..."
          />
        </div>
      </div>

      {(saveError || retranslateError) && (
        <div className="mt-3 rounded bg-error/10 px-3 py-2 text-sm text-error">
          {saveError || retranslateError}
        </div>
      )}
    </div>
  );
}
