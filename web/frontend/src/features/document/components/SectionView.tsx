/**
 * 章节视图组件
 * 显示选中章节的段落列表
 */

import { Loader2, Maximize2 } from 'lucide-react';
import { ParagraphItem } from './ParagraphItem';
import { SectionNavigation } from './SectionNavigation';
import { Button } from '@/components/ui/button-extended';
import type { Section, Paragraph } from '@/shared/types';

interface SectionViewProps {
  sections: Section[];
  currentSection: Section | null;
  currentParagraph: Paragraph | null;
  isLoading: boolean;
  isRefetching?: boolean;
  onSectionChange: (section: Section) => void;
  onParagraphSelect: (paragraph: Paragraph) => void;
  onEnterImmersive?: () => void;
}

export function SectionView({
  sections,
  currentSection,
  currentParagraph,
  isLoading,
  isRefetching = false,
  onSectionChange,
  onParagraphSelect,
  onEnterImmersive,
}: SectionViewProps) {
  if (!currentSection || isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-5 sm:px-6 sm:py-6">
      {/* 刷新指示器 */}
      {isRefetching && (
        <div className="mb-4 flex items-center justify-center text-sm text-text-muted">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          正在刷新...
        </div>
      )}

      {/* 章节标题 */}
      <div className="mb-6 flex flex-col items-start justify-between gap-3 sm:flex-row">
        <div className="min-w-0">
          <h2 className="text-xl font-bold">{currentSection.title}</h2>
          {currentSection.title_translation && (
            <p className="text-text-muted">{currentSection.title_translation}</p>
          )}
        </div>
        {onEnterImmersive && (
          <Button
            variant="outline"
            size="sm"
            type="button"
            onClick={onEnterImmersive}
            leftIcon={<Maximize2 className="h-4 w-4" />}
          >
            沉浸编辑
          </Button>
        )}
      </div>

      {/* 章节导航 */}
      <div className="mb-4">
        <SectionNavigation
          sections={sections}
          currentSection={currentSection}
          onSectionChange={onSectionChange}
        />
      </div>

      {/* 段落列表 */}
      <div className="space-y-3">
        {currentSection.paragraphs?.map(paragraph => (
          <ParagraphItem
            key={paragraph.id}
            paragraph={paragraph}
            isActive={currentParagraph?.id === paragraph.id}
            onClick={() => onParagraphSelect(paragraph)}
          />
        ))}
      </div>

      {/* 底部导航 */}
      <div className="sticky bottom-0 z-10 -mx-4 mt-6 flex justify-center border-t bg-background/95 px-4 py-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] backdrop-blur-sm sm:static sm:mx-0 sm:border-0 sm:bg-transparent sm:px-0 sm:pb-3 sm:backdrop-blur-none">
        <SectionNavigation
          sections={sections}
          currentSection={currentSection}
          onSectionChange={onSectionChange}
        />
      </div>
    </div>
  );
}
