import { useState } from 'react';
import { toast } from 'sonner';
import { useTranslateText } from '../hooks';
import { Button } from '@/components/ui/Button';
import { PANE, PANE_FOOTER, PANE_HEADER, PANE_TEXTAREA } from '@/shared/ui/pane';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ArrowRightLeft, Copy, Languages, RotateCw } from 'lucide-react';
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
    <div className="grid min-w-0 gap-4 md:grid-cols-2">
      <section className={PANE} aria-labelledby="translator-source-label">
        <header className={PANE_HEADER}>
          <label id="translator-source-label" className="text-[13px] font-semibold text-text-secondary">原文</label>
          <Select value={sourceLang} onValueChange={setSourceLang}>
            <SelectTrigger className="h-7 w-auto gap-1 rounded-full border-transparent bg-bg-inset px-3 text-xs hover:border-transparent" aria-label="原文语言">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">自动检测</SelectItem>
              <SelectItem value="en">英语</SelectItem>
              <SelectItem value="zh">中文</SelectItem>
            </SelectContent>
          </Select>
        </header>
        <Textarea
          value={source}
          onChange={(e) => setSource(e.target.value)}
          placeholder="输入要翻译的文本…"
          aria-labelledby="translator-source-label"
          className={PANE_TEXTAREA}
        />
        <footer className={PANE_FOOTER}>
          <Button variant="ghost" size="sm" onClick={handleSwap} title="交换语言和内容">
            <ArrowRightLeft />
            交换
          </Button>
          <Button size="sm" className="h-9 min-w-24" onClick={handleTranslate} disabled={!source.trim() || translateMutation.isPending}>
            {translateMutation.isPending ? <RotateCw className="animate-spin" /> : <Languages />}
            翻译
          </Button>
        </footer>
      </section>

      <section className={PANE} aria-labelledby="translator-target-label">
        <header className={PANE_HEADER}>
          <label id="translator-target-label" className="text-[13px] font-semibold text-text-secondary">
            译文 · {targetLang === 'zh' ? '中文' : '英语'}
          </label>
        </header>
        <Textarea
          value={target}
          readOnly
          placeholder="翻译结果会出现在这里"
          aria-labelledby="translator-target-label"
          aria-live="polite"
          className={`${PANE_TEXTAREA} bg-paper-primary`}
        />
        <footer className={`${PANE_FOOTER} justify-end`}>
          <Button variant="outline" size="sm" className="h-9" onClick={handleCopy} disabled={!target}>
            <Copy />
            复制译文
          </Button>
        </footer>
      </section>
    </div>
  );
}
