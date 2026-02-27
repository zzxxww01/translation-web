/**
 * 原文面板组件
 * 显示左侧原文内容（30%宽度）
 */

import { useState } from 'react';
import { BookOpen } from 'lucide-react';
import { cn } from '../../../shared/utils';
import type { Paragraph } from '../types';
import { GlossaryModal } from './GlossaryModal';

interface SourcePanelProps {
  paragraph: Paragraph | null;
  projectId?: string;
  className?: string;
}

export function SourcePanel({ paragraph, projectId = '', className }: SourcePanelProps) {
  const [isGlossaryOpen, setIsGlossaryOpen] = useState(false);

  if (!paragraph) {
    return (
      <div className={cn('w-[30%] border-r border-border bg-muted/30 p-6', className)}>
        <div className="flex h-full items-center justify-center text-text-secondary">
          加载中...
        </div>
      </div>
    );
  }

  return (
    <div className={cn('w-[30%] border-r border-border bg-muted/30 p-6 overflow-y-auto relative', className)}>
      {/* 术语库按钮 */}
      {projectId && (
        <button
          onClick={() => setIsGlossaryOpen(true)}
          className={cn(
            'absolute top-4 right-4 rounded-lg p-2',
            'text-text-secondary hover:text-primary hover:bg-primary/10',
            'transition-all',
            'group'
          )}
          title="打开术语库"
        >
          <BookOpen className="h-4 w-4" />
        </button>
      )}

      {/* 章节标题 */}
      <div className="mb-4">
        <div className="text-xs font-medium text-text-secondary uppercase tracking-wide">
          章节
        </div>
        <div className="text-sm font-semibold text-text-primary mt-1">
          {paragraph.section_title}
        </div>
      </div>

      {/* 段落索引 */}
      <div className="mb-4">
        <div className="text-xs font-medium text-text-secondary uppercase tracking-wide">
          段落
        </div>
        <div className="text-sm font-semibold text-text-primary mt-1">
          #{paragraph.index + 1}
        </div>
      </div>

      {/* 原文内容 */}
      <div className="prose prose-sm max-w-none">
        <div className="text-xs font-medium text-text-secondary uppercase tracking-wide mb-2">
          原文
        </div>
        <div className="text-text-primary whitespace-pre-wrap leading-relaxed">
          {paragraph.source}
        </div>
      </div>

      {/* 状态标签 */}
      <div className="mt-6 pt-4 border-t border-border">
        <div className="inline-flex items-center gap-2 rounded-full bg-primary/10 px-3 py-1">
          <div
            className={cn(
              'h-2 w-2 rounded-full',
              paragraph.status === 'approved'
                ? 'bg-success'
                : paragraph.status === 'translated'
                ? 'bg-warning'
                : 'bg-text-tertiary'
            )}
          />
          <span className="text-xs font-medium text-primary">
            {paragraph.status === 'approved'
              ? '已确认'
              : paragraph.status === 'translated'
              ? '已翻译'
              : '待处理'}
          </span>
        </div>
      </div>

      {/* 术语库模态框 */}
      {projectId && (
        <GlossaryModal
          isOpen={isGlossaryOpen}
          onClose={() => setIsGlossaryOpen(false)}
          projectId={projectId}
        />
      )}
    </div>
  );
}
