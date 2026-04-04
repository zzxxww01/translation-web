import { type FC, useMemo, useState } from 'react';
import { Check, Copy, Edit3, X } from 'lucide-react';
import { toast } from 'sonner';
import type { SlackReplyVariant } from '@/shared/types';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { copyToClipboard } from '@/shared/utils';
import { cn } from '@/lib/utils';

interface ReplySuggestionsProps {
  title: string;
  options: SlackReplyVariant[];
  onSelectReply: (contentEn: string, contentCn: string) => void;
  onClose: () => void;
  confirmLabel?: string;
}

const VERSION_META: Record<string, { label: string; description: string }> = {
  A: { label: '版本 A', description: '最 casual，适合同级快速沟通' },
  B: { label: '版本 B', description: '标准职场 casual，适合跨部门协作' },
  C: { label: '版本 C', description: '稍正式，适合上司或大群' },
};

export const ReplySuggestions: FC<ReplySuggestionsProps> = ({
  title,
  options,
  onSelectReply,
  onClose,
  confirmLabel = '使用这个版本',
}) => {
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState('');

  const orderedOptions = useMemo(
    () => [...options].sort((a, b) => a.version.localeCompare(b.version)),
    [options]
  );

  const selectedOption = orderedOptions.find(o => o.version === selectedVersion) ?? null;

  const handleSelect = (option: SlackReplyVariant) => {
    setSelectedVersion(option.version);
    setEditedContent(option.english);
    setIsEditing(false);
  };

  const handleCopy = async (content: string) => {
    const ok = await copyToClipboard(content);
    if (ok) toast.success('已复制到剪贴板');
  };

  const handleConfirm = () => {
    if (!selectedOption) return;
    onSelectReply(isEditing ? editedContent : selectedOption.english, selectedOption.chinese ?? '');
  };

  if (orderedOptions.length === 0) return null;

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-medium">{title}</h4>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onClose}>
          <X className="h-3 w-3" />
        </Button>
      </div>

      <div className="space-y-2">
        {orderedOptions.map(option => {
          const meta = VERSION_META[option.version] ?? { label: `版本 ${option.version}`, description: '' };
          const isSelected = selectedVersion === option.version;

          return (
            <Card
              key={option.version}
              onClick={() => handleSelect(option)}
              className={cn(
                'cursor-pointer transition-colors',
                isSelected && 'border-primary ring-1 ring-primary'
              )}
            >
              <CardContent className="p-3">
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs font-medium text-muted-foreground">{meta.label}</span>
                  <span className="text-xs text-muted-foreground">{meta.description}</span>
                </div>
                <p className="text-sm">{option.english}</p>
                {option.chinese && (
                  <p className="mt-1 text-xs text-muted-foreground">中文参考: {option.chinese}</p>
                )}

                {isSelected && (
                  <div className="mt-2 flex gap-2">
                    <Button size="sm" variant="outline" onClick={e => { e.stopPropagation(); handleCopy(option.english); }}>
                      <Copy className="h-3 w-3" /> 复制
                    </Button>
                    <Button size="sm" variant="outline" onClick={e => { e.stopPropagation(); setIsEditing(c => !c); }}>
                      <Edit3 className="h-3 w-3" /> 编辑
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {isEditing && selectedOption && (
        <Textarea
          value={editedContent}
          onChange={e => setEditedContent(e.target.value)}
          placeholder="编辑英文回复..."
          className="mt-3 min-h-[72px]"
        />
      )}

      {selectedOption && (
        <div className="mt-3 flex justify-end">
          <Button size="sm" onClick={handleConfirm}>
            <Check className="h-4 w-4" /> {confirmLabel}
          </Button>
        </div>
      )}
    </div>
  );
};
