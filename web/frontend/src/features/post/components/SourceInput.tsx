import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/Button';
import { Loader2, Send, Trash2 } from 'lucide-react';
import { getCharCount } from '@/shared/utils';
import { POST_CONTENT_MAX_LENGTH } from '../types';

interface SourceInputProps {
  value: string;
  onChange: (value: string) => void;
  onTranslate: () => void;
  onClear: () => void;
  isLoading: boolean;
  isTranslating: boolean;
  canClear: boolean;
}

export function SourceInput({ value, onChange, onTranslate, onClear, isLoading, isTranslating, canClear }: SourceInputProps) {
  const charCount = getCharCount(value);

  return (
    <div className="flex min-w-0 flex-col">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">原文</h3>
        <span className="text-xs text-muted-foreground">
          {charCount.toLocaleString()}/{POST_CONTENT_MAX_LENGTH.toLocaleString()} 字符
        </span>
      </div>
      <Textarea
        id="postSourceInput"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        maxLength={POST_CONTENT_MAX_LENGTH}
        aria-label="帖子原文"
        placeholder="原文..."
        className="min-h-[42svh] resize-y sm:min-h-[320px] lg:min-h-[560px] lg:max-h-[calc(100svh-240px)]"
      />
      <div className="mt-4 flex items-center justify-between gap-3">
        <Button type="button" variant="outline" size="sm" className="h-10 px-4 sm:h-9" onClick={onClear} disabled={isLoading || !canClear}>
          <Trash2 className="h-4 w-4" /> 清空
        </Button>
        <Button
          type="button"
          onClick={onTranslate}
          disabled={!value.trim() || isLoading}
          size="sm"
          className="h-11 min-w-28 rounded-full px-5 shadow-md hover:shadow-lg sm:h-10 sm:min-w-10 sm:p-0"
          title="翻译 (Ctrl+Enter)"
          aria-label={isTranslating ? '正在翻译帖子' : '翻译帖子'}
        >
          {isTranslating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          <span className="sm:hidden">{isTranslating ? '翻译中' : '翻译'}</span>
        </Button>
      </div>
    </div>
  );
}
