import { useState } from 'react';
import { ExternalLink, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { isCookieError, type SubstackArticle } from '@/features/substack/api';
import { CookieForm } from '@/features/substack/components/CookieForm';
import { importAndTranslate, type SecondChoice } from '../lib/importFlow';
import { SECOND_MODELS } from '../lib/tracks';

const longDate = new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });

interface ArticlePreviewProps {
  article: SubstackArticle;
  onImported: (projectId: string) => void;
}

export function ArticlePreview({ article, onImported }: ArticlePreviewProps) {
  const queryClient = useQueryClient();
  const [second, setSecond] = useState<SecondChoice>(article.is_paid ? 'model' : 'claude');
  const [modelIndex, setModelIndex] = useState(0);
  const [busy, setBusy] = useState(false);
  const [needCookie, setNeedCookie] = useState(false);
  const date = Date.parse(article.post_date);

  const start = async () => {
    setBusy(true);
    try {
      const projectId = await importAndTranslate(article, second, SECOND_MODELS[modelIndex]);
      await queryClient.invalidateQueries({ queryKey: ['articles'] });
      onImported(projectId);
    } catch (error) {
      if (isCookieError(error)) setNeedCookie(true);
      else toast.error(error instanceof Error ? error.message : '导入失败');
    } finally {
      setBusy(false);
    }
  };

  const choice = (value: SecondChoice, label: string, note?: string) => (
    <label className={cn('flex cursor-pointer items-start gap-2 rounded-md px-2 py-1.5', second === value && 'bg-white')}>
      <input type="radio" name="second" checked={second === value} onChange={() => setSecond(value)} className="mt-1 accent-[var(--color-primary-500)]" />
      <span className="text-sm text-text-primary">
        {label}
        {note && <span className="block text-xs text-text-muted">{note}</span>}
      </span>
    </label>
  );

  return (
    <div className="mx-auto w-full max-w-2xl px-5 py-8 sm:px-8 sm:py-12">
      <p className="text-xs text-text-muted">
        {Number.isFinite(date) ? longDate.format(date) : ''}
        {article.is_paid && ' · 付费'}
        {article.wordcount ? ` · ${article.wordcount} 词` : ''}
      </p>
      <h1 className="mt-3 text-[26px] leading-snug text-text-primary [font-family:var(--font-display)]">{article.zh_title || article.title}</h1>
      {article.zh_title && <p className="mt-1 text-base text-text-secondary">{article.title}</p>}
      {article.subtitle && <p className="mt-3 text-sm leading-relaxed text-text-muted">{article.subtitle}</p>}
      {article.cover_image && <img src={article.cover_image} alt="" className="mt-5 max-h-64 w-full rounded-lg border border-border-subtle object-cover" />}
      {article.zh_summary && <p className="mt-5 text-[15px] leading-[1.8] text-text-primary">{article.zh_summary}</p>}
      <a href={article.url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-sm text-primary-700 hover:underline">
        看原文 <ExternalLink className="h-3.5 w-3.5" />
      </a>

      <div className="mt-8 rounded-xl border border-border-subtle bg-bg-tertiary/60 p-4">
        {needCookie ? (
          <CookieForm reason="这是付费文章，要先填订阅 cookie" onSaved={() => { setNeedCookie(false); void start(); }} onCancel={() => setNeedCookie(false)} />
        ) : (
          <>
            <p className="text-sm font-medium text-text-primary">导入后同时翻两版，在三栏里对照</p>
            <p className="mt-1 text-xs text-text-muted">译本 1 是网页版（默认模型）。两路都在服务器上跑，关掉页面也不会停。</p>
            <div className="mt-3 space-y-0.5">
              <p className="px-2 text-xs text-text-muted">译本 2</p>
              {choice('model', '换个模型再翻一版', '付费文章也能用')}
              {second === 'model' && (
                <div className="flex flex-wrap gap-1.5 pb-1 pl-8">
                  {SECOND_MODELS.map((option, index) => (
                    <button
                      key={option.model}
                      type="button"
                      onClick={() => setModelIndex(index)}
                      aria-pressed={modelIndex === index}
                      className={cn('rounded-full border px-2.5 py-0.5 text-xs', modelIndex === index ? 'border-primary-300 bg-primary-50 text-primary-700' : 'border-border-subtle bg-white text-text-secondary')}
                    >
                      {option.label}{option.note && ` · ${option.note}`}
                    </button>
                  ))}
                </div>
              )}
              {choice('claude', '交给 Claude（four-step-translate）', article.is_paid ? '付费文章 Claude 通常不肯全文翻译，只给导读' : undefined)}
              {choice('none', '先不要')}
            </div>
            <Button className="mt-4 w-full" onClick={start} disabled={busy}>
              {busy ? <><Loader2 className="animate-spin" /> 导入中…</> : '导入并翻译'}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
