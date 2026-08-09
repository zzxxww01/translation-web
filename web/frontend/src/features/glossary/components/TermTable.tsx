import { useState } from 'react';
import { Pencil, Tag, Trash2 } from 'lucide-react';
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
import { cn } from '@/lib/utils';
import type { GlossaryTerm } from '@/features/confirmation/types';
import type { EffectiveGlossaryTerm } from '../model';
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

function effectiveDetails(term: GlossaryTerm) {
  const effective = term as Partial<EffectiveGlossaryTerm>;
  return {
    source:
      effective.effectiveScope === 'project' || term.scope === 'project'
        ? '项目'
        : '全局',
    overridesGlobal: Boolean(effective.overridesGlobal),
    globalTranslation: effective.globalTerm?.translation,
  };
}

function TermBadges({ term, showSource }: { term: GlossaryTerm; showSource: boolean }) {
  const details = effectiveDetails(term);
  return (
    <div className="flex flex-wrap gap-1.5">
      <Badge variant="outline">{strategyLabels[term.strategy]}</Badge>
      {showSource ? (
        <Badge variant={details.source === '项目' ? 'default' : 'secondary'}>
          {details.source}生效
        </Badge>
      ) : null}
      {details.overridesGlobal ? <Badge variant="outline">覆盖全局</Badge> : null}
      <Badge variant={(term.status || 'active') === 'disabled' ? 'secondary' : 'default'}>
        {(term.status || 'active') === 'disabled' ? '停用' : '启用'}
      </Badge>
    </div>
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
  const [pendingDeleteOriginal, setPendingDeleteOriginal] = useState<string | null>(null);
  const isEffectiveView = activeScope === 'effective';

  if (!terms.length) {
    return (
      <div className="rounded-md border border-dashed border-border p-10 text-center text-muted-foreground">
        当前筛选条件下没有术语。
      </div>
    );
  }

  const visibleOriginals = terms.map(term => term.original);
  const allSelected =
    visibleOriginals.length > 0 &&
    visibleOriginals.every(original => selectedOriginals.includes(original));

  async function handleDeleteConfirm() {
    if (!pendingDeleteOriginal) return;
    await onDeleteTerm(pendingDeleteOriginal);
    setPendingDeleteOriginal(null);
  }

  return (
    <div key={tableKey}>
      <div className="space-y-2 md:hidden">
        <label className="flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm">
          <input
            type="checkbox"
            checked={allSelected}
            onChange={() => onToggleAllVisible(terms)}
            disabled={isEffectiveView}
          />
          选择当前显示的全部术语
        </label>
        {terms.map(term => {
          const isSelected = selectedOriginals.includes(term.original);
          const isFocused = focusedOriginal === term.original && !isCreating;
          const details = effectiveDetails(term);
          return (
            <article
              key={term.original}
              className={cn(
                'rounded-md border bg-background p-4',
                isFocused && 'border-primary ring-1 ring-primary/30'
              )}
            >
              <div className="flex items-start gap-3">
                {!isEffectiveView ? (
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => onToggleSelected(term.original)}
                    aria-label={`选择 ${term.original}`}
                    className="mt-1"
                  />
                ) : null}
                <div className="min-w-0 flex-1">
                  <h3 className="break-words font-semibold">{term.original}</h3>
                  <p className="mt-1 break-words text-sm text-muted-foreground">
                    {term.translation || '保留原文'}
                  </p>
                </div>
              </div>

              <div className="mt-3">
                <TermBadges term={term} showSource={isEffectiveView} />
              </div>
              {(term.tags || []).length ? (
                <div className="mt-3 flex flex-wrap gap-1">
                  {(term.tags || []).map(tag => (
                    <Badge key={`${term.original}-${tag}`} variant="secondary">{tag}</Badge>
                  ))}
                </div>
              ) : null}
              {details.overridesGlobal ? (
                <p className="mt-3 text-xs leading-5 text-muted-foreground">
                  全局译法：{details.globalTranslation || '保留原文'}
                </p>
              ) : null}

              <div className="mt-4 flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  leftIcon={<Pencil className="h-4 w-4" />}
                  onClick={() => onFocusTerm(term)}
                >
                  {isEffectiveView ? '编辑来源' : '编辑'}
                </Button>
                {!isEffectiveView ? (
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-destructive hover:text-destructive"
                    leftIcon={<Trash2 className="h-4 w-4" />}
                    onClick={() => setPendingDeleteOriginal(term.original)}
                  >
                    删除
                  </Button>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>

      <div className="hidden overflow-x-auto rounded-md border border-border bg-background md:block">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              {!isEffectiveView ? (
                <TableHead>
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={() => onToggleAllVisible(terms)}
                    aria-label="选择当前列表全部术语"
                  />
                </TableHead>
              ) : null}
              <TableHead>原文</TableHead>
              <TableHead>译法</TableHead>
              <TableHead>策略与来源</TableHead>
              <TableHead>标签</TableHead>
              <TableHead>更新时间</TableHead>
              <TableHead>操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {terms.map(term => {
              const isSelected = selectedOriginals.includes(term.original);
              const isFocused = focusedOriginal === term.original && !isCreating;
              const details = effectiveDetails(term);
              return (
                <TableRow key={term.original} className={cn(isFocused && 'bg-primary/5')}>
                  {!isEffectiveView ? (
                    <TableCell className="align-top">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleSelected(term.original)}
                        aria-label={`选择 ${term.original}`}
                      />
                    </TableCell>
                  ) : null}
                  <TableCell className="max-w-56 break-words align-top font-medium">
                    {term.original}
                  </TableCell>
                  <TableCell className="max-w-64 break-words align-top text-muted-foreground">
                    {term.translation || '保留原文'}
                    {details.overridesGlobal ? (
                      <span className="mt-1 block text-xs">
                        全局：{details.globalTranslation || '保留原文'}
                      </span>
                    ) : null}
                  </TableCell>
                  <TableCell className="align-top">
                    <TermBadges term={term} showSource={isEffectiveView} />
                  </TableCell>
                  <TableCell className="max-w-48 align-top">
                    <div className="flex flex-wrap gap-1">
                      {(term.tags || []).length ? (
                        (term.tags || []).map(tag => (
                          <Badge key={`${term.original}-${tag}`} variant="secondary">{tag}</Badge>
                        ))
                      ) : (
                        <span className="text-sm text-muted-foreground">未分类</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap align-top text-sm text-muted-foreground">
                    {term.updated_at ? new Date(term.updated_at).toLocaleString() : '-'}
                  </TableCell>
                  <TableCell className="align-top">
                    <div className="flex items-center gap-2">
                      <Button size="sm" variant="outline" onClick={() => onFocusTerm(term)}>
                        {isEffectiveView ? '编辑来源' : '编辑'}
                      </Button>
                      {!isEffectiveView ? (
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-destructive hover:text-destructive"
                          onClick={() => setPendingDeleteOriginal(term.original)}
                        >
                          删除
                        </Button>
                      ) : null}
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <AlertDialog
        open={pendingDeleteOriginal !== null}
        onOpenChange={open => {
          if (!open) setPendingDeleteOriginal(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除</AlertDialogTitle>
            <AlertDialogDescription>
              {activeScope === 'project'
                ? '删除项目术语后只会移除项目覆盖，全局术语不受影响。'
                : '删除全局术语后，所有使用全局术语的翻译功能都会受到影响。'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => void handleDeleteConfirm()}>
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
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
      <div className="rounded-md border border-dashed border-border p-10 text-center text-muted-foreground">
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
