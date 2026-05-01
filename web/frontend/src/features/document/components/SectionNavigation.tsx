/**
 * 章节导航组件
 * 用于在章节之间切换，支持上一章/下一章导航
 */

import { type FC } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '../../../shared/utils';
import type { Section } from '../../../shared/types';

export interface SectionNavigationProps {
  sections: Section[];
  currentSection: Section | null;
  onSectionChange: (section: Section) => void;
  className?: string;
}

export const SectionNavigation: FC<SectionNavigationProps> = ({
  sections,
  currentSection,
  onSectionChange,
  className,
}) => {
  if (sections.length === 0) return null;

  const currentIndex = currentSection
    ? sections.findIndex(s => s.section_id === currentSection.section_id)
    : -1;

  const hasPrevious = currentIndex > 0;
  const hasNext = currentIndex < sections.length - 1;

  const goToPrevious = () => {
    if (hasPrevious) {
      onSectionChange(sections[currentIndex - 1]);
    }
  };

  const goToNext = () => {
    if (hasNext) {
      onSectionChange(sections[currentIndex + 1]);
    }
  };

  return (
    <div className={cn('flex items-center gap-2 rounded-lg bg-white/70 p-1', className)}>
      {/* 上一章按钮 */}
      <button
        onClick={goToPrevious}
        disabled={!hasPrevious}
        className={cn(
          'flex min-h-10 items-center gap-1 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          'disabled:cursor-not-allowed disabled:opacity-50',
          hasPrevious
            ? 'bg-primary-100 text-primary-700 hover:bg-primary-200'
            : 'bg-bg-muted text-text-muted'
        )}
      >
        <ChevronLeft className="h-4 w-4" />
        <span className="hidden sm:inline">上一章</span>
      </button>

      {/* 章节信息 */}
      <div className="min-w-0 flex-1 text-center">
        {currentSection ? (
          <div className="text-sm">
            <span className="text-text-muted">第 {currentIndex + 1} 章 / 共 {sections.length} 章</span>
            {currentSection.title && (
              <div className="truncate px-1 font-medium text-text-primary">
                {currentSection.title}
              </div>
            )}
          </div>
        ) : (
          <span className="text-sm text-text-muted">选择章节开始翻译</span>
        )}
      </div>

      {/* 下一章按钮 */}
      <button
        onClick={goToNext}
        disabled={!hasNext}
        className={cn(
          'flex min-h-10 items-center gap-1 rounded-md px-3 py-2 text-sm font-medium transition-colors',
          'disabled:cursor-not-allowed disabled:opacity-50',
          hasNext
            ? 'bg-primary-100 text-primary-700 hover:bg-primary-200'
            : 'bg-bg-muted text-text-muted'
        )}
      >
        <span className="hidden sm:inline">下一章</span>
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
};

/**
 * 简化的章节选择器组件
 */
export interface SectionSelectorProps {
  sections: Section[];
  currentSectionId: string | null;
  onSectionChange: (sectionId: string) => void;
  className?: string;
}

export const SectionSelector: FC<SectionSelectorProps> = ({
  sections,
  currentSectionId,
  onSectionChange,
  className,
}) => {
  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {sections.map((section, index) => {
        const isActive = section.section_id === currentSectionId;
        const isComplete = section.is_complete;

        return (
          <button
            key={section.section_id}
            onClick={() => onSectionChange(section.section_id)}
            className={cn(
              'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              'disabled:cursor-not-allowed disabled:opacity-50',
              isActive
                ? 'bg-primary-500 text-white'
                : 'bg-bg-card text-text-primary hover:bg-bg-muted',
              isComplete && !isActive && 'border border-success-500 text-success-700'
            )}
          >
            <span className="hidden sm:inline">第 {index + 1} 章</span>
            <span className="sm:hidden">#{index + 1}</span>
            {isComplete && (
              <span className="ml-1 text-success-600">✓</span>
            )}
          </button>
        );
      })}
    </div>
  );
};
