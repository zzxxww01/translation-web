import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Copy, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { copyToClipboard } from '@/shared/utils';
import { TranslationVersionType } from '@/shared/constants';
import type { TranslationVersion } from '@/shared/types';
import { POST_CONTENT_MAX_LENGTH } from '../types';
import { PANE, PANE_FOOTER, PANE_HEADER, PANE_TEXTAREA } from '@/shared/ui/pane';

interface TranslationOutputProps {
  versions: TranslationVersion[];
  currentVersionId: string | null;
  originalText: string;
  currentContent: string;
  isEdited: boolean;
  editedContent: string;
  onSetCurrentVersion: (id: string) => void;
  onSetEditedContent: (content: string) => void;
  onSaveEdit: () => void;
  onDiscardEdit: () => void;
  /** 放在有栏头的分栏里时不再显示「译文」小标题 */
  hideTitle?: boolean;
  /** 译文框之后、复制按钮旁边的额外按钮 */
  extraActions?: React.ReactNode;
}

/**
 * 判断某个版本是否基于与当前原文不同的底稿。
 * 必须比原文文本而不是 sourceRevision —— revision 单调递增，用户「改一个字再删掉」
 * 后文本完全相同但 revision 已经 +2，会常驻一个误导性的「原文已更新」徽标。
 */
function isStaleVersion(version: TranslationVersion, originalText: string): boolean {
  return version.sourceText.trim() !== '' && version.sourceText !== originalText;
}

export function TranslationOutput({
  versions, currentVersionId, originalText, currentContent, isEdited, editedContent,
  onSetCurrentVersion, onSetEditedContent, onSaveEdit, onDiscardEdit, hideTitle, extraActions,
}: TranslationOutputProps) {
  // 计数与上限同源，都用 length（与后端校验口径一致）
  const charCount = currentContent.length;
  const currentVersion = versions.find(v => v.id === currentVersionId);
  const isBasedOnOlderSource =
    currentVersion !== undefined && isStaleVersion(currentVersion, originalText);

  const handleChange = (next: string) => {
    if (next.length > POST_CONTENT_MAX_LENGTH) {
      const dropped = next.length - POST_CONTENT_MAX_LENGTH;
      onSetEditedContent(next.slice(0, POST_CONTENT_MAX_LENGTH));
      toast.warning(
        `译文超出 ${POST_CONTENT_MAX_LENGTH.toLocaleString()} 字符上限，已截断 ${dropped.toLocaleString()} 个字符`
      );
      return;
    }
    onSetEditedContent(next);
  };

  const handleCopy = async () => {
    const content = isEdited ? editedContent : versions.find(v => v.id === currentVersionId)?.content || '';
    if (content) {
      const ok = await copyToClipboard(content);
      if (ok) toast.success('译文已复制');
      else toast.error('复制失败，请长按文本手动复制');
    }
  };

  const versionPicker = versions.length > 0 && (
    <Select value={currentVersionId || ''} onValueChange={onSetCurrentVersion}>
      <SelectTrigger className={hideTitle ? 'h-9 w-full min-w-0 sm:w-48' : 'h-7 w-auto min-w-0 max-w-52 rounded-full border-transparent bg-bg-inset px-3 text-xs hover:border-transparent'} aria-label="选择译文版本">
        <SelectValue placeholder="选择版本" />
      </SelectTrigger>
      <SelectContent>
        {versions.map(v => {
          const typeLabel = v.type === TranslationVersionType.TRANSLATION ? '翻译' :
            v.type === TranslationVersionType.OPTIMIZATION ? '优化' : '编辑';
          const instruction = v.instruction?.trim() ?? '';
          const preview = instruction
            ? ` - ${instruction.length > 12 ? `${instruction.slice(0, 12)}…` : instruction}`
            : '';
          const staleMark = isStaleVersion(v, originalText) ? ' · 旧底稿' : '';
          return (
            <SelectItem key={v.id} value={v.id}>
              v{v.versionNumber} ({typeLabel}){preview}{staleMark}
            </SelectItem>
          );
        })}
      </SelectContent>
    </Select>
  );
  const status = (
    <div className="flex shrink-0 items-center gap-2">
      {isEdited && <Badge variant="warning">已编辑</Badge>}
      {isBasedOnOlderSource && <Badge variant="outline">原文已更新</Badge>}
      <span className="text-xs tabular-nums text-text-muted">
        {charCount.toLocaleString()}/{POST_CONTENT_MAX_LENGTH.toLocaleString()}
      </span>
    </div>
  );
  const textarea = (className: string) => (
    <Textarea
      id="translationEditor"
      value={currentContent}
      onChange={(e) => handleChange(e.target.value)}
      onKeyDown={(e) => {
        // Escape 只在译文编辑框内生效：挂到 window 上会与 Radix 弹层/下拉的
        // Escape 关闭逻辑抢同一次事件，导致确认框关不掉、语义被替换
        if (e.key === 'Escape' && !e.repeat && isEdited) {
          e.preventDefault();
          onDiscardEdit();
        }
      }}
      aria-label="帖子译文"
      placeholder={hideTitle ? '译文...' : '译文会出现在这里，可以直接改；改完点「保存版本」'}
      className={className}
    />
  );
  const actions = (
    <>
      {extraActions}
      {isEdited && (
        <>
          <Button type="button" variant="ghost" size="sm" onClick={onDiscardEdit}>放弃修改</Button>
          <Button type="button" variant="outline" size="sm" onClick={onSaveEdit} disabled={!editedContent.trim()}>
            <Sparkles /> 保存版本
          </Button>
        </>
      )}
      <Button type="button" variant={hideTitle ? 'outline' : 'default'} size="sm" className={hideTitle ? 'h-10 min-w-28 sm:h-9' : 'h-9 min-w-24 px-4'} onClick={handleCopy} disabled={!currentContent} title="复制译文">
        <Copy />
        复制译文
      </Button>
    </>
  );

  if (hideTitle) {
    return (
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 flex-wrap items-center gap-3">{versionPicker}</div>
          {status}
        </div>
        {textarea('min-h-[34svh] sm:min-h-[280px]')}
        <div className="mt-3 flex flex-wrap justify-end gap-2">{actions}</div>
      </div>
    );
  }

  return (
    <section className={PANE}>
      <header className={PANE_HEADER}>
        <div className="flex min-w-0 items-center gap-2">
          <h3 className="shrink-0 text-[13px] font-semibold text-text-secondary">译文</h3>
          {versionPicker}
        </div>
        {status}
      </header>
      {textarea(PANE_TEXTAREA)}
      <footer className={`${PANE_FOOTER} justify-end`}>{actions}</footer>
    </section>
  );
}
