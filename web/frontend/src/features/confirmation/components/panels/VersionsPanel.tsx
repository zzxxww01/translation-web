/**
 * 版本列表面板组件
 * 显示右侧所有翻译版本（70%宽度）
 */

import { useState } from 'react';
import { cn } from '../../../../shared/utils';
import { VersionCard } from '../cards/VersionCard';
import { EditCard } from '../cards/EditCard';
import { RetranslatePanel } from './RetranslatePanel';
import { useConfirmationStore } from '../../stores/confirmationStore';
import type { ParagraphVersion } from '../../types';

interface VersionsPanelProps {
  className?: string;
  onSelectVersion: (versionId: string) => void;
  onEditVersion: (version: ParagraphVersion) => void;
  onConfirm: (translation: string) => void;
  onRetranslate?: (instruction: string, model?: string) => Promise<void>;
  isRetranslating?: boolean;
}

export function VersionsPanel({
  className,
  onSelectVersion,
  onEditVersion,
  onConfirm,
  onRetranslate,
  isRetranslating = false,
}: VersionsPanelProps) {
  const { versions, currentParagraph, selectedVersionId, customTranslation, totalParagraphs } =
    useConfirmationStore();

  const [showRetranslate, setShowRetranslate] = useState(false);

  const handleRetranslate = async (instruction: string, model?: string) => {
    if (onRetranslate) {
      await onRetranslate(instruction, model);
      setShowRetranslate(false);
    }
  };

  if (!currentParagraph) {
    return (
      <div className={cn('flex-1 flex items-center justify-center', className)}>
        <div className="text-text-secondary">加载中...</div>
      </div>
    );
  }

  return (
    <div className={cn('flex-1 overflow-y-auto p-6', className)}>
      {/* 进度信息 */}
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            第 {currentParagraph.index + 1} 段 / 共 {totalParagraphs || '?'} 段
          </h2>
          <p className="text-sm text-text-secondary mt-1">
            请选择一个版本或自定义编辑，然后确认译文
          </p>
        </div>
        {onRetranslate && (
          <button
            onClick={() => setShowRetranslate(!showRetranslate)}
            className={cn(
              'text-sm font-medium transition-colors',
              showRetranslate ? 'text-primary' : 'text-text-secondary hover:text-primary'
            )}
          >
            {showRetranslate ? '收起' : '重新翻译'}
          </button>
        )}
      </div>

      {/* 重新翻译面板 */}
      {showRetranslate && onRetranslate && (
        <div className="mb-4">
          <RetranslatePanel
            onRetranslate={handleRetranslate}
            isRetranslating={isRetranslating}
          />
        </div>
      )}

      {/* 版本列表 */}
      <div className="space-y-4">
        {versions.map((version) => (
          <VersionCard
            key={version.id}
            version={version}
            isSelected={selectedVersionId === version.id}
            onSelect={onSelectVersion}
            onEdit={onEditVersion}
          />
        ))}

        {/* 编辑卡片 */}
        <EditCard
          value={customTranslation}
          onChange={(value: string) => useConfirmationStore.getState().setCustomTranslation(value)}
          onConfirm={onConfirm}
        />
      </div>
    </div>
  );
}
