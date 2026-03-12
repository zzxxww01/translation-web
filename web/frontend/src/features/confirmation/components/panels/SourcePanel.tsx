import { cn } from '../../../../shared/utils';
import type { Paragraph } from '../../types';

interface SourcePanelProps {
  paragraph: Paragraph | null;
  projectId?: string;
  className?: string;
}

export function SourcePanel({
  paragraph,
  projectId: _projectId = '',
  className,
}: SourcePanelProps) {
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
    <div
      className={cn(
        'relative w-[30%] overflow-y-auto border-r border-border bg-muted/30 p-6',
        className
      )}
    >
      <div className="mb-4">
        <div className="text-xs font-medium uppercase tracking-wide text-text-secondary">
          章节
        </div>
        <div className="mt-1 text-sm font-semibold text-text-primary">
          {paragraph.section_title}
        </div>
      </div>

      <div className="mb-4">
        <div className="text-xs font-medium uppercase tracking-wide text-text-secondary">
          段落
        </div>
        <div className="mt-1 text-sm font-semibold text-text-primary">
          #{paragraph.index + 1}
        </div>
      </div>

      <div className="prose prose-sm max-w-none">
        <div className="mb-2 text-xs font-medium uppercase tracking-wide text-text-secondary">
          原文
        </div>
        <div className="whitespace-pre-wrap leading-relaxed text-text-primary">
          {paragraph.source}
        </div>
      </div>

      <div className="mt-6 border-t border-border pt-4">
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
    </div>
  );
}
