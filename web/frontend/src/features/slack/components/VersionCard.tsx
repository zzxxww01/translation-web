import { useState } from 'react';
import { Copy, Send, Edit2, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import { copyToClipboard } from '@/shared/utils';
import type { SlackReplyVariant } from '@/shared/types';
import { useRefineVersion } from '../hooks/useRefineVersion';

interface VersionCardProps {
  version: SlackReplyVariant;
  label: string;
  onSelect: () => void;
  onRefine?: (updatedVersion: SlackReplyVariant) => void;
  disabled?: boolean;
}

const STYLE_MAP: Record<string, string> = {
  A: '简洁',
  B: '正式',
  C: '友好',
};

export function VersionCard({ version, label, onSelect, onRefine, disabled }: VersionCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedChinese, setEditedChinese] = useState(version.chinese || '');
  const refineMutation = useRefineVersion();

  const handleCopyOnly = async () => {
    const ok = await copyToClipboard(version.english);
    if (ok) {
      toast.success('已复制到剪贴板');
    } else {
      toast.error('复制失败');
    }
  };

  const handleSave = async () => {
    if (!editedChinese.trim() || editedChinese === version.chinese) {
      setIsEditing(false);
      return;
    }

    const style = STYLE_MAP[version.version] || '正式';

    try {
      const updated = await refineMutation.mutateAsync({
        version: version.version,
        chinese: editedChinese,
        style,
      });

      if (onRefine) {
        onRefine(updated);
      }

      toast.success('已更新翻译');
      setIsEditing(false);
    } catch (error) {
      toast.error('更新失败');
    }
  };

  const handleCancel = () => {
    setEditedChinese(version.chinese || '');
    setIsEditing(false);
  };

  return (
    <Card className="p-3">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <div className="font-semibold text-xs text-muted-foreground">{label}</div>
          {version.style && (
            <span className="text-xs px-1.5 py-0.5 bg-muted rounded">{version.style}</span>
          )}
        </div>
        <div className="flex gap-1.5">
          {!isEditing && (
            <>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setIsEditing(true)}
                disabled={disabled}
                className="h-7 text-xs px-2"
              >
                <Edit2 size={12} className="mr-1" />
                编辑
              </Button>
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
                onClick={onSelect}
                disabled={disabled}
                className="h-7 text-xs px-2"
              >
                <Send size={12} className="mr-1" />
                发送
              </Button>
            </>
          )}
          {isEditing && (
            <>
              <Button
                size="sm"
                onClick={handleSave}
                disabled={refineMutation.isPending}
                className="h-7 text-xs px-2"
              >
                <Check size={12} className="mr-1" />
                {refineMutation.isPending ? '保存中...' : '保存'}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCancel}
                disabled={refineMutation.isPending}
                className="h-7 text-xs px-2"
              >
                <X size={12} className="mr-1" />
                取消
              </Button>
            </>
          )}
        </div>
      </div>

      {isEditing ? (
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground mb-1">中文内容</div>
          <textarea
            value={editedChinese}
            onChange={(e) => setEditedChinese(e.target.value)}
            className="w-full min-h-[60px] p-2 text-sm border rounded resize-none leading-relaxed"
            autoFocus
            placeholder="输入中文内容..."
          />
        </div>
      ) : (
        <>
          {version.chinese && (
            <div className="text-xs text-muted-foreground mb-2 opacity-60">
              {version.chinese}
            </div>
          )}
          <div className="text-sm whitespace-pre-wrap break-words leading-relaxed">
            {version.english}
          </div>
        </>
      )}
    </Card>
  );
}
