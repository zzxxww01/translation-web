import { type FC } from 'react';
import { CheckCircle, Clock, FileText } from 'lucide-react';
import type { Section } from '../../../shared/types';
import { cn } from '../../../shared/utils';

interface SectionListProps {
  sections: Section[];
  activeSectionId?: string;
  onSelectSection: (sectionId: string) => void;
}

export const SectionList: FC<SectionListProps> = ({
  sections,
  activeSectionId,
  onSelectSection,
}) => {
  if (sections.length === 0) {
    return (
      <div className="flex flex-col items-center py-8 text-text-muted">
        <FileText className="mb-2 h-8 w-8" />
        <p className="text-sm">暂无章节</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {sections.map(section => {
        const isActive = section.section_id === activeSectionId;
        const percent = section.total_paragraphs > 0
          ? (section.approved_count / section.total_paragraphs) * 100
          : 0;

        return (
          <button
            key={section.section_id}
            onClick={() => onSelectSection(section.section_id)}
            className={cn(
              'relative w-full rounded-lg p-2.5 text-left transition-all border-l-2 border-transparent',
              isActive
                ? 'border-l-primary-500 bg-primary-50/50 text-primary-700'
                : 'hover:bg-bg-tertiary hover:shadow-sm'
            )}
          >
            <div className="flex items-start gap-1.5">
              {/* 状态图标 */}
              <div className="mt-0.5 flex-shrink-0">
                {section.is_complete ? (
                  <CheckCircle className="h-4 w-4 text-success" />
                ) : (
                  <Clock className="h-4 w-4 text-text-muted" />
                )}
              </div>

              {/* 章节信息 */}
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium">
                  {section.title}
                </div>
                {section.title_translation && (
                  <div className="truncate text-xs text-text-muted">
                    {section.title_translation}
                  </div>
                )}
                <div className="mt-1 flex items-center gap-1.5 text-xs text-text-muted">
                  <span>{section.approved_count}/{section.total_paragraphs}</span>
                  {/* 进度条 */}
                  <div className="h-1 w-16 rounded-full bg-border">
                    <div
                      className="h-full rounded-full bg-primary-500"
                      style={{ width: `${percent}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
};
