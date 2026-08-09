import { useState } from 'react';
import { Loader2, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/textarea';
import type { TranslationRule } from '../api';

interface TranslationRulesPanelProps {
  rules: TranslationRule[];
  isLoading: boolean;
  isAdding: boolean;
  deletingIndex: number | null;
  error: unknown;
  onRetry: () => void;
  onAdd: (text: string) => Promise<boolean>;
  onDelete: (index: number) => Promise<void>;
}

export function TranslationRulesPanel({
  rules,
  isLoading,
  isAdding,
  deletingIndex,
  error,
  onRetry,
  onAdd,
  onDelete,
}: TranslationRulesPanelProps) {
  const [draft, setDraft] = useState('');

  async function handleAdd() {
    if (!draft.trim()) return;
    if (await onAdd(draft.trim())) setDraft('');
  }

  if (isLoading) {
    return (
      <div className="flex min-h-48 items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        正在加载翻译规则
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-destructive/30 bg-destructive/5 p-5">
        <p className="text-sm text-destructive">翻译规则加载失败，术语列表仍可正常使用。</p>
        <Button type="button" variant="outline" size="sm" className="mt-3" onClick={onRetry}>
          <RefreshCw className="h-4 w-4" />
          重试
        </Button>
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,420px)_minmax(0,1fr)]">
      <section className="space-y-3 lg:sticky lg:top-4 lg:self-start" aria-labelledby="new-rule-heading">
        <div>
          <h2 id="new-rule-heading" className="font-semibold">添加翻译规则</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            规则会应用到所有翻译工作流。每条规则只表达一个明确约束。
          </p>
        </div>
        <Textarea
          value={draft}
          onChange={event => setDraft(event.target.value)}
          placeholder="例如：产品名 token 始终保留英文，不翻译为“词元”。"
          rows={5}
          aria-label="新翻译规则"
        />
        <Button
          type="button"
          onClick={() => void handleAdd()}
          disabled={!draft.trim() || isAdding}
          className="w-full sm:w-auto"
        >
          {isAdding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          添加规则
        </Button>
      </section>

      <section aria-labelledby="rule-list-heading">
        <div className="mb-3 flex items-center justify-between">
          <h2 id="rule-list-heading" className="font-semibold">当前规则</h2>
          <span className="text-sm text-muted-foreground">{rules.length} 条</span>
        </div>
        <ol className="space-y-2">
          {rules.map((rule, position) => (
            <li key={`${rule.index}-${rule.text}`} className="flex items-start gap-3 rounded-md border bg-background p-3">
              <span className="mt-0.5 min-w-6 text-xs tabular-nums text-muted-foreground">
                {position + 1}
              </span>
              <p className="min-w-0 flex-1 whitespace-pre-wrap text-sm leading-6">{rule.text}</p>
              <Button
                type="button"
                size="icon"
                variant="ghost"
                onClick={() => void onDelete(rule.index)}
                disabled={deletingIndex !== null}
                title="删除规则"
              >
                {deletingIndex === rule.index ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                <span className="sr-only">删除规则：{rule.text}</span>
              </Button>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
