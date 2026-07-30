import { useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Sparkles, Copy, Loader2 } from 'lucide-react';
import { copyToClipboard } from '@/shared/utils';
import { TITLE_INSTRUCTION_MAX_LENGTH } from '../types';

interface TitleGeneratorProps {
  onGenerate: (instruction?: string) => Promise<string[]>;
  isLoading: boolean;
  isGenerating: boolean;
  canGenerate: boolean;
  contentIdentity: string;
}

export function TitleGenerator({
  onGenerate,
  isLoading,
  isGenerating,
  canGenerate,
  contentIdentity,
}: TitleGeneratorProps) {
  const [instruction, setInstruction] = useState('');
  const [titleResult, setTitleResult] = useState<{
    contentIdentity: string;
    titles: string[];
  } | null>(null);
  // 已生成的标题一律保留：内容变化只标记为「已过期」，不清空，
  // 否则在译文里敲一个字符或一次请求失败就会把用户还没复制的结果抹掉
  const titles = titleResult?.titles ?? [];
  const isStale =
    titleResult !== null && titleResult.contentIdentity !== contentIdentity;

  const handleGenerate = async () => {
    try {
      const result = await onGenerate(instruction.trim() || undefined);
      if (result.length > 0) {
        setTitleResult({ contentIdentity, titles: result });
      }
    } catch {
      // 请求错误由统一 mutation 错误处理器展示。
    }
  };

  const handleCopy = async (title: string) => {
    const ok = await copyToClipboard(title);
    if (ok) toast.success('标题已复制');
    else toast.error('复制失败，请长按标题手动复制');
  };

  return (
    <div className="rounded-xl border border-white/60 bg-white/85 p-4 shadow-sm backdrop-blur-sm">
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h4 className="text-sm font-semibold">生成标题</h4>
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
            className="h-10 min-w-24 sm:h-9 sm:min-w-0"
          >
            {isGenerating ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
            {isGenerating ? '生成中' : '生成'}
          </Button>
        </div>

        <div>
          <Input
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            maxLength={TITLE_INSTRUCTION_MAX_LENGTH}
            aria-label="标题生成要求"
            placeholder="标题要求（可选），例如：突出核心观点，语气克制"
            disabled={isLoading}
            className="h-10 w-full"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            写一两个词即可，系统会自动补全为完整 prompt
          </p>
        </div>

        {isStale && titles.length > 0 && (
          <p className="text-xs text-muted-foreground">
            这批标题基于此前的内容生成，仍可点击复制；如需匹配当前内容请重新生成。
          </p>
        )}

        {titles.length > 0 ? (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {titles.map((title, i) => (
              <button
                key={i}
                type="button"
                className="group relative min-h-12 rounded-lg border bg-white/70 p-3 pr-9 text-left text-sm leading-relaxed transition-colors hover:border-primary/50 active:border-primary active:bg-primary/5"
                onClick={() => handleCopy(title)}
                title="复制标题"
              >
                {title}
                <Copy className="absolute right-3 top-3 h-4 w-4 opacity-60 transition-opacity group-hover:opacity-90" />
              </button>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center rounded-lg border border-dashed py-6 text-sm text-muted-foreground">
            生成后点击任意标题即可复制
          </div>
        )}
      </div>
    </div>
  );
}
