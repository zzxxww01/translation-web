import { useState } from 'react';
import { ButtonExtended as Button } from '@/components/ui/button-extended';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import type { TranslationStrategy } from '@/features/confirmation/types';
import type { BatchGlossaryRequest } from '@/features/confirmation/api/glossaryApi';
import { normalizeTags, type GlossaryScope } from '../types';

interface BatchActionsBarProps {
  activeScope: GlossaryScope;
  selectedOriginals: string[];
  onClearSelection: () => void;
  onRunBatch: (action: BatchGlossaryRequest['action'], overrides?: Partial<BatchGlossaryRequest>) => Promise<void>;
}

export function BatchActionsBar({
  activeScope,
  selectedOriginals,
  onClearSelection,
  onRunBatch,
}: BatchActionsBarProps) {
  const [batchTagInput, setBatchTagInput] = useState('');
  const [batchStrategy, setBatchStrategy] = useState<TranslationStrategy>('translate');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  if (activeScope === 'recommendations' || !selectedOriginals.length) {
    return null;
  }

  function handleTagAction(action: 'add_tags' | 'replace_tags' | 'remove_tags') {
    const tags = normalizeTags(batchTagInput);
    if (!tags.length) {
      toast.warning('请输入至少一个标签');
      return;
    }
    setBatchTagInput('');
    void onRunBatch(action, { tags });
  }

  return (
    <>
      <div className="flex flex-col gap-3 rounded-2xl border border-border bg-white p-4 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="text-sm text-muted-foreground">已选择 {selectedOriginals.length} 条术语</div>
          <Button size="sm" variant="outline" onClick={onClearSelection}>
            清空选择
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => void onRunBatch('set_status', { status: 'active' })}>
            批量启用
          </Button>
          <Button size="sm" variant="outline" onClick={() => void onRunBatch('set_status', { status: 'disabled' })}>
            批量停用
          </Button>
          <Select
            value={batchStrategy}
            onValueChange={(value: string) => setBatchStrategy(value as TranslationStrategy)}
          >
            <SelectTrigger className="w-[120px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="translate">翻译</SelectItem>
              <SelectItem value="first_annotate">首次标注</SelectItem>
              <SelectItem value="preserve">保留原文</SelectItem>
              <SelectItem value="preserve_annotate">保留原文+首次注释</SelectItem>
            </SelectContent>
          </Select>
          <Button
            size="sm"
            variant="outline"
            onClick={() => void onRunBatch('set_strategy', { strategy: batchStrategy })}
          >
            批量改策略
          </Button>
          <Input
            value={batchTagInput}
            onChange={event => setBatchTagInput(event.target.value)}
            placeholder="标签，逗号分隔"
            className="min-w-[220px]"
          />
          <Button size="sm" variant="outline" onClick={() => handleTagAction('add_tags')}>
            批量加标签
          </Button>
          <Button size="sm" variant="outline" onClick={() => handleTagAction('replace_tags')}>
            替换标签
          </Button>
          <Button size="sm" variant="outline" onClick={() => handleTagAction('remove_tags')}>
            移除标签
          </Button>
          <Button
            size="sm"
            variant="destructive"
            leftIcon={<Trash2 className="h-4 w-4" />}
            onClick={() => setDeleteDialogOpen(true)}
          >
            批量删除
          </Button>
        </div>
      </div>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认批量删除</AlertDialogTitle>
            <AlertDialogDescription>
              {activeScope === 'project'
                ? '批量删除项目术语后，只会移除项目覆盖。确认继续？'
                : '批量删除全局术语后，所有依赖全局术语的功能都会受影响。确认继续？'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setDeleteDialogOpen(false);
                void onRunBatch('delete');
              }}
            >
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
