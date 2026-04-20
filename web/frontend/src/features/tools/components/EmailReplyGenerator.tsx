import { useState } from 'react';
import { toast } from 'sonner';
import { useGenerateEmailReply } from '../hooks';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Send, Copy, Trash2 } from 'lucide-react';
import { copyToClipboard } from '@/shared/utils';
import { EmailStyle } from '@/shared/constants';
import { cn } from '@/lib/utils';

export function EmailReplyGenerator() {
  const emailMutation = useGenerateEmailReply();
  const [sender, setSender] = useState('');
  const [subject, setSubject] = useState('');
  const [content, setContent] = useState('');
  const [style, setStyle] = useState<EmailStyle>(EmailStyle.PROFESSIONAL);
  const [replies, setReplies] = useState<Array<{ type: string; content_en: string; content_zh: string }>>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);

  const handleGenerate = async () => {
    if (!content.trim()) return;
    const result = await emailMutation.mutateAsync({
      sender,
      subject,
      content,
      style,
    });
    setReplies(result.replies);
    setSelectedIdx(0);
  };

  const handleCopy = async () => {
    if (replies[selectedIdx]) {
      const ok = await copyToClipboard(replies[selectedIdx].content_en);
      if (ok) toast.success('已复制英文回复到剪贴板');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem', width: '100%' }}>
      {/* Left: Input */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div className="space-y-1.5">
          <Label>发件人（可选）</Label>
          <Input placeholder="例如: John Smith" value={sender} onChange={(e) => setSender(e.target.value)} />
        </div>

        <div className="space-y-1.5">
          <Label>回复风格</Label>
          <Select value={style} onValueChange={(v) => setStyle(v as EmailStyle)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="professional">专业正式</SelectItem>
              <SelectItem value="polite">礼貌客气</SelectItem>
              <SelectItem value="casual">轻松随意</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label>邮件主题（可选）</Label>
          <Input placeholder="邮件主题..." value={subject} onChange={(e) => setSubject(e.target.value)} />
        </div>

        <div className="space-y-1.5" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <Label>邮件内容</Label>
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="粘贴收到的邮件内容..."
            className="resize-y"
            style={{ flex: 1, minHeight: '200px', maxHeight: '300px' }}
          />
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => { setSender(''); setSubject(''); setContent(''); setReplies([]); }}
          >
            <Trash2 className="h-4 w-4" />
            清空
          </Button>
          <Button
            onClick={handleGenerate}
            disabled={!content.trim() || emailMutation.isPending}
          >
            <Send className="h-4 w-4" />
            {emailMutation.isPending ? '生成中...' : '生成回复'}
          </Button>
        </div>
      </div>

      {/* Right: Replies */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {replies.length > 0 ? (
          <>
            <h4 className="text-sm font-semibold">回复建议</h4>
            <div className="space-y-2" style={{ flex: 1, overflowY: 'auto' }}>
              {replies.map((reply, i) => (
                <Card
                  key={i}
                  onClick={() => setSelectedIdx(i)}
                  className={cn(
                    'cursor-pointer transition-colors',
                    selectedIdx === i && 'border-primary ring-1 ring-primary'
                  )}
                >
                  <CardContent className="p-4">
                    <div className="mb-2 text-xs font-medium text-muted-foreground">{reply.type}</div>
                    <div className="mb-3 text-sm whitespace-pre-wrap border-l-2 border-primary pl-3">{reply.content_en}</div>
                    <div className="text-xs text-muted-foreground whitespace-pre-wrap border-l-2 border-muted pl-3">{reply.content_zh}</div>
                  </CardContent>
                </Card>
              ))}
            </div>
            <Button variant="outline" onClick={handleCopy}>
              <Copy className="h-4 w-4" />
              复制选中回复
            </Button>
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
            生成的回复将在这里显示
          </div>
        )}
      </div>
    </div>
  );
}
