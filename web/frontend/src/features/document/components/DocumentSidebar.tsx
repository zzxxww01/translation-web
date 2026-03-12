/**
 * Document sidebar with project picker, section list, translation controls, and export actions.
 */

import { useState } from 'react';
import { BookOpen, Download, Layers, Zap } from 'lucide-react';
import { Button, CollapsibleSection } from '../../../components/ui';
import {
  DEFAULT_TRANSLATION_METHOD,
  TRANSLATION_METHOD_OPTIONS,
  TranslationMethod,
} from '../../../shared/constants';
import type { Section } from '../../../shared/types';
import { useExportProject } from '../hooks';
import { ProjectSelector } from './ProjectSelector';
import { SectionList } from './SectionList';

interface DocumentSidebarProps {
  sections: Section[];
  activeSectionId: string | null;
  onSectionSelect: (sectionId: string) => void;
  onNewProject: () => void;
  onFullTranslate?: (method?: TranslationMethod) => void;
  isFullTranslating?: boolean;
  fullTranslateProgress?: { current: number; total: number } | null;
  currentStep?: string | null;
  projectId?: string;
}

export function DocumentSidebar({
  sections,
  activeSectionId,
  onSectionSelect,
  onNewProject,
  onFullTranslate,
  isFullTranslating,
  fullTranslateProgress,
  currentStep,
  projectId,
}: DocumentSidebarProps) {
  const [exportFormat, setExportFormat] = useState<'markdown' | 'html'>('markdown');
  const [selectedMethod, setSelectedMethod] = useState<TranslationMethod>(
    DEFAULT_TRANSLATION_METHOD
  );
  const exportMutation = useExportProject();

  const totalParagraphs = sections.reduce((acc, section) => acc + section.total_paragraphs, 0);
  const approvedParagraphs = sections.reduce((acc, section) => acc + section.approved_count, 0);
  const progressPercent = totalParagraphs > 0 ? (approvedParagraphs / totalParagraphs) * 100 : 0;

  const selectedMethodOption = TRANSLATION_METHOD_OPTIONS.find(
    method => method.id === selectedMethod
  );

  const translateProgressPercent =
    fullTranslateProgress && fullTranslateProgress.total > 0
      ? (fullTranslateProgress.current / fullTranslateProgress.total) * 100
      : 0;

  const handleExport = () => {
    if (!projectId) return;
    exportMutation.mutate({ projectId, format: exportFormat });
  };

  return (
    <aside className="flex h-full w-72 flex-col border-r border-border-subtle bg-bg-secondary">
      <div className="border-b border-border-subtle p-3">
        <ProjectSelector onNewProject={onNewProject} />
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {sections.length > 0 ? (
          <>
            <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-text-muted">
              {'\u7AE0\u8282\u5217\u8868'}
            </h3>
            <SectionList
              sections={sections}
              activeSectionId={activeSectionId || undefined}
              onSelectSection={onSectionSelect}
            />
          </>
        ) : (
          <div className="flex flex-col items-center py-8 text-center text-text-muted">
            <BookOpen className="mb-2 h-10 w-10 opacity-50" />
            <p className="text-sm">{'\u9009\u62E9\u9879\u76EE\u67E5\u770B\u7AE0\u8282'}</p>
          </div>
        )}
      </div>

      {totalParagraphs > 0 && (
        <div className="space-y-3 border-t border-border-subtle p-3">
          <div>
            <div className="mb-2 flex justify-between text-sm">
              <span className="font-medium text-text-secondary">{'\u7FFB\u8BD1\u8FDB\u5EA6'}</span>
              <span className="font-medium">
                {approvedParagraphs}/{totalParagraphs}
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-bg-tertiary">
              <div
                className="h-full rounded-full bg-primary-500 transition-all"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <p className="mt-1 text-right text-sm text-text-muted">{progressPercent.toFixed(0)}%</p>
          </div>

          {isFullTranslating && fullTranslateProgress && (
            <div className="rounded-md bg-primary-500/10 p-3">
              <div className="mb-2 flex justify-between text-sm">
                <span className="font-medium text-primary-500">
                  {currentStep || '\u6B63\u5728\u7FFB\u8BD1...'}
                </span>
                <span className="text-primary-500">
                  {fullTranslateProgress.current}/{fullTranslateProgress.total}
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-bg-tertiary">
                <div
                  className="h-full rounded-full bg-primary-500 transition-all"
                  style={{ width: `${translateProgressPercent}%` }}
                />
              </div>
              {currentStep && (
                <p className="mt-1 truncate text-xs text-primary-400">
                  {translateProgressPercent.toFixed(0)}%
                </p>
              )}
            </div>
          )}

          {onFullTranslate && projectId && (
            <div className="space-y-2">
              <Button
                variant="primary"
                size="md"
                onClick={() => onFullTranslate(selectedMethod)}
                disabled={isFullTranslating}
                leftIcon={<Zap className="h-5 w-5" />}
                className="w-full"
              >
                {isFullTranslating
                  ? '\u7FFB\u8BD1\u4E2D...'
                  : '\u5168\u6587\u4E00\u952E\u7FFB\u8BD1'}
              </Button>

              <CollapsibleSection title={'\u9AD8\u7EA7\u9009\u9879'} defaultOpen={false}>
                <div className="flex items-center gap-1.5">
                  <Layers className="h-3.5 w-3.5 flex-shrink-0 text-text-muted" />
                  <select
                    value={selectedMethod}
                    onChange={event =>
                      setSelectedMethod(event.target.value as TranslationMethod)
                    }
                    className="flex-1 rounded-md border border-border bg-bg-primary px-2 py-1.5 text-xs"
                    disabled={isFullTranslating}
                    title={selectedMethodOption?.description}
                  >
                    {TRANSLATION_METHOD_OPTIONS.map(method => (
                      <option key={method.id} value={method.id}>
                        {method.name}
                      </option>
                    ))}
                  </select>
                </div>
              </CollapsibleSection>
            </div>
          )}

          {projectId && (
            <CollapsibleSection title={'\u5BFC\u51FA\u6587\u7AE0'} defaultOpen={false}>
              <div className="flex items-center gap-2">
                <select
                  value={exportFormat}
                  onChange={event =>
                    setExportFormat(event.target.value as 'markdown' | 'html')
                  }
                  className="flex-1 rounded-md border border-border bg-bg-primary px-2 py-1.5 text-xs"
                  disabled={exportMutation.isPending}
                >
                  <option value="markdown">Markdown</option>
                  <option value="html">HTML</option>
                </select>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleExport}
                  disabled={exportMutation.isPending}
                  leftIcon={<Download className="h-4 w-4" />}
                >
                  {exportMutation.isPending ? '\u5BFC\u51FA\u4E2D...' : '\u5BFC\u51FA'}
                </Button>
              </div>
            </CollapsibleSection>
          )}
        </div>
      )}
    </aside>
  );
}
