import { useEffect, useState } from 'react';
import { Copy, Send, Edit2, Check, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import { copyToClipboard } from '@/shared/utils';
import type { SlackReplyVariant } from '@/shared/types';
import { cn } from '@/lib/utils';

interface VersionCardProps {
  version: SlackReplyVariant;
  label: string;
  onSelect: () => void;
  onRefine?: (updatedVersion: SlackReplyVariant) => void;
  disabled?: boolean;
}

export function VersionCard({ version, label, onSelect, onRefine, disabled }: VersionCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedEnglish, setEditedEnglish] = useState(version.english || '');
  const [showSuccess, setShowSuccess] = useState(false);

  useEffect(() => {
    if (!isEditing) {
      setEditedEnglish(version.english || '');
    }
  }, [isEditing, version.english]);

  const handleCopyOnly = async () => {
    const ok = await copyToClipboard(version.english);
    if (ok) {
      toast.success('已复制到剪贴板');
    } else {
      toast.error('复制失败');
    }
  };

  const handleSave = async () => {
    const nextEnglish = editedEnglish.trim();
    if (!nextEnglish || nextEnglish === version.english) {
      setIsEditing(false);
      return;
    }

    if (onRefine) {
      onRefine({
        ...version,
        english: nextEnglish,
      });
    }

    toast.success('已更新英文');
    setIsEditing(false);
    setShowSuccess(true);
    setTimeout(() => setShowSuccess(false), 500);
  };

  const handleCancel = () => {
    setEditedEnglish(version.english || '');
    setIsEditing(false);
  };

  return (
    <Card className={cn(
      "version-card",
      isEditing && "editing",
      showSuccess && "save-success"
    )}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="style-tag">{label}</span>
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
                编辑英文
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
                className="h-7 text-xs px-2"
              >
                <Check size={12} className="mr-1" />
                保存
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCancel}
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
          {version.chinese && (
            <div className="text-xs leading-relaxed opacity-60" style={{
              color: 'var(--color-muted)',
              fontFamily: 'var(--font-chinese)'
            }}>
              {version.chinese}
            </div>
          )}
          <div className="text-xs mb-1" style={{ color: 'var(--color-muted)' }}>英文结果</div>
          <textarea
            value={editedEnglish}
            onChange={(e) => setEditedEnglish(e.target.value)}
            className="editorial-textarea w-full min-h-[120px] p-3 text-sm border rounded resize-y leading-relaxed"
            style={{
              fontFamily: 'var(--font-body)',
              borderColor: 'var(--color-border)'
            }}
            autoFocus
            placeholder="编辑英文回复..."
          />
        </div>
      ) : (
        <>
          {version.chinese && (
            <div className="text-xs mb-2 opacity-60" style={{
              color: 'var(--color-muted)',
              fontFamily: 'var(--font-chinese)'
            }}>
              {version.chinese}
            </div>
          )}
          <div className="text-sm whitespace-pre-wrap break-words leading-relaxed" style={{
            fontFamily: 'var(--font-body)'
          }}>
            {version.english}
          </div>
        </>
      )}
    </Card>
  );
}
