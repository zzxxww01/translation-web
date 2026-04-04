import { Badge } from '@/components/ui/badge';
import { ButtonExtended as Button } from '@/components/ui/button-extended';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Star } from 'lucide-react';
import type { GlossaryTerm, TranslationStrategy } from '@/features/confirmation/types';
import type { EditingTerm, GlossaryScope } from '../types';
import { scopeLabel, strategyExamples } from '../types';

interface TermEditorProps {
  activeScope: GlossaryScope;
  isCreating: boolean;
  focusedTerm: GlossaryTerm | null;
  editor: EditingTerm;
  isSaving: boolean;
  tagDraft: string;
  onEditorChange: (updater: (current: EditingTerm) => EditingTerm) => void;
  onTagDraftChange: (value: string) => void;
  onAddTagFromDraft: () => void;
  onRemoveEditorTag: (tag: string) => void;
  onSave: () => void;
  onDelete: (original: string) => void;
  onReset: () => void;
}

export function TermEditor({
  activeScope,
  isCreating,
  focusedTerm,
  editor,
  isSaving,
  tagDraft,
  onEditorChange,
  onTagDraftChange,
  onAddTagFromDraft,
  onRemoveEditorTag,
  onSave,
  onDelete,
  onReset,
}: TermEditorProps) {
  if (activeScope === 'recommendations') {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Star className="h-4 w-4" />
            推荐提升说明
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-6 text-muted-foreground">
            这里展示的是项目内高频、适合沉淀为全局标准的术语。提升到全局后，帖子翻译、Slack、工具箱和其他项目都可以复用。
          </p>
        </CardContent>
      </Card>
    );
  }

  if (!isCreating && !focusedTerm) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-white p-8 text-center text-muted-foreground">
        从左侧列表选择一条术语，或创建新术语。
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-lg">{isCreating ? '新建术语' : '编辑术语'}</CardTitle>
            <p className="text-sm text-muted-foreground">{scopeLabel(activeScope)}</p>
          </div>
          <Button size="sm" variant="outline" onClick={onReset}>
            取消
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label className="mb-1 block">原文术语</Label>
          <Input
            value={editor.original}
            disabled={!isCreating}
            onChange={event => onEditorChange(current => ({ ...current, original: event.target.value }))}
            placeholder="例如 TSMC"
          />
        </div>

        <div>
          <Label className="mb-1 block">译法</Label>
          <Input
            value={editor.translation}
            onChange={event => onEditorChange(current => ({ ...current, translation: event.target.value }))}
            placeholder="例如 台积电"
          />
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <Label className="mb-1 block">策略</Label>
            <Select
              value={editor.strategy}
              onValueChange={(value: string) =>
                onEditorChange(current => ({ ...current, strategy: value as TranslationStrategy }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="translate">翻译</SelectItem>
                <SelectItem value="first_annotate">首次标注</SelectItem>
                <SelectItem value="preserve">保留原文</SelectItem>
                <SelectItem value="preserve_annotate">保留原文+首次注释</SelectItem>
              </SelectContent>
            </Select>
            <p className="mt-1.5 text-xs leading-5 text-muted-foreground">
              {strategyExamples[editor.strategy]}
            </p>
          </div>
          <div>
            <Label className="mb-1 block">状态</Label>
            <Select
              value={editor.status}
              onValueChange={(value: string) =>
                onEditorChange(current => ({ ...current, status: value as 'active' | 'disabled' }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="active">active</SelectItem>
                <SelectItem value="disabled">disabled</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div>
          <Label className="mb-1 block">词义说明</Label>
          <Textarea
            value={editor.note}
            onChange={event => onEditorChange(current => ({ ...current, note: event.target.value }))}
            rows={4}
            placeholder="说明这里指的是什么意思，为什么在当前语境下要这样翻"
          />
        </div>

        <div>
          <Label className="mb-1 block">标签</Label>
          <div className="flex gap-2">
            <Input
              value={tagDraft}
              onChange={event => onTagDraftChange(event.target.value)}
              onKeyDown={event => {
                if (event.key === 'Enter') {
                  event.preventDefault();
                  onAddTagFromDraft();
                }
              }}
              placeholder="输入标签，逗号分隔"
            />
            <Button size="sm" variant="outline" onClick={onAddTagFromDraft}>
              添加标签
            </Button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {editor.tags.length ? (
              editor.tags.map(tag => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className="cursor-pointer gap-1"
                  onClick={() => onRemoveEditorTag(tag)}
                >
                  {tag}
                  <span aria-hidden="true">x</span>
                </Badge>
              ))
            ) : (
              <span className="text-sm text-muted-foreground">尚未添加标签</span>
            )}
          </div>
        </div>

        <div className="flex flex-wrap justify-end gap-2 pt-2">
          {!isCreating && focusedTerm ? (
            <Button size="sm" variant="destructive" onClick={() => onDelete(focusedTerm.original)}>
              删除
            </Button>
          ) : null}
          <Button size="sm" variant="outline" onClick={onReset}>
            取消
          </Button>
          <Button size="sm" isLoading={isSaving} onClick={onSave}>
            保存术语
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
