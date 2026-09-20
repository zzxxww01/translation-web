import { useState } from 'react';
import { ChevronDown, Download } from 'lucide-react';
import { Button } from '@/components/ui/button-extended';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useExportProject, useProject } from '../hooks';

/** Mount with key={projectId}: a QA exception must never survive a project switch. */
export function ProjectExport({ projectId }: { projectId: string }) {
  const [format, setFormat] = useState<'en' | 'zh'>('zh');
  const [open, setOpen] = useState(false);
  const mutation = useExportProject();
  const { data: project } = useProject(projectId);
  const exportedIncomplete = mutation.isSuccess && mutation.data.is_incomplete;
  const completeness = mutation.isSuccess
    ? mutation.data.translation_completeness
    : project?.translation_completeness;
  const qaBlocked = mutation.isError
    && mutation.error.message.includes('导出被 QA 阻断')
    && mutation.variables?.projectId === projectId
    && mutation.variables?.format === format;

  const exportOnce = (allowQaOverride = false) => {
    if (mutation.isPending) return;
    if (allowQaOverride && (!qaBlocked || !window.confirm(
      `${mutation.error?.message ?? ''}\n仍然导出（忽略本次QA）？下载的可能是含英文原文的未完成稿，不代表翻译完成。仅跳过本次 QA，不会关闭后续检查。`
    ))) return;
    mutation.mutate({ projectId, format, allowQaOverride });
  };

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger asChild>
        <button type="button" className="flex w-full items-center gap-1 rounded px-2 py-1 text-xs text-text-muted hover:bg-bg-tertiary">
          <ChevronDown className={`h-3 w-3 transition-transform ${open ? 'rotate-180' : ''}`} />
          导出文章
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-1 flex items-center gap-2">
          <Select value={format} onValueChange={(value) => {
            setFormat(value as 'en' | 'zh');
            mutation.reset();
          }} disabled={mutation.isPending}>
            <SelectTrigger className="h-8 flex-1 text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="zh">中文 Markdown</SelectItem>
              <SelectItem value="en">英文 Markdown</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={() => exportOnce()}
            disabled={mutation.isPending} leftIcon={<Download className="h-4 w-4" />}>
            {mutation.isPending ? '导出中...' : '导出'}
          </Button>
        </div>
        {format === 'zh' && completeness && !completeness.is_complete && (
          <div role="status" className="mt-2 space-y-1 rounded-md border-l-2 border-amber-500 bg-amber-50 p-3 text-xs text-amber-900">
            <p className="font-semibold">{exportedIncomplete ? '已下载未完成稿' : '中文稿未完成'} · 缺译 {completeness.missing_count} 处</p>
            <p>章节标题 {completeness.missing_title_count} · 正文 {completeness.missing_body_count} · 文章标题 {completeness.missing_document_title_count}</p>
            <p>可能保留英文原文，不能作为完整译稿交付。默认导出将进行 QA 检查。</p>
            <details>
              <summary className="cursor-pointer py-1 underline underline-offset-2">查看缺译位置</summary>
              <ul className="max-h-40 space-y-1 overflow-y-auto break-words">
                {completeness.items.map((item, index) => (
                  <li key={`${item.section_id}-${item.paragraph_id}-${index}`}>
                    {item.section_title || '文章标题'}
                    {item.kind === 'section_title' ? ' / 章节标题' : ''}
                    {item.paragraph_index !== undefined ? ` / 第 ${item.paragraph_index + 1} 段` : ''}
                    ：{item.source_preview}
                  </li>
                ))}
              </ul>
            </details>
          </div>
        )}
        {qaBlocked && (
          <div role="alert" className="mt-2 space-y-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
            <p className="break-words">{mutation.error.message}</p>
            <p>建议先补全翻译并查看质量报告；下载草稿不代表翻译完成，忽略仅对本次导出生效。</p>
            <Button variant="outline" size="sm" className="w-full" disabled={mutation.isPending}
              onClick={() => exportOnce(true)}>
              仍然导出（忽略本次QA）
            </Button>
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}
