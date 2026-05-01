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
    const result = await translateMutation.mutateAsync({
      text: source,
      source_lang: sourceLang,
      target_lang: targetLang,
    });
    setTarget(result.translation);
  };

  const handleCopy = async () => {
    if (target) {
      const ok = await copyToClipboard(target);
      if (ok) toast.success('已复制到剪贴板');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'row', gap: '1rem', width: '100%' }}>
      {/* Source */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">原文</label>
          <Select value={sourceLang} onValueChange={setSourceLang}>
            <SelectTrigger className="w-28 h-8">
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
          className="min-h-[500px] resize-y"
        />
      </div>

      {/* Controls */}
      <div className="flex flex-col items-center justify-center gap-3 py-8">
        <Button variant="outline" size="icon" onClick={handleSwap} title="交换语言">
          <ArrowRightLeft className="h-4 w-4" />
        </Button>
        <Button
          onClick={handleTranslate}
          disabled={!source.trim() || translateMutation.isPending}
        >
          {translateMutation.isPending ? <RotateCw className="h-4 w-4 animate-spin" /> : <RotateCw className="h-4 w-4" />}
          翻译
        </Button>
      </div>

      {/* Target */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium">译文</label>
        </div>
        <Textarea
          value={target}
          readOnly
          placeholder="翻译结果..."
          className="min-h-[500px] resize-y"
        />
        <Button variant="outline" className="w-full" onClick={handleCopy} disabled={!target}>
          <Copy className="h-4 w-4" />
          复制译文
        </Button>
      </div>
    </div>
  );
}
