import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { ButtonExtended as Button } from '@/components/ui/button-extended';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '@/components/ui/table';
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
import { Tag } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { GlossaryTerm } from '@/features/confirmation/types';
import { strategyLabels, type GlossaryScope } from '../types';

interface TermTableProps {
  terms: GlossaryTerm[];
  tableKey: string;
  selectedOriginals: string[];
  focusedOriginal: string | null;
  isCreating: boolean;
  activeScope: GlossaryScope;
  onToggleSelected: (original: string) => void;
  onToggleAllVisible: (terms: GlossaryTerm[]) => void;
  onFocusTerm: (term: GlossaryTerm) => void;
  onDeleteTerm: (original: string) => Promise<void>;
}

interface GroupedTermTableProps extends TermTableProps {
  groupedTerms: Array<{ tag: string; terms: GlossaryTerm[] }>;
}

function TermRows({
  terms,
  selectedOriginals,
  focusedOriginal,
  isCreating,
  activeScope,
  onToggleSelected,
  onFocusTerm,
  onDeleteTerm,
}: Omit<TermTableProps, 'tableKey' | 'onToggleAllVisible'>) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [pendingDeleteOriginal, setPendingDeleteOriginal] = useState<string | null>(null);

  function handleDeleteClick(original: string) {
    setPendingDeleteOriginal(original);
    setDeleteDialogOpen(true);
  }

  async function handleDeleteConfirm() {
    if (pendingDeleteOriginal) {
      await onDeleteTerm(pendingDeleteOriginal);
    }
    setDeleteDialogOpen(false);
    setPendingDeleteOriginal(null);
  }

  return (
    <>
      {terms.map(term => {
        const isSelected = selectedOriginals.includes(term.original);
        const isFocused = focusedOriginal === term.original && !isCreating;
        return (
          <TableRow
            key={term.original}
            className={cn(
              'cursor-pointer border-b border-gray-100 transition-colors last:border-0',
              'hover:bg-primary/5',
              isFocused ? 'bg-primary/5' : ''
            )}
          >
            <TableCell className="align-top">
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => onToggleSelected(term.original)}
                aria-label={`选择 ${term.original}`}
              />
            </TableCell>
            <TableCell className="align-top">
              <button
                type="button"
                className="text-left font-medium text-foreground hover:text-primary"
                onClick={() => onFocusTerm(term)}
              >
                {term.original}
              </button>
            </TableCell>
            <TableCell className="align-top text-muted-foreground">{term.translation || '-'}</TableCell>
            <TableCell className="align-top">
              <Badge variant="outline">{strategyLabels[term.strategy]}</Badge>
            </TableCell>
            <TableCell className="align-top">
              <div className="flex flex-wrap gap-1">
                {(term.tags || []).length ? (
                  (term.tags || []).map(tag => (
                    <Badge key={`${term.original}-${tag}`} variant="secondary">
                      {tag}
                    </Badge>
                  ))
                ) : (
                  <span className="text-sm text-muted-foreground">未分类</span>
                )}
              </div>
            </TableCell>
            <TableCell className="align-top">
              <Badge variant={(term.status || 'active') === 'disabled' ? 'secondary' : 'default'}>
                {term.status || 'active'}
              </Badge>
            </TableCell>
            <TableCell className="align-top text-sm text-muted-foreground">
              {term.updated_at ? new Date(term.updated_at).toLocaleString() : '-'}
            </TableCell>
            <TableCell className="align-top">
              <div className="flex items-center gap-2">
                <Button size="sm" variant="outline" onClick={() => onFocusTerm(term)}>
                  编辑
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={() => handleDeleteClick(term.original)}
                >
                  删除
                </Button>
              </div>
            </TableCell>
          </TableRow>
        );
      })}

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              {activeScope === 'project'
                ? '删除项目术语后，只会移除项目覆盖，不会影响全局术语。确认继续？'
                : '删除全局术语后，所有依赖全局术语的功能都会受影响。确认继续？'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => void handleDeleteConfirm()}>确认删除</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

export function TermTable({
  terms,
  tableKey,
  selectedOriginals,
  focusedOriginal,
  isCreating,
  activeScope,
  onToggleSelected,
  onToggleAllVisible,
  onFocusTerm,
  onDeleteTerm,
}: TermTableProps) {
  if (!terms.length) {
    return (
      <div className="rounded-2xl border border-dashed border-border p-10 text-center text-muted-foreground">
        当前筛选条件下没有术语。
      </div>
    );
  }

  const visibleOriginals = terms.map(term => term.original);
  const allSelected =
    visibleOriginals.length > 0 && visibleOriginals.every(original => selectedOriginals.includes(original));

  return (
    <div key={tableKey} className="overflow-x-auto rounded-lg border border-border bg-white shadow-sm">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50">
            <TableHead>
              <input
                type="checkbox"
                checked={allSelected}
                onChange={() => onToggleAllVisible(terms)}
                aria-label="选择当前列表全部术语"
              />
            </TableHead>
            <TableHead>原文</TableHead>
            <TableHead>译法</TableHead>
            <TableHead>策略</TableHead>
            <TableHead>标签</TableHead>
            <TableHead>状态</TableHead>
            <TableHead>更新时间</TableHead>
            <TableHead>操作</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TermRows
            terms={terms}
            selectedOriginals={selectedOriginals}
            focusedOriginal={focusedOriginal}
            isCreating={isCreating}
            activeScope={activeScope}
            onToggleSelected={onToggleSelected}
            onFocusTerm={onFocusTerm}
            onDeleteTerm={onDeleteTerm}
          />
        </TableBody>
      </Table>
    </div>
  );
}

export function GroupedTermView({
  groupedTerms,
  selectedOriginals,
  focusedOriginal,
  isCreating,
  activeScope,
  onToggleSelected,
  onToggleAllVisible,
  onFocusTerm,
  onDeleteTerm,
}: Omit<GroupedTermTableProps, 'terms' | 'tableKey'>) {
  if (!groupedTerms.length) {
    return (
      <div className="rounded-2xl border border-dashed border-border p-10 text-center text-muted-foreground">
        当前筛选条件下没有术语。
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {groupedTerms.map(group => (
        <section key={group.tag} className="space-y-3">
          <div className="flex items-center gap-3">
            <Badge variant="secondary" className="px-3 py-1 text-sm">
              <Tag className="mr-1 h-3.5 w-3.5" />
              {group.tag}
            </Badge>
            <span className="text-sm text-muted-foreground">{group.terms.length} 条</span>
          </div>
          <TermTable
            terms={group.terms}
            tableKey={`group-${group.tag}`}
            selectedOriginals={selectedOriginals}
            focusedOriginal={focusedOriginal}
            isCreating={isCreating}
            activeScope={activeScope}
            onToggleSelected={onToggleSelected}
            onToggleAllVisible={onToggleAllVisible}
            onFocusTerm={onFocusTerm}
            onDeleteTerm={onDeleteTerm}
          />
        </section>
      ))}
    </div>
  );
}
