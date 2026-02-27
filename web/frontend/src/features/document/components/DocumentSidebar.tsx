/**
 * 文档翻译侧边栏组件
 * 包含项目选择、章节列表和进度显示
 */

import { useState } from 'react';
import { BookOpen, Zap, Download, Cpu, Layers } from 'lucide-react';
import { ProjectSelector } from './ProjectSelector';
import { SectionList } from './SectionList';
import { Button } from '../../../components/ui';
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
      <div className="border-b border-border-subtle p-4">
        <ProjectSelector onNewProject={onNewProject} />
      </div>

      {/* 章节列表 */}
      <div className="flex-1 overflow-y-auto p-4">
        {sections.length > 0 ? (
          <>
            <h3 className="mb-3 text-sm font-bold text-text-secondary">章节列表</h3>
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
        <div className="border-t border-border-subtle p-4 space-y-3">
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
              {/* 翻译方法选择 */}
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Layers className="h-4 w-4 text-text-muted" />
                  <select
                    value={selectedMethod}
                    onChange={(e) => setSelectedMethod(e.target.value as TranslationMethod)}
                    className="flex-1 rounded-md border border-border bg-bg-primary px-2 py-1.5 text-sm"
                    disabled={isFullTranslating}
                  >
                    {TRANSLATION_METHOD_OPTIONS.map((method) => (
                      <option key={method.id} value={method.id}>
                        {method.name}
                      </option>
                    ))}
                  </select>
                </div>
                {selectedMethodOption && (
                  <p className="text-xs text-text-muted pl-6">
                    {selectedMethodOption.description}
                  </p>
                )}
              </div>

              {/* 模型选择 */}
              <div className="flex items-center gap-2">
                <Cpu className="h-4 w-4 text-text-muted" />
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="flex-1 rounded-md border border-border bg-bg-primary px-2 py-1.5 text-sm"
                  disabled={isFullTranslating}
                >
                  {MODEL_OPTIONS.map((model) => (
                    <option key={model.id} value={model.id}>
                      {model.name}
                    </option>
                  ))}
                </select>
              </div>

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
            </div>
          )}

          {/* 导出按钮 */}
          {projectId && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <label className="text-xs text-text-muted">导出格式:</label>
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value as 'markdown' | 'html')}
                  className="flex-1 rounded-md border border-border bg-bg-primary px-3 py-1.5 text-sm"
                  disabled={exportMutation.isPending}
                >
                  <option value="markdown">Markdown (.md)</option>
                  <option value="html">HTML (.html)</option>
                </select>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleExport}
                disabled={exportMutation.isPending}
                leftIcon={<Download className="h-5 w-5" />}
                className="w-full"
              >
                {exportMutation.isPending ? '导出中...' : '导出文章'}
              </Button>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
