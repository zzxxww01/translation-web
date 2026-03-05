/**
 * 文档翻译侧边栏组件
 * 包含项目选择、章节列表和进度显示
 */

import { useState } from 'react';
import { BookOpen, Zap, Download, Cpu, Layers } from 'lucide-react';
import { ProjectSelector } from './ProjectSelector';
import { SectionList } from './SectionList';
import { Button, CollapsibleSection } from '../../../components/ui';
import { useExportProject } from '../hooks';
import {
  MODEL_OPTIONS,
  DEFAULT_MODEL,
  TRANSLATION_METHOD_OPTIONS,
  DEFAULT_TRANSLATION_METHOD,
  TranslationMethod,
} from '../../../shared/constants';
import type { Section } from '../../../shared/types';

interface DocumentSidebarProps {
  sections: Section[];
  activeSectionId: string | null;
  onSectionSelect: (sectionId: string) => void;
  onNewProject: () => void;
  onFullTranslate?: (model?: string, method?: TranslationMethod) => void;
  isFullTranslating?: boolean;
  fullTranslateProgress?: { current: number; total: number } | null;
  currentStep?: string | null;  // 四步法当前步骤
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
  const [selectedModel, setSelectedModel] = useState<string>(DEFAULT_MODEL);
  const [selectedMethod, setSelectedMethod] = useState<TranslationMethod>(DEFAULT_TRANSLATION_METHOD);
  const exportMutation = useExportProject();

  // 计算进度
  const totalParagraphs = sections.reduce((acc, s) => acc + s.total_paragraphs, 0);
  const approvedParagraphs = sections.reduce((acc, s) => acc + s.approved_count, 0);
  const progressPercent = totalParagraphs > 0 ? (approvedParagraphs / totalParagraphs) * 100 : 0;

  const handleExport = () => {
    if (!projectId) return;
    exportMutation.mutate({ projectId, format: exportFormat });
  };

  // 获取当前选中翻译方法的描述
  const selectedMethodOption = TRANSLATION_METHOD_OPTIONS.find(m => m.id === selectedMethod);

  // 计算翻译进度百分比
  const translateProgressPercent = fullTranslateProgress && fullTranslateProgress.total > 0
    ? (fullTranslateProgress.current / fullTranslateProgress.total) * 100
    : 0;

  return (
    <aside className="flex h-full w-72 flex-col border-r border-border-subtle bg-bg-secondary">
      {/* 项目选择 */}
      <div className="border-b border-border-subtle p-3">
        <ProjectSelector onNewProject={onNewProject} />
      </div>

      {/* 章节列表 */}
      <div className="flex-1 overflow-y-auto p-3">
        {sections.length > 0 ? (
          <>
            <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-text-muted">章节列表</h3>
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

      {/* 进度条和操作按钮 */}
      {totalParagraphs > 0 && (
        <div className="border-t border-border-subtle p-3 space-y-3">
          <div>
            <div className="mb-2 flex justify-between text-sm">
              <span className="text-text-secondary font-medium">翻译进度</span>
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
            <p className="mt-1 text-right text-sm text-text-muted">
              {progressPercent.toFixed(0)}%
            </p>
          </div>

          {/* 全文一键翻译进度 */}
          {isFullTranslating && fullTranslateProgress && (
            <div className="rounded-md bg-primary-500/10 p-3">
              <div className="mb-2 flex justify-between text-sm">
                <span className="text-primary-500 font-medium">
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
                <p className="mt-1 text-xs text-primary-400 truncate">
                  {translateProgressPercent.toFixed(0)}%
                </p>
              )}
            </div>
          )}

          {/* 全文一键翻译按钮 */}
          {onFullTranslate && projectId && (
            <div className="space-y-2">
              {/* 全文一键翻译按钮 - 始终可见 */}
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

              {/* 高级选项 - 可折叠 */}
              <CollapsibleSection title="高级选项" defaultOpen={false}>
                {/* 翻译方法和模型 - 合并为一行 */}
                <div className="grid grid-cols-2 gap-2">
                  <div className="flex items-center gap-1.5">
                    <Layers className="h-3.5 w-3.5 text-text-muted flex-shrink-0" />
                    <select
                      value={selectedMethod}
                      onChange={(e) => setSelectedMethod(e.target.value as TranslationMethod)}
                      className="flex-1 rounded-md border border-border bg-bg-primary px-2 py-1.5 text-xs"
                      disabled={isFullTranslating}
                      title={selectedMethodOption?.description}
                    >
                      {TRANSLATION_METHOD_OPTIONS.map((method) => (
                        <option key={method.id} value={method.id}>
                          {method.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <Cpu className="h-3.5 w-3.5 text-text-muted flex-shrink-0" />
                    <select
                      value={selectedModel}
                      onChange={(e) => setSelectedModel(e.target.value)}
                      className="flex-1 rounded-md border border-border bg-bg-primary px-2 py-1.5 text-xs"
                      disabled={isFullTranslating}
                    >
                      {MODEL_OPTIONS.map((model) => (
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

          {/* 导出按钮 */}
          {projectId && (
            <CollapsibleSection title="导出文章" defaultOpen={false}>
              <div className="flex items-center gap-2">
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value as 'markdown' | 'html')}
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
