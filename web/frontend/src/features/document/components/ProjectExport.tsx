import { useState } from 'react';
import { ChevronDown, Download } from 'lucide-react';
import { Button } from '@/components/ui/button-extended';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useExportProject } from '../hooks';

/** Mount with key={projectId}: a QA exception must never survive a project switch. */
export function ProjectExport({ projectId }: { projectId: string }) {
  const [format, setFormat] = useState<'en' | 'zh'>('zh');
  const [open, setOpen] = useState(false);
  const mutation = useExportProject();
  const qaBlocked = mutation.isError
    && mutation.error.message.includes('导出被 QA 阻断')
    && mutation.variables?.projectId === projectId
    && mutation.variables?.format === format;

  const exportOnce = (allowQaOverride = false) => {
    if (mutation.isPending) return;
    if (allowQaOverride && (!qaBlocked || !window.confirm(
      '仍然导出（忽略本次QA）？译文可能存在质量问题。此操作仅跳过本次导出的 QA 阻断，不会关闭后续 QA 检查。'
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
        {qaBlocked && (
          <div role="alert" className="mt-2 space-y-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
            <p className="break-words">{mutation.error.message}</p>
            <p>建议先查看质量报告并修复问题；忽略仅对本次导出生效。</p>
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
