import { sanitizeSourceHtml } from '@/shared/safeHtml';
/**
 * 段落列表项组件
 * 显示单个段落的信息和状态
 */

import { Check } from 'lucide-react';
import { type FC } from 'react';
import type { Paragraph } from '../../../shared/types';
import { cn } from '../../../shared/utils';
import {
  PARAGRAPH_STATUS_CLASSES,
  PARAGRAPH_STATUS_LABELS,
  ParagraphStatus,
} from '../../../shared/constants';

interface ParagraphItemProps {
  paragraph: Paragraph;
  isActive: boolean;
  onClick: () => void;
}

export const ParagraphItem: FC<ParagraphItemProps> = ({
  paragraph,
  isActive,
  onClick,
}) => {
  const status = paragraph.status ?? ParagraphStatus.PENDING;
  const isConfirmed = status === ParagraphStatus.APPROVED;
  const elementType = paragraph.element_type ?? 'p';

  const renderSource = () => {
    if (elementType === 'image') {
      return (
        <img
          src={paragraph.source}
          alt="image"
          className="max-h-48 w-auto rounded border border-border-subtle bg-bg-tertiary object-contain"
          loading="lazy"
        />
      );
    }
    if (elementType === 'table' && paragraph.source_html) {
      return (
        <div
          className="max-h-48 overflow-auto rounded border border-border-subtle bg-bg-tertiary p-2 text-sm"
          dangerouslySetInnerHTML={{ __html: sanitizeSourceHtml(paragraph.source_html) }}
        />
      );
    }
    if (elementType === 'code') {
      return (
        <pre className="whitespace-pre-wrap rounded border border-border-subtle bg-bg-tertiary p-2 text-sm">
          {paragraph.source}
        </pre>
      );
    }
    return <span>{paragraph.source}</span>;
  };

  return (
    <div
      onClick={onClick}
      className={cn(
        'group cursor-pointer rounded-xl border px-5 py-4 transition-colors',
        isActive
          ? 'border-primary-300 bg-paper-hover'
          : 'border-border-subtle bg-white hover:border-primary-200 hover:bg-paper-hover/60'
      )}
    >
      {/* 段号和状态：一行小字，状态只写一次（点 + 文字），不再叠彩色边框和徽章 */}
      <div className="mb-2 flex items-center gap-2 text-xs text-text-muted">
        <span className="tabular-nums">#{paragraph.index}</span>
        <span className={cn('inline-flex items-center gap-1', PARAGRAPH_STATUS_CLASSES[status])}>
          {isConfirmed ? <Check className="h-3.5 w-3.5" /> : <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />}
          {PARAGRAPH_STATUS_LABELS[status]}
        </span>
      </div>

      {/* 原文：英文衬线体，浅一级 */}
      <div className="mb-2 font-[family-name:var(--font-source)] text-[14.5px] leading-[1.75] text-text-secondary">
        {renderSource()}
      </div>

      {/* 译文：中文宋体 */}
      <div className="font-[family-name:var(--font-display)] text-[15.5px] leading-[1.9] text-text-primary">
        {paragraph.translation ?? <span className="font-[family-name:var(--font-body)] text-sm text-text-disabled">还没翻译，点开在右边翻</span>}
      </div>
    </div>
  );
};
