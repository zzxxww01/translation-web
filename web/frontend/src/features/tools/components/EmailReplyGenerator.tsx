import { useState } from 'react';
import { toast } from 'sonner';
import { useGenerateEmailReply } from '../hooks';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Copy, RotateCw, Send, Trash2 } from 'lucide-react';
import { copyToClipboard } from '@/shared/utils';
import { EmailStyle } from '@/shared/constants';
import { cn } from '@/lib/utils';
import { PANE, PANE_FOOTER, PANE_HEADER, PANE_TEXTAREA } from '@/shared/ui/pane';

// 卡片里的单行输入：无边框，和下面的正文连成一张纸
const FIELD = 'h-10 rounded-none border-0 px-4 text-sm focus:border-transparent focus:shadow-none';
// 正文比文本翻译少掉发件人 / 主题那一行（41px），整张卡和文本翻译一样高，切标签时底边不跳；右栏随左栏等高
const BODY_MIN_H = 'min-h-[40svh] lg:min-h-[max(439px,calc(100svh-321px))]';

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
    try {
      const result = await emailMutation.mutateAsync({
        sender,
        subject,
        content,
        style,
      });
      setReplies(result.replies);
      setSelectedIdx(0);
    } catch {
      // Mutation hook owns the user-facing error message.
    }
  };

  const handleCopy = async () => {
    if (replies[selectedIdx]) {
      const ok = await copyToClipboard(replies[selectedIdx].content_en);
      if (ok) toast.success('已复制英文回复到剪贴板');
    }
  };

  const handleClear = () => {
    setSender('');
    setSubject('');
    setContent('');
    setReplies([]);
  };

  // 版式和文本翻译一样：左边收到的邮件、右边回复建议，两张等高的「纸」
  return (
    <div className="grid min-w-0 gap-5 md:grid-cols-2">
      <section className={PANE} aria-labelledby="email-input-label">
        <header className={PANE_HEADER}>
          <h2 id="email-input-label" className="text-[13px] font-semibold text-text-secondary">收到的邮件</h2>
          <Select value={style} onValueChange={(v) => setStyle(v as EmailStyle)}>
            <SelectTrigger className="h-7 w-auto gap-1 rounded-full border-transparent bg-bg-inset px-3 text-xs hover:border-transparent" aria-label="回复风格">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="professional">专业正式</SelectItem>
              <SelectItem value="polite">礼貌客气</SelectItem>
              <SelectItem value="casual">轻松随意</SelectItem>
            </SelectContent>
          </Select>
        </header>
        <div className="grid shrink-0 grid-cols-2 divide-x divide-border-subtle border-b border-border-subtle">
          <Input aria-label="发件人（可选）" placeholder="发件人（可选）" value={sender} onChange={(e) => setSender(e.target.value)} className={FIELD} />
          <Input aria-label="邮件主题（可选）" placeholder="主题（可选）" value={subject} onChange={(e) => setSubject(e.target.value)} className={FIELD} />
        </div>
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              void handleGenerate();
            }
          }}
          placeholder="粘贴收到的邮件内容…（Ctrl/⌘ + Enter 生成）"
          aria-label="邮件内容"
          className={cn(PANE_TEXTAREA, BODY_MIN_H)}
        />
        <footer className={PANE_FOOTER}>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" onClick={handleClear} disabled={!sender && !subject && !content && !replies.length}>
              <Trash2 />
              清空
            </Button>
            <span className="text-xs tabular-nums text-text-muted">{content.length} 字</span>
          </div>
          <Button size="sm" className="h-9 min-w-24" onClick={handleGenerate} disabled={!content.trim() || emailMutation.isPending}>
            {emailMutation.isPending ? <RotateCw className="animate-spin" /> : <Send />}
            生成回复
          </Button>
        </footer>
      </section>

      <section className={PANE} aria-labelledby="email-replies-label">
        <header className={PANE_HEADER}>
          <h2 id="email-replies-label" className="text-[13px] font-semibold text-text-secondary">
            回复建议{replies.length > 0 ? ` · ${replies.length} 条` : ''}
          </h2>
        </header>
        {/* 正文绝对定位、自己滚动：高度跟着左栏走，回复再多也不把卡片撑高 */}
        <div className="relative min-h-[40svh] flex-1 md:min-h-0">
        <div
          className={cn('absolute inset-0 overflow-y-auto bg-paper-primary px-4 py-3', emailMutation.isPending && 'opacity-60')}
          aria-live="polite"
        >
          {replies.length > 0 ? (
            <div className="space-y-2.5">
              {replies.map((reply, i) => (
                <button
                  key={i}
                  type="button"
                  className={cn(
                    'w-full rounded-lg border bg-white p-3.5 text-left transition-colors',
                    selectedIdx === i ? 'border-primary ring-1 ring-primary' : 'border-border-subtle hover:border-border'
                  )}
                  onClick={() => setSelectedIdx(i)}
                  aria-pressed={selectedIdx === i}
                >
                  <div className="mb-2 text-xs font-medium text-text-muted">{reply.type}</div>
                  <div className="mb-2.5 whitespace-pre-wrap text-sm leading-6 text-text-primary">{reply.content_en}</div>
                  <div className="whitespace-pre-wrap border-l-2 border-border-subtle pl-3 text-xs leading-6 text-text-muted">{reply.content_zh}</div>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-[15px] leading-7 text-text-disabled">生成的回复会出现在这里</p>
          )}
        </div>
        </div>
        <footer className={PANE_FOOTER}>
          <span className="px-2 text-xs text-text-muted">{replies.length > 1 ? '点一条选中' : ''}</span>
          <Button variant="outline" size="sm" className="h-9" onClick={handleCopy} disabled={!replies.length}>
            <Copy />
            复制选中回复
          </Button>
        </footer>
      </section>
    </div>
  );
}
