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
              'w-full rounded-lg p-3.5 text-left transition-colors',
              isActive
                ? 'bg-primary-50 text-primary-700'
                : 'hover:bg-bg-tertiary'
            )}
          >
            <div className="flex items-start gap-2">
              {/* 状态图标 */}
              <div className="mt-0.5 flex-shrink-0">
                {section.is_complete ? (
                  <CheckCircle className="h-5 w-5 text-success" />
                ) : (
                  <Clock className="h-5 w-5 text-text-muted" />
                )}
              </div>

              {/* 章节信息 */}
              <div className="min-w-0 flex-1">
                <div className="truncate text-base font-medium">
                  {section.title}
                </div>
                {section.title_translation && (
                  <div className="truncate text-sm text-text-muted">
                    {section.title_translation}
                  </div>
                )}
                <div className="mt-1.5 flex items-center gap-2 text-sm text-text-muted">
                  <span>{section.approved_count}/{section.total_paragraphs} 已确认</span>
                  {/* 进度条 */}
                  <div className="h-1.5 w-20 flex-1 rounded-full bg-border">
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
