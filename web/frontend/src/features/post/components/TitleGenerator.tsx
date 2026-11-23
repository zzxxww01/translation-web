import { useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Sparkles, Loader2 } from 'lucide-react';
import { copyToClipboard } from '@/shared/utils';
import { TITLE_INSTRUCTION_MAX_LENGTH } from '../types';

const TITLE_MAX_LENGTH = 20;

interface TitleGeneratorProps {
  onGenerate: (instruction?: string) => Promise<string[]>;
  isLoading: boolean;
  isGenerating: boolean;
  canGenerate: boolean;
  contentIdentity: string;
  titles: string[];
  titlesContentIdentity: string;
  selectedTitle: string;
  onSelectTitle: (title: string) => void;
}

export function TitleGenerator({
  onGenerate,
  isLoading,
  isGenerating,
  canGenerate,
  contentIdentity,
  titles,
  titlesContentIdentity,
  selectedTitle,
  onSelectTitle,
}: TitleGeneratorProps) {
  const [instruction, setInstruction] = useState('');
  // 已生成的标题一律保留：内容变化只标记为「已过期」，不清空，
  // 否则在译文里敲一个字符或一次请求失败就会把用户还没复制的结果抹掉
  const isStale = titles.length > 0 && titlesContentIdentity !== contentIdentity;

  const handleGenerate = async () => {
    try {
      await onGenerate(instruction.trim() || undefined);
    } catch {
      // 请求错误由统一 mutation 错误处理器展示。
    }
  };

  const handleCopy = async (title: string) => {
    onSelectTitle(title);
    const ok = await copyToClipboard(title);
    if (ok) toast.success('标题已复制');
    else toast.error('复制失败，请长按标题手动复制');
  };

  return (
    <div className="rounded-xl border border-border-subtle bg-white p-4">
      <div className="space-y-3">
        <div className="flex min-h-8 items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <h4 className="flex items-center gap-2 text-[13px] font-semibold text-text-secondary">
              <Sparkles className="h-4 w-4 text-primary-500" />
              生成标题
            </h4>
            {isStale && titles.length > 0 && (
              <Badge variant="outline">内容已变更</Badge>
            )}
          </div>
          <Button
            size="sm"
            variant="outline"
            type="button"
            onClick={handleGenerate}
            disabled={isLoading || !canGenerate}
            className="h-8"
          >
            {isGenerating ? <Loader2 className="animate-spin" /> : <Sparkles />}
            {isGenerating ? '生成中' : '生成'}
          </Button>
        </div>

        <Input
          value={instruction}
          onChange={(e) => setInstruction(e.target.value)}
          maxLength={TITLE_INSTRUCTION_MAX_LENGTH}
          aria-label="标题生成要求"
          placeholder="要求（可选，写一两个词就行）：突出核心观点、语气克制…"
          disabled={isLoading}
          className="h-9 w-full"
        />

        {isStale && titles.length > 0 && (
          <p className="text-xs text-muted-foreground">
            这批标题基于此前的内容生成，仍可点击复制；如需匹配当前内容请重新生成。
          </p>
        )}

        {titles.length > 0 ? (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {titles.map((title, i) => {
              // 后端保证新生成的标题不超过 20 字；这里只拦早先存下的超长标题，不再逐条显示字数
              const tooLong = Array.from(title).length > TITLE_MAX_LENGTH;
              return (
                <button
                  key={i}
                  type="button"
                  className={`min-h-12 rounded-lg border border-border-subtle bg-bg-tertiary/40 p-3 text-left text-sm leading-relaxed transition-colors hover:border-primary-200 hover:bg-paper-hover disabled:opacity-60 ${selectedTitle === title ? 'border-primary-300 bg-primary-50' : ''}`}
                  onClick={() => handleCopy(title)}
                  disabled={tooLong}
                  title={tooLong ? '标题超过20字，请重新生成' : '点击复制标题'}
                >
                  {title}
                  {tooLong && (
                    <span className="block text-xs text-destructive">超过20字，请重新生成</span>
                  )}
                </button>
              );
            })}
          </div>
        ) : (
          <p className="py-2 text-xs text-text-muted">
            {canGenerate ? '生成后点任意一个标题就能复制。' : '先粘贴原文或翻译出译文。'}
          </p>
        )}
      </div>
    </div>
  );
}
