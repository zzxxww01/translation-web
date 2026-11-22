import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/Button';
import { Loader2, Send, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { POST_CONTENT_MAX_LENGTH } from '../types';
import { PANE, PANE_FOOTER, PANE_HEADER, PANE_TEXTAREA } from '@/shared/ui/pane';

interface SourceInputProps {
  value: string;
  onChange: (value: string) => void;
  onTranslate: () => void;
  onClear: () => void;
  isLoading: boolean;
  isTranslating: boolean;
  canClear: boolean;
  /** 放在有栏头的分栏里时不再显示「原文」小标题 */
  hideTitle?: boolean;
  /** 原文框高度（分栏里撑满） */
  className?: string;
}

export function SourceInput({ value, onChange, onTranslate, onClear, isLoading, isTranslating, canClear, hideTitle, className }: SourceInputProps) {
  // 计数与上限必须同源：都用 value.length（与后端校验口径一致）
  const charCount = value.length;

  const handleChange = (next: string) => {
    if (next.length > POST_CONTENT_MAX_LENGTH) {
      // textarea 原生 maxLength 会在粘贴时静默截断且不产生任何事件，
      // 这里改为显式截断并告知用户被丢弃了多少字符
      const dropped = next.length - POST_CONTENT_MAX_LENGTH;
      onChange(next.slice(0, POST_CONTENT_MAX_LENGTH));
      toast.warning(
        `原文超出 ${POST_CONTENT_MAX_LENGTH.toLocaleString()} 字符上限，已截断 ${dropped.toLocaleString()} 个字符`
      );
      return;
    }
    onChange(next);
  };

  const count = (
    <span className="text-xs tabular-nums text-text-muted">
      {charCount.toLocaleString()}/{POST_CONTENT_MAX_LENGTH.toLocaleString()}
    </span>
  );
  const actions = (
    <>
      <Button type="button" variant="ghost" size="sm" onClick={onClear} disabled={isLoading || !canClear}>
        <Trash2 /> 清空
      </Button>
      <Button
        type="button"
        onClick={onTranslate}
        disabled={!value.trim() || isLoading}
        size="sm"
        className="h-9 min-w-24 px-4"
        title="翻译 (Ctrl+Enter)"
        aria-label={isTranslating ? '正在翻译帖子' : '翻译帖子'}
      >
        {isTranslating ? <Loader2 className="animate-spin" /> : <Send />}
        <span>{isTranslating ? '翻译中' : '翻译'}</span>
      </Button>
    </>
  );
  const textarea = (extra: string) => (
    <Textarea
      id="postSourceInput"
      value={value}
      onChange={(e) => handleChange(e.target.value)}
      aria-label="帖子原文"
      placeholder="把英文帖子粘贴到这里…"
      className={className ?? extra}
    />
  );

  // 分栏里（Slack）：栏头已经有标题，保持原来的轻量排法
  if (hideTitle) {
    return (
      <div className="flex min-w-0 flex-col">
        <div className="mb-3 flex justify-end">{count}</div>
        {textarea('min-h-[42svh] resize-y')}
        <div className="mt-4 flex items-center justify-between gap-3">{actions}</div>
      </div>
    );
  }

  // 帖子翻译页：一张纸，上面栏名和字数，下面一条操作栏；和译文那张等高
  return (
    <section className={PANE}>
      <header className={PANE_HEADER}>
        <h3 className="text-[13px] font-semibold text-text-secondary">原文</h3>
        {count}
      </header>
      {textarea(PANE_TEXTAREA)}
      <footer className={PANE_FOOTER}>{actions}</footer>
    </section>
  );
}
