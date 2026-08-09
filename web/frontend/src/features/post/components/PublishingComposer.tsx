import { useMemo, useState } from 'react';
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Copy,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  X,
} from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { copyToClipboard } from '@/shared/utils';
import {
  composeXiaohongshuPost,
  isGenericHashtag,
  normalizeHashtag,
} from '../publishing';

interface PublishingComposerProps {
  title: string;
  body: string;
  hashtags: string[];
  onAddHashtag: (hashtag: string) => void;
  onUpdateHashtag: (index: number, hashtag: string) => void;
  onRemoveHashtag: (index: number) => void;
  onMoveHashtag: (index: number, direction: -1 | 1) => void;
  onRegenerateHashtags: () => Promise<boolean>;
  isRegenerating: boolean;
}

export function PublishingComposer({
  title,
  body,
  hashtags,
  onAddHashtag,
  onUpdateHashtag,
  onRemoveHashtag,
  onMoveHashtag,
  onRegenerateHashtags,
  isRegenerating,
}: PublishingComposerProps) {
  const [newTag, setNewTag] = useState('');
  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editingValue, setEditingValue] = useState('');
  const composed = useMemo(
    () => composeXiaohongshuPost(title, body, hashtags),
    [body, hashtags, title]
  );

  const normalizeUserTag = (value: string) => {
    if (isGenericHashtag(value)) {
      toast.warning('标签过于宽泛，请填写文章中的具体公司、产品、技术或事件');
      return null;
    }
    const normalized = normalizeHashtag(value);
    if (!normalized) toast.warning('请输入有效的具体标签');
    return normalized;
  };

  const handleAdd = () => {
    const normalized = normalizeUserTag(newTag);
    if (!normalized) return;
    onAddHashtag(normalized);
    setNewTag('');
  };

  const handleEdit = (index: number) => {
    const normalized = normalizeUserTag(editingValue);
    if (!normalized) return;
    onUpdateHashtag(index, normalized);
    setEditingIndex(null);
    setEditingValue('');
  };

  const handleCopy = async () => {
    if (!composed) return;
    const copied = await copyToClipboard(composed);
    if (copied) toast.success('完整小红书帖子已复制');
    else toast.error('复制失败，请长按预览内容手动复制');
  };

  return (
    <section
      id="publishingComposer"
      tabIndex={-1}
      className="rounded-lg border bg-background p-4 outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
      aria-labelledby="publishingComposerTitle"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 id="publishingComposerTitle" className="text-sm font-semibold">
            小红书发布组合
          </h3>
          <p className="mt-1 text-xs text-muted-foreground">
            标题、正文和标签会合并为一份可直接发布的内容
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => void onRegenerateHashtags()}
            disabled={!body.trim() || isRegenerating}
          >
            {isRegenerating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {isRegenerating ? '更新中' : '仅更新标签'}
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={handleCopy}
            disabled={!composed}
          >
            <Copy className="h-4 w-4" />
            复制完整帖子
          </Button>
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-2 flex items-center justify-between gap-3">
          <span className="text-xs font-medium text-muted-foreground">具体标签</span>
          <span className="text-xs text-muted-foreground">{hashtags.length}/8</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {hashtags.map((tag, index) => (
            <div
              key={`${tag}-${index}`}
              className="flex min-h-9 max-w-full items-center gap-1 rounded-md border bg-muted/35 px-2"
            >
              {editingIndex === index ? (
                <>
                  <Input
                    value={editingValue}
                    onChange={event => setEditingValue(event.target.value)}
                    onKeyDown={event => {
                      if (event.key === 'Enter') {
                        event.preventDefault();
                        handleEdit(index);
                      }
                      if (event.key === 'Escape') setEditingIndex(null);
                    }}
                    className="h-7 w-36 border-0 bg-transparent px-1 shadow-none"
                    aria-label={`编辑标签 ${tag}`}
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={() => handleEdit(index)}
                    className="rounded p-1 text-muted-foreground hover:bg-background hover:text-foreground"
                    aria-label="保存标签"
                  >
                    <Check className="h-3.5 w-3.5" />
                  </button>
                </>
              ) : (
                <>
                  <span className="max-w-44 truncate text-xs font-medium">{tag}</span>
                  <button
                    type="button"
                    onClick={() => {
                      setEditingIndex(index);
                      setEditingValue(tag);
                    }}
                    className="rounded p-1 text-muted-foreground hover:bg-background hover:text-foreground"
                    aria-label={`编辑 ${tag}`}
                    title="编辑标签"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onMoveHashtag(index, -1)}
                    disabled={index === 0}
                    className="rounded p-1 text-muted-foreground hover:bg-background hover:text-foreground disabled:opacity-30"
                    aria-label={`前移 ${tag}`}
                    title="前移"
                  >
                    <ArrowLeft className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onMoveHashtag(index, 1)}
                    disabled={index === hashtags.length - 1}
                    className="rounded p-1 text-muted-foreground hover:bg-background hover:text-foreground disabled:opacity-30"
                    aria-label={`后移 ${tag}`}
                    title="后移"
                  >
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onRemoveHashtag(index)}
                    className="rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    aria-label={`删除 ${tag}`}
                    title="删除标签"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </>
              )}
            </div>
          ))}
          {hashtags.length < 8 && (
            <div className="flex min-h-9 min-w-0 items-center gap-1 rounded-md border border-dashed px-2">
              <Input
                value={newTag}
                onChange={event => setNewTag(event.target.value)}
                onKeyDown={event => {
                  if (event.key === 'Enter') {
                    event.preventDefault();
                    handleAdd();
                  }
                }}
                className="h-7 min-w-0 w-32 border-0 bg-transparent px-1 shadow-none"
                placeholder="公司、产品或技术"
                aria-label="添加具体标签"
              />
              <button
                type="button"
                onClick={handleAdd}
                className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                aria-label="添加标签"
                title="添加标签"
              >
                <Plus className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
        {hashtags.length === 0 && (
          <p className="mt-2 text-xs text-muted-foreground">
            暂无具体标签。可从正文重新识别，或手动添加文章中的实体和技术主题。
          </p>
        )}
      </div>

      <div className="mt-4 rounded-md border bg-muted/20 p-4">
        <p className="mb-2 text-xs font-medium text-muted-foreground">发布预览</p>
        {composed ? (
          <div className="max-h-80 overflow-y-auto whitespace-pre-wrap break-words text-sm leading-7">
            {composed}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">翻译完成后在这里组合发布内容</p>
        )}
      </div>
    </section>
  );
}
