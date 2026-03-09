/**
 * Document sidebar with project picker, section list, translation controls, and export actions.
 */

import { useState } from 'react';
import { BookOpen, Cpu, Download, Languages, Layers, Zap } from 'lucide-react';
import { Button, CollapsibleSection } from '../../../components/ui';
import {
  DEFAULT_MODEL,
  DEFAULT_TRANSLATION_METHOD,
  MODEL_OPTIONS,
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
  onFullTranslate?: (model?: string, method?: TranslationMethod) => void;
  onOpenGlossaryManagement?: () => void;
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
  onOpenGlossaryManagement,
  isFullTranslating,
  fullTranslateProgress,
  currentStep,
  projectId,
}: DocumentSidebarProps) {
  const [exportFormat, setExportFormat] = useState<'markdown' | 'html'>('markdown');
  const [selectedModel, setSelectedModel] = useState<string>(DEFAULT_MODEL);
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
              章节列表
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
            <p className="text-sm">选择项目查看章节</p>
          </div>
        )}
      </div>

      {totalParagraphs > 0 && (
        <div className="space-y-3 border-t border-border-subtle p-3">
          <div>
            <div className="mb-2 flex justify-between text-sm">
              <span className="font-medium text-text-secondary">翻译进度</span>
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
                  {currentStep || '正在翻译...'}
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
                onClick={() => onFullTranslate(selectedModel, selectedMethod)}
                disabled={isFullTranslating}
                leftIcon={<Zap className="h-5 w-5" />}
                className="w-full"
              >
                {isFullTranslating ? '翻译中...' : '全文一键翻译'}
              </Button>

              <CollapsibleSection title="高级选项" defaultOpen={false}>
                <div className="grid grid-cols-2 gap-2">
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

                  <div className="flex items-center gap-1.5">
                    <Cpu className="h-3.5 w-3.5 flex-shrink-0 text-text-muted" />
                    <select
                      value={selectedModel}
                      onChange={event => setSelectedModel(event.target.value)}
                      className="flex-1 rounded-md border border-border bg-bg-primary px-2 py-1.5 text-xs"
                      disabled={isFullTranslating}
                    >
                      {MODEL_OPTIONS.map(model => (
                        <option key={model.id} value={model.id}>
                          {model.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </CollapsibleSection>
            </div>
          )}

          {projectId && onOpenGlossaryManagement && (
            <Button
              variant="secondary"
              size="md"
              onClick={onOpenGlossaryManagement}
              leftIcon={<Languages className="h-4 w-4" />}
              className="w-full"
            >
              术语管理
            </Button>
          )}

          {projectId && (
            <CollapsibleSection title="导出文章" defaultOpen={false}>
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
                  {exportMutation.isPending ? '导出中...' : '导出'}
                </Button>
              </div>
            </CollapsibleSection>
          )}
        </div>
      )}
    </aside>
  );
}
