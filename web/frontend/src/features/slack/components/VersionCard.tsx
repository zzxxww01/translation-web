import { useState } from 'react';
import { Copy, Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import { copyToClipboard } from '@/shared/utils';
import type { SlackReplyVariant } from '@/shared/types';

interface VersionCardProps {
  version: SlackReplyVariant;
  label: string;
  onSelect: () => void;
  onEdit?: (newEnglish: string) => void;
  disabled?: boolean;
}

export function VersionCard({ version, label, onSelect, onEdit, disabled }: VersionCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(version.english);

  const handleCopyOnly = async () => {
    const ok = await copyToClipboard(isEditing ? editContent : version.english);
    if (ok) {
      toast.success('已复制到剪贴板');
    } else {
      toast.error('复制失败');
    }
  };

  const handleSend = () => {
    if (isEditing && editContent !== version.english && onEdit) {
      onEdit(editContent);
    }
    onSelect();
  };

  const handleBlur = () => {
    if (editContent !== version.english && onEdit) {
      onEdit(editContent);
    }
    setIsEditing(false);
  };

  return (
    <Card className="p-3">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="font-semibold text-xs text-muted-foreground">{label}</div>
        <div className="flex gap-1.5">
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopyOnly}
            disabled={disabled}
            className="h-7 text-xs px-2"
          >
            <Copy size={12} className="mr-1" />
            复制
          </Button>
          <Button
            size="sm"
            onClick={handleSend}
            disabled={disabled}
            className="h-7 text-xs px-2"
          >
            <Send size={12} className="mr-1" />
            发送
          </Button>
        </div>
      </div>
      {isEditing ? (
        <textarea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          onBlur={handleBlur}
          className="w-full min-h-[60px] p-2 text-sm border rounded resize-none leading-relaxed"
          autoFocus
        />
      ) : (
        <div
          className="text-sm whitespace-pre-wrap break-words leading-relaxed cursor-text hover:bg-muted/30 rounded p-2 -m-2"
          onClick={() => setIsEditing(true)}
        >
          {editContent}
        </div>
      )}
      {version.chinese && (
        <div className="mt-1.5 text-xs text-muted-foreground opacity-60">
          {version.chinese}
        </div>
      )}
    </Card>
  );
}
