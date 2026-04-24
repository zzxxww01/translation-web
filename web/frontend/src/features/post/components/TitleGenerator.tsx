import { useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Sparkles, Copy } from 'lucide-react';
import { copyToClipboard } from '@/shared/utils';

interface TitleGeneratorProps {
  onGenerate: (instruction?: string) => Promise<string[]>;
  isLoading: boolean;
  canGenerate: boolean;
}

export function TitleGenerator({ onGenerate, isLoading, canGenerate }: TitleGeneratorProps) {
  const [instruction, setInstruction] = useState('');
  const [titles, setTitles] = useState<string[]>([]);

  const handleGenerate = async () => {
    const result = await onGenerate(instruction.trim() || undefined);
    setTitles(result);
  };

  const handleCopy = async (title: string) => {
    const ok = await copyToClipboard(title);
    if (ok) toast.success('标题已复制');
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h4 className="text-sm font-semibold">生成标题</h4>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={handleGenerate}
            disabled={isLoading || !canGenerate}
          >
            <Sparkles className="h-3 w-3" /> 生成
          </Button>
        </div>

        <div>
          <Input
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="标题要求（可选），例如：突出核心观点，语气克制"
            disabled={isLoading}
            className="w-full"
          />
          <p className="mt-1 text-xs text-muted-foreground">
            写一两个词即可，系统会自动补全为完整 prompt
          </p>
        </div>

        {titles.length > 0 ? (
          <div className="grid grid-cols-2 gap-2">
            {titles.map((title, i) => (
              <div
                key={i}
                className="group relative rounded-lg border p-3 text-sm hover:border-primary/50 transition-colors cursor-pointer"
                onClick={() => handleCopy(title)}
              >
                {title}
                <Copy className="absolute right-2 top-2 h-3 w-3 opacity-0 group-hover:opacity-60 transition-opacity" />
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center rounded-lg border border-dashed py-6 text-sm text-muted-foreground">
            点击"生成"获取标题建议
          </div>
        )}
      </CardContent>
    </Card>
  );
}
