/**
 * 段落列表项组件
 * 显示单个段落的信息和状态
 */

import { Check } from 'lucide-react';
import { type FC } from 'react';
import type { Paragraph } from '../../../shared/types';
import { cn } from '../../../shared/utils';
import {
  PARAGRAPH_STATUS_ICONS,
  PARAGRAPH_STATUS_CLASSES,
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
          dangerouslySetInnerHTML={{ __html: paragraph.source_html }}
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
        'group cursor-pointer rounded-lg border p-5 transition-all',
        isActive
          ? 'border-primary-500 bg-primary-50 shadow-md'
          : 'border-border-subtle bg-bg-card hover:border-primary-300 hover:shadow-sm',
        // 已确认的段落有绿色边框标识
        isConfirmed && !isActive && 'border-l-4 border-l-green-500'
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-sm text-text-muted">#{paragraph.index}</span>
            <span className={cn('text-sm', PARAGRAPH_STATUS_CLASSES[status])}>
              {PARAGRAPH_STATUS_ICONS[status]}
            </span>
            {/* 已确认标识 */}
            {isConfirmed && (
              <span className="flex items-center gap-1.5 rounded-full bg-green-100 px-2.5 py-1 text-sm font-medium text-green-700">
                <Check className="h-4 w-4" />
                已确认
              </span>
            )}
          </div>

          {/* 原文 */}
          <div className="mb-2 text-base leading-relaxed text-text-primary">
            {renderSource()}
          </div>

          {/* 译文 */}
          <div className="text-base leading-relaxed text-text-secondary">
            {paragraph.translation ?? <span className="text-text-muted">点击翻译...</span>}
          </div>
        </div>
      </div>
    </div>
  );
};
