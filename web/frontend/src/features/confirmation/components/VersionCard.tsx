/**
 * 版本卡片组件
 * 显示单个翻译版本（AI版本或参考版本）
 */

import { Check } from 'lucide-react';
import { cn } from '../../../shared/utils';
import { Button } from '../../../components/ui';
import type { VersionCardProps } from '../types';
import { AIInsightPanel } from './AIInsightPanel';

export function VersionCard({
  version,
  isSelected,
  onSelect,
  onEdit,
}: VersionCardProps) {
  const isAI = version.source_type === 'ai';

  return (
    <div
      className={cn(
        'group relative rounded-2xl border-2 bg-card p-4 transition-all',
        'hover:shadow-lg hover:-translate-y-0.5',
        isAI ? 'border-l-4 border-l-primary' : 'border-l-4 border-l-success',
        isSelected
          ? 'ring-2 ring-primary ring-offset-2 border-primary'
          : 'border-border hover:border-primary/50'
      )}
    >
      {/* 版本头部 */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg" role="img" aria-label="version-icon">
            {isAI ? '⭐' : '📄'}
          </span>
          <span className="font-semibold text-text-primary">{version.name}</span>
          {isAI && (
            <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              推荐
            </span>
          )}
        </div>
        {isSelected && (
          <div className="flex items-center gap-1 text-primary">
            <Check size={16} />
            <span className="text-xs font-medium">已选择</span>
          </div>
        )}
      </div>

      {/* 版本内容 */}
      <div className="mb-3 text-sm leading-relaxed text-text-secondary whitespace-pre-wrap">
        {version.translation}
      </div>

      {/* 操作按钮 */}
      <div className="flex gap-2">
        <Button
          variant={isSelected ? 'primary' : 'secondary'}
          size="sm"
          onClick={() => onSelect(version.id)}
          className="flex-1"
        >
          {isSelected ? '已选择' : '采用此版本'}
        </Button>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => onEdit(version)}
        >
          编辑
        </Button>
      </div>

      {/* AI透明度面板 */}
      {isAI && version.ai_insight && (
        <AIInsightPanel insight={version.ai_insight} />
      )}
    </div>
  );
}
