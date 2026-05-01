/**
 * Document sidebar with project picker, section list, translation controls, and export actions.
 */

import { useState } from 'react';
import { BarChart3, BookOpen, ChevronDown, Download, Layers, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button-extended';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Progress } from '@/components/ui/progress';
import {
  DEFAULT_TRANSLATION_METHOD,
  TRANSLATION_METHOD_OPTIONS,
  TranslationMethod,
} from '@/shared/constants';
import type { Section } from '@/shared/types';
import { useExportProject } from '../hooks';
import { ProjectSelector } from './ProjectSelector';
import { SectionList } from './SectionList';
import { ModelSelector } from '@/components/ModelSelector';
import { cn } from '@/lib/utils';

interface DocumentSidebarProps {
  sections: Section[];
  activeSectionId: string | null;
  onSectionSelect: (sectionId: string) => void;
  onNewProject: () => void;
  onFullTranslate?: (method?: TranslationMethod, model?: string) => void;
  onStopTranslate?: () => void;
  isFullTranslating?: boolean;
  isCancelling?: boolean;
  isPreparingFullTranslate?: boolean;
  fullTranslateProgress?: { current: number; total: number } | null;
  currentStep?: string | null;
  activeTranslationProjectId?: string | null;
  projectId?: string;
  className?: string;
}

export function DocumentSidebar({
  sections,
  activeSectionId,
  onSectionSelect,
  onNewProject,
  onFullTranslate,
  onStopTranslate,
  isFullTranslating,
  isCancelling,
  isPreparingFullTranslate,
  fullTranslateProgress,
  currentStep,
  activeTranslationProjectId,
  projectId,
  className,
}: DocumentSidebarProps) {
  const [exportFormat, setExportFormat] = useState<'en' | 'zh'>('zh');
  const [selectedMethod, setSelectedMethod] = useState<TranslationMethod>(
    DEFAULT_TRANSLATION_METHOD
  );
  const [selectedModel, setSelectedModel] = useState<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const exportMutation = useExportProject();

  const totalParagraphs = sections.reduce((acc, section) => acc + section.total_paragraphs, 0);
  const approvedParagraphs = sections.reduce((acc, section) => acc + section.approved_count, 0);
  const progressPercent = totalParagraphs > 0 ? (approvedParagraphs / totalParagraphs) * 100 : 0;

  const translateProgressPercent =
    fullTranslateProgress && fullTranslateProgress.total > 0
      ? (fullTranslateProgress.current / fullTranslateProgress.total) * 100
      : 0;

  const handleExport = () => {
    if (!projectId) return;
    exportMutation.mutate({ projectId, format: exportFormat });
  };

  const isTranslateBusy = Boolean(isFullTranslating || isPreparingFullTranslate || isCancelling);
  const isOtherProjectTranslating =
    Boolean(activeTranslationProjectId && projectId && activeTranslationProjectId !== projectId);

  return (
    <aside className={cn('flex h-full min-h-0 w-72 flex-col border-r border-border-subtle bg-bg-secondary', className)}>
      <div className="shrink-0 border-b border-border-subtle p-3">
        <ProjectSelector onNewProject={onNewProject} />
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
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
        <div className="shrink-0 space-y-3 overflow-y-auto border-t border-border-subtle bg-bg-secondary p-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] shadow-[0_-12px_24px_-22px_rgba(15,23,42,0.45)] max-h-[48vh]">
          <div>
            <div className="mb-2 flex justify-between text-sm">
              <span className="font-medium text-text-secondary">翻译进度</span>
              <span className="font-medium">
                {approvedParagraphs}/{totalParagraphs}
              </span>
            </div>
            <Progress value={progressPercent} className="h-2" />
            <p className="mt-1 text-right text-sm text-text-muted">{progressPercent.toFixed(0)}%</p>
          </div>

          {(isFullTranslating || isCancelling) && fullTranslateProgress && (
            <div className="rounded-md bg-primary-500/10 p-3">
              <div className="mb-2 flex items-start justify-between gap-3 text-sm">
                <div className="min-w-0">
                  <span className="font-medium text-primary-500">
                    {isCancelling ? '正在取消...' : currentStep || '正在翻译...'}
                  </span>
                  {currentStep && (
                    <p className="mt-1 truncate text-xs text-primary-400">
                      {translateProgressPercent.toFixed(0)}%
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-primary-500">
                    {fullTranslateProgress.current}/{fullTranslateProgress.total}
                  </span>
                </div>
              </div>
              <Progress value={translateProgressPercent} className="h-1.5" />
            </div>
          )}

          {isOtherProjectTranslating && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
              另一个项目正在翻译中：
              <span className="mx-1 font-medium">{activeTranslationProjectId}</span>
              现在启动当前项目会先停止它，再等待切换。
            </div>
          )}

          {onFullTranslate && projectId && (
            <div className="space-y-2">
              {isFullTranslating ? (
                <Button
                  variant="outline"
                  size="default"
                  onClick={onStopTranslate}
                  leftIcon={<Zap className="h-5 w-5" />}
                  className="w-full"
                >
                  停止全文翻译
                </Button>
              ) : (
                <Button
                  variant="default"
                  size="default"
                  onClick={() => onFullTranslate(selectedMethod, selectedModel || undefined)}
                  disabled={isTranslateBusy}
                  leftIcon={<Zap className="h-5 w-5" />}
                  className="w-full"
                >
                  {isCancelling ? '等待释放中...' : isPreparingFullTranslate ? '术语预检中...' : '全文一键翻译'}
                </Button>
              )}

              <Collapsible open={advancedOpen} onOpenChange={setAdvancedOpen}>
                <CollapsibleTrigger asChild>
                  <button className="flex w-full items-center gap-1 rounded px-2 py-1 text-xs text-text-muted hover:bg-bg-tertiary">
                    <ChevronDown className={`h-3 w-3 transition-transform ${advancedOpen ? 'rotate-180' : ''}`} />
                    高级选项
                  </button>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="space-y-3 mt-2 px-1">
                    <div>
                      <label className="text-xs text-text-muted mb-1.5 block">翻译方法</label>
                      <div className="flex items-center gap-1.5">
                        <Layers className="h-3.5 w-3.5 flex-shrink-0 text-text-muted" />
                        <Select
                          value={selectedMethod}
                          onValueChange={(value) => setSelectedMethod(value as TranslationMethod)}
                          disabled={isTranslateBusy}
                        >
                          <SelectTrigger className="h-8 flex-1 text-xs">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {TRANSLATION_METHOD_OPTIONS.map(method => (
                              <SelectItem key={method.id} value={method.id}>
                                {method.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-text-muted mb-1.5 block">选择模型</label>
                      <ModelSelector
                        value={selectedModel || undefined}
                        onChange={(model) => setSelectedModel(model || null)}
                        className="h-8 text-xs"
                        disabled={isTranslateBusy}
                      />
                    </div>
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </div>
          )}

          {projectId && (
            <Button
              variant="outline"
              size="default"
              leftIcon={<BarChart3 className="h-4 w-4" />}
              className="w-full"
              onClick={() => {
                window.location.href = `/document/${projectId}/quality-report`;
              }}
            >
              查看质量报告
            </Button>
          )}

          {projectId && (
            <Collapsible open={exportOpen} onOpenChange={setExportOpen}>
              <CollapsibleTrigger asChild>
                <button className="flex w-full items-center gap-1 rounded px-2 py-1 text-xs text-text-muted hover:bg-bg-tertiary">
                  <ChevronDown className={`h-3 w-3 transition-transform ${exportOpen ? 'rotate-180' : ''}`} />
                  导出文章
                </button>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <div className="mt-1 flex items-center gap-2">
                  <Select
                    value={exportFormat}
                    onValueChange={(value) => setExportFormat(value as 'en' | 'zh')}
                    disabled={exportMutation.isPending}
                  >
                    <SelectTrigger className="h-8 flex-1 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="zh">中文 Markdown</SelectItem>
                      <SelectItem value="en">英文 Markdown</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleExport}
                    disabled={exportMutation.isPending}
                    leftIcon={<Download className="h-4 w-4" />}
                  >
                    {exportMutation.isPending ? '导出中...' : '导出'}
                  </Button>
                </div>
              </CollapsibleContent>
            </Collapsible>
          )}
        </div>
      )}
    </aside>
  );
}
