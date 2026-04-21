import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Send, Trash2 } from 'lucide-react';
import { getCharCount } from '@/shared/utils';

interface SourceInputProps {
  value: string;
  onChange: (value: string) => void;
  onTranslate: () => void;
  onClear: () => void;
  isLoading: boolean;
  canClear: boolean;
}

export function SourceInput({ value, onChange, onTranslate, onClear, isLoading, canClear }: SourceInputProps) {
  const charCount = getCharCount(value);

  return (
    <div className="flex flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">原文</h3>
        <span className="text-xs text-muted-foreground">{charCount} 字符</span>
      </div>
      <Textarea
        id="postSourceInput"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="原文..."
        className="flex-1 resize-y min-h-[280px] max-h-[400px]"
      />
      <div className="mt-4 flex items-center justify-between">
        <Button variant="outline" size="sm" onClick={onClear} disabled={isLoading || !canClear}>
          <Trash2 className="h-4 w-4" /> 清空
        </Button>
        <Button
          onClick={onTranslate}
          disabled={!value.trim() || isLoading}
          size="sm"
          className="h-9 w-9 p-0 rounded-full shadow-md hover:shadow-lg"
          title="翻译 (Ctrl+Enter)"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
