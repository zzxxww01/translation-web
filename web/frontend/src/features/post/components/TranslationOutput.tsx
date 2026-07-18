import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Copy, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { copyToClipboard, getCharCount } from '@/shared/utils';
import { TranslationVersionType } from '@/shared/constants';
import type { TranslationVersion } from '@/shared/types';
import { POST_CONTENT_MAX_LENGTH } from '../types';

interface TranslationOutputProps {
  versions: TranslationVersion[];
  currentVersionId: string | null;
  currentSourceRevision: number;
  currentContent: string;
  isEdited: boolean;
  editedContent: string;
  onSetCurrentVersion: (id: string) => void;
  onSetEditedContent: (content: string) => void;
  onSaveEdit: () => void;
  onDiscardEdit: () => void;
}

export function TranslationOutput({
  versions, currentVersionId, currentSourceRevision, currentContent, isEdited, editedContent,
  onSetCurrentVersion, onSetEditedContent, onSaveEdit, onDiscardEdit,
}: TranslationOutputProps) {
  const charCount = getCharCount(currentContent);
  const currentVersion = versions.find(v => v.id === currentVersionId);
  const isBasedOnOlderSource =
    currentVersion !== undefined && currentVersion.sourceRevision !== currentSourceRevision;

  const handleCopy = async () => {
    const content = isEdited ? editedContent : versions.find(v => v.id === currentVersionId)?.content || '';
    if (content) {
      const ok = await copyToClipboard(content);
      if (ok) toast.success('译文已复制');
      else toast.error('复制失败，请长按文本手动复制');
    }
  };

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex min-w-0 flex-wrap items-center gap-3">
          <h3 className="text-sm font-semibold">译文</h3>
          {versions.length > 0 && (
            <Select value={currentVersionId || ''} onValueChange={onSetCurrentVersion}>
              <SelectTrigger className="h-9 w-full min-w-0 sm:w-48" aria-label="选择译文版本">
                <SelectValue placeholder="选择版本" />
              </SelectTrigger>
              <SelectContent>
                {versions.map(v => {
                  const typeLabel = v.type === TranslationVersionType.TRANSLATION ? '翻译' :
                    v.type === TranslationVersionType.OPTIMIZATION ? '优化' : '编辑';
                  const preview = v.instruction ? ` - ${v.instruction.substring(0, 12)}...` : '';
                  return (
                    <SelectItem key={v.id} value={v.id}>
                      v{v.versionNumber} ({typeLabel}){preview}
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          )}
        </div>
        <div className="flex items-center justify-between gap-2 sm:justify-end">
          {isEdited && <Badge variant="warning">已编辑</Badge>}
          {isBasedOnOlderSource && <Badge variant="outline">原文已更新</Badge>}
          <span className="text-xs text-muted-foreground">
            {charCount.toLocaleString()}/{POST_CONTENT_MAX_LENGTH.toLocaleString()} 字
          </span>
        </div>
      </div>

      <Textarea
        id="translationEditor"
        value={currentContent}
        onChange={(e) => onSetEditedContent(e.target.value)}
        maxLength={POST_CONTENT_MAX_LENGTH}
        aria-label="帖子译文"
        placeholder="译文..."
        className="min-h-[34svh] sm:min-h-[280px] lg:min-h-[280px]"
      />

      <div className="mt-3 flex flex-wrap justify-end gap-2">
        <Button type="button" variant="outline" size="sm" className="h-10 min-w-28 sm:h-9" onClick={handleCopy} disabled={!currentContent} title="复制译文">
          <Copy className="h-4 w-4" />
          复制译文
        </Button>
        {isEdited && (
          <>
            <Button type="button" variant="outline" size="sm" onClick={onDiscardEdit}>放弃</Button>
            <Button type="button" size="sm" onClick={onSaveEdit} disabled={!editedContent.trim()}>
              <Sparkles className="h-4 w-4" /> 保存版本
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
