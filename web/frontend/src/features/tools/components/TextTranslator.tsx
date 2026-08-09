import { useState } from 'react';
import { toast } from 'sonner';
import { useTranslateText } from '../hooks';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ArrowRightLeft, RotateCw, Copy } from 'lucide-react';
import { copyToClipboard } from '@/shared/utils';

export function TextTranslator() {
  const translateMutation = useTranslateText();
  const [source, setSource] = useState('');
  const [target, setTarget] = useState('');
  const [sourceLang, setSourceLang] = useState('auto');

  // 自动确定目标语言
  const targetLang = sourceLang === 'zh' ? 'en' : 'zh';

  const handleSwap = () => {
    setSourceLang(targetLang);
    setSource(target);
    setTarget(source);
  };

  const handleTranslate = async () => {
    if (!source.trim()) return;
    try {
      const result = await translateMutation.mutateAsync({
        text: source,
        source_lang: sourceLang,
        target_lang: targetLang,
      });
      setTarget(result.translation);
    } catch {
      // Mutation hook owns the user-facing error message.
    }
  };

  const handleCopy = async () => {
    if (target) {
      const ok = await copyToClipboard(target);
      if (ok) toast.success('已复制到剪贴板');
    }
  };

  return (
    <div className="grid min-w-0 gap-4 md:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
      <section className="flex min-w-0 flex-col gap-3" aria-labelledby="translator-source-label">
        <div className="flex items-center justify-between">
          <label id="translator-source-label" className="text-sm font-medium">原文</label>
          <Select value={sourceLang} onValueChange={setSourceLang}>
            <SelectTrigger className="h-8 w-28" aria-label="原文语言">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">自动检测</SelectItem>
              <SelectItem value="en">英语</SelectItem>
              <SelectItem value="zh">中文</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Textarea
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="输入要翻译的文本..."
          aria-labelledby="translator-source-label"
          className="min-h-[260px] resize-y md:min-h-[500px]"
        />
      </section>

      <div className="flex items-center justify-center gap-3 md:flex-col md:py-8">
        <Button variant="outline" size="icon" onClick={handleSwap} title="交换语言">
          <ArrowRightLeft className="h-4 w-4" />
          <span className="sr-only">交换语言和内容</span>
        </Button>
        <Button
          onClick={handleTranslate}
          disabled={!source.trim() || translateMutation.isPending}
        >
          {translateMutation.isPending ? <RotateCw className="h-4 w-4 animate-spin" /> : <RotateCw className="h-4 w-4" />}
          翻译
        </Button>
      </div>

      <section className="flex min-w-0 flex-col gap-3" aria-labelledby="translator-target-label">
        <div className="flex items-center justify-between">
          <label id="translator-target-label" className="text-sm font-medium">
            译文 · {targetLang === 'zh' ? '中文' : '英语'}
          </label>
        </div>
        <Textarea
          value={target}
          readOnly
          placeholder="翻译结果..."
          aria-labelledby="translator-target-label"
          aria-live="polite"
          className="min-h-[260px] resize-y md:min-h-[500px]"
        />
        <Button variant="outline" className="w-full" onClick={handleCopy} disabled={!target}>
          <Copy className="h-4 w-4" />
          复制译文
        </Button>
      </section>
    </div>
  );
}
