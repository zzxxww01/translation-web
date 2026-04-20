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
  disabled?: boolean;
}

export function VersionCard({ version, label, onSelect, disabled }: VersionCardProps) {
  const handleCopyOnly = async () => {
    const ok = await copyToClipboard(version.english);
    if (ok) {
      toast.success('已复制到剪贴板');
    } else {
      toast.error('复制失败');
    }
  };

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="font-medium text-sm text-muted-foreground">{label}</div>
        <div className="flex gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={handleCopyOnly}
            disabled={disabled}
            className="h-8"
          >
            <Copy size={14} className="mr-1" />
            仅复制
          </Button>
          <Button
            size="sm"
            onClick={onSelect}
            disabled={disabled}
            className="h-8"
          >
            <Send size={14} className="mr-1" />
            选择并发送
          </Button>
        </div>
      </div>
      <div className="text-sm whitespace-pre-wrap break-words bg-muted/50 rounded p-3">
        {version.english}
      </div>
      {version.chinese && (
        <div className="mt-2 text-xs text-muted-foreground">
          中文: {version.chinese}
        </div>
      )}
    </Card>
  );
}
