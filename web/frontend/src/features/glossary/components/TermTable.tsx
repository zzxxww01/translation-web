import { useState } from 'react';
import { Pencil, Tag, Trash2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/Button';
import { buttonVariants } from '@/components/ui/button-variants';
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
    // 全局优先：同名时生效的是全局条目，项目那条被压掉不生效。
    shadowsProjectTerm: Boolean(effective.shadowedProjectTerm),
    shadowedProjectTranslation: effective.shadowedProjectTerm?.translation,
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
      {details.shadowsProjectTerm ? (
        <Badge variant="outline" title="项目词表里有同名条目，但全局优先，那条不生效">
          项目条目不生效
        </Badge>
      ) : null}
      {/* 启用是默认状态，不再每行都标一遍；只标出停用的 */}
      {(term.status || 'active') === 'disabled' ? <Badge variant="warning">已停用</Badge> : null}
    </div>
  );
}

/** 更新时间：今年的只写「11/22 18:30」，往年的加年份 */
function formatUpdatedAt(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  const pad = (n: number) => String(n).padStart(2, '0');
  const day = `${date.getMonth() + 1}/${date.getDate()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  return date.getFullYear() === new Date().getFullYear() ? day : `${date.getFullYear()}/${day}`;
}

/** 行内操作：两个图标按钮，删除悬停才变红，不再满屏红字按钮 */
function RowActions({ isEffectiveView, onEdit, onDelete }: {
  isEffectiveView: boolean;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <>
      <Button size="icon" variant="ghost" className="h-8 w-8" onClick={onEdit}
        title={isEffectiveView ? '编辑来源' : '编辑'} aria-label={isEffectiveView ? '编辑来源' : '编辑'}>
        <Pencil />
      </Button>
      {!isEffectiveView ? (
        <Button size="icon" variant="ghost" className="h-8 w-8 hover:bg-error-light hover:text-error" onClick={onDelete}
          title="删除" aria-label="删除">
          <Trash2 />
        </Button>
      ) : null}
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
  const [pendingDeleteOriginal, setPendingDeleteOriginal] = useState<string | null>(null);
  const isEffectiveView = activeScope === 'effective';

  if (!terms.length) {
    return (
      <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-text-muted">
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
        <label className="flex items-center gap-2 px-1 py-1 text-sm text-text-secondary">
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
                'rounded-xl border border-border-subtle bg-white p-4',
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
              {details.shadowsProjectTerm ? (
                <p className="mt-3 text-xs leading-5 text-muted-foreground">
                  项目词表里的「{details.shadowedProjectTranslation || '保留原文'}」不生效——全局优先
                </p>
              ) : null}

              <div className="mt-3 flex justify-end gap-1">
                <RowActions
                  isEffectiveView={isEffectiveView}
                  onEdit={() => onFocusTerm(term)}
                  onDelete={() => setPendingDeleteOriginal(term.original)}
                />
              </div>
            </article>
          );
        })}
      </div>

      <div className="hidden overflow-x-auto rounded-xl border border-border-subtle bg-white md:block">
        <Table>
          <TableHeader>
            <TableRow className="bg-bg-tertiary/60 hover:bg-bg-tertiary/60">
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
              <TableHead>策略</TableHead>
              <TableHead>标签</TableHead>
              <TableHead>更新</TableHead>
              <TableHead className="w-20"><span className="sr-only">操作</span></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {terms.map(term => {
              const isSelected = selectedOriginals.includes(term.original);
              const isFocused = focusedOriginal === term.original && !isCreating;
              const details = effectiveDetails(term);
              return (
                <TableRow key={term.original} className={cn('group', isFocused && 'bg-primary/5')}>
                  {!isEffectiveView ? (
                    <TableCell className="align-top">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleSelected(term.original)}
                        aria-label={`选择 ${term.original}`}
                        className="mt-[3px] block"
                      />
                    </TableCell>
                  ) : null}
                  <TableCell className="max-w-56 break-words align-top font-medium">
                    {term.original}
                  </TableCell>
                  <TableCell className="max-w-64 break-words align-top text-muted-foreground">
                    {term.translation || '保留原文'}
                    {details.shadowsProjectTerm ? (
                      <span className="mt-1 block text-xs text-muted-foreground line-through">
                        项目：{details.shadowedProjectTranslation || '保留原文'}
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
                        <span className="text-sm text-text-disabled">—</span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="whitespace-nowrap align-top text-sm text-muted-foreground">
                    {formatUpdatedAt(term.updated_at)}
                  </TableCell>
                  <TableCell className="align-top">
                    {/* 图标按钮比一行字高，往上收一点，和第一行文字居中对齐 */}
                    <div className="-my-1.5 flex items-center justify-end gap-0.5">
                      <RowActions
                        isEffectiveView={isEffectiveView}
                        onEdit={() => onFocusTerm(term)}
                        onDelete={() => setPendingDeleteOriginal(term.original)}
                      />
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
            <AlertDialogTitle>删除「{pendingDeleteOriginal}」？</AlertDialogTitle>
            <AlertDialogDescription>
              {activeScope === 'project'
                ? '删除项目术语后只会移除项目覆盖，全局术语不受影响。'
                : '删除全局术语后，所有使用全局术语的翻译功能都会受到影响。'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction className={buttonVariants({ variant: 'destructive' })} onClick={() => void handleDeleteConfirm()}>
              删除
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
      <div className="rounded-xl border border-dashed border-border p-10 text-center text-sm text-text-muted">
        当前筛选条件下没有术语。
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {groupedTerms.map(group => (
        <section key={group.tag} className="space-y-3">
          <div className="flex items-center gap-3">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-text-primary">
              <Tag className="h-3.5 w-3.5 text-text-muted" />
              {group.tag}
            </h3>
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
