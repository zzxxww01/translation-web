import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Copy, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { copyToClipboard, getCharCount } from '@/shared/utils';
import { TranslationVersionType } from '@/shared/constants';

interface Version {
  id: string;
  content: string;
  type: string;
  instruction?: string;
  versionNumber: number;
}

interface TranslationOutputProps {
  versions: Version[];
  currentVersionId: string | null;
  currentContent: string;
  isEdited: boolean;
  editedContent: string;
  onSetCurrentVersion: (id: string) => void;
  onSetEditedContent: (content: string) => void;
  onSaveEdit: () => void;
  onDiscardEdit: () => void;
}

export function TranslationOutput({
  versions, currentVersionId, currentContent, isEdited, editedContent,
  onSetCurrentVersion, onSetEditedContent, onSaveEdit, onDiscardEdit,
}: TranslationOutputProps) {
  const charCount = getCharCount(currentContent);

  const handleCopy = async () => {
    const content = isEdited ? editedContent : versions.find(v => v.id === currentVersionId)?.content || '';
    if (content) {
      const ok = await copyToClipboard(content);
      if (ok) toast.success('已复制');
    }
  };

  return (
    <div className="flex flex-1 flex-col">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold">译文</h3>
          {versions.length > 0 && (
            <Select value={currentVersionId || ''} onValueChange={onSetCurrentVersion}>
              <SelectTrigger className="h-8 w-48">
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
        <div className="flex items-center gap-2">
          {isEdited && <Badge variant="warning">已编辑</Badge>}
          <span className="text-xs text-muted-foreground">{charCount} 字</span>
        </div>
      </div>

      <Textarea
        id="translationEditor"
        value={currentContent}
        onChange={(e) => onSetEditedContent(e.target.value)}
        placeholder="译文..."
        className="flex-1 min-h-[250px]"
      />

      <div className="mt-3 flex justify-end gap-2">
        <Button variant="outline" size="icon" className="h-8 w-8" onClick={handleCopy} disabled={!currentContent} title="复制">
          <Copy className="h-4 w-4" />
        </Button>
        {isEdited && (
          <>
            <Button variant="outline" size="sm" onClick={onDiscardEdit}>放弃</Button>
            <Button size="sm" onClick={onSaveEdit}>
              <Sparkles className="h-4 w-4" /> 保存版本
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
