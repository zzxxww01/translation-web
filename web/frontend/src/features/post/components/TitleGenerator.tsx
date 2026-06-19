import { useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { Sparkles, Copy, Loader2 } from 'lucide-react';
import { copyToClipboard } from '@/shared/utils';

interface TitleGeneratorProps {
  onGenerate: (instruction?: string) => Promise<string[]>;
  isLoading: boolean;
  isGenerating: boolean;
  canGenerate: boolean;
}

export function TitleGenerator({ onGenerate, isLoading, isGenerating, canGenerate }: TitleGeneratorProps) {
  const [instruction, setInstruction] = useState('');
  const [titles, setTitles] = useState<string[]>([]);

  const handleGenerate = async () => {
    const result = await onGenerate(instruction.trim() || undefined);
    setTitles(result);
    if (result.length === 0) {
      toast.info('内容太短，先补充原文或译文后再生成标题');
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
          </div>
          <Button
            size="sm"
            variant="outline"
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
            placeholder="标题要求（可选），例如：突出核心观点，语气克制"
            disabled={isLoading}
            className="h-10 w-full"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            写一两个词即可，系统会自动补全为完整 prompt
          </p>
        </div>

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
