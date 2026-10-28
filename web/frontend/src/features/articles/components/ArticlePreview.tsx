import { useState } from 'react';
import { ExternalLink, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { isCookieError, type SubstackArticle } from '@/features/substack/api';
import { CookieForm } from '@/features/substack/components/CookieForm';
import type { Harness } from '@/features/skills/harness';
import { ARTICLE_HARNESSES } from '../lib/agentChoice';
import { importAndTranslate, runsAgent, type ImportPlan } from '../lib/importFlow';
import { ArticleAgentChoice } from './ArticleAgentChoice';

const PLANS: { id: ImportPlan; label: string; note: string }[] = [
  { id: 'both', label: '两个都翻', note: '网页版出译本 1，Agent 出译本 2，翻完三栏对照' },
  { id: 'web', label: '只翻网页版', note: '网站自己的翻译流程，出译本 1' },
  { id: 'agent', label: '只用 Agent 翻', note: '所选 Agent 跑 four-step-translate，出译本 2' },
  { id: 'import', label: '只导入', note: '先不翻，之后在工作台里再开始' },
];

const longDate = new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });

interface ArticlePreviewProps {
  article: SubstackArticle;
  onImported: (projectId: string) => void;
}

export function ArticlePreview({ article, onImported }: ArticlePreviewProps) {
  const queryClient = useQueryClient();
  const [plan, setPlan] = useState<ImportPlan>('both');
  const [harness, setHarness] = useState<Harness>('codex');
  const [busy, setBusy] = useState(false);
  const [needCookie, setNeedCookie] = useState(false);
  const date = Date.parse(article.post_date);

  const start = async () => {
    setBusy(true);
    try {
      const projectId = await importAndTranslate(article, plan, harness);
      await queryClient.invalidateQueries({ queryKey: ['articles'] });
      onImported(projectId);
    } catch (error) {
      if (isCookieError(error)) setNeedCookie(true);
      else toast.error(error instanceof Error ? error.message : '导入失败');
    } finally {
      setBusy(false);
    }
  };

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
            <p className="text-sm font-medium text-text-primary">导入后怎么翻</p>
            <p className="mt-1 text-xs leading-relaxed text-text-muted">
              译本 1 是网页版，译本 2 可选 {ARTICLE_HARNESSES.map(item => item.label).join('、')}。都在服务器上跑，关掉页面也不会停。
            </p>
            <div className="mt-3 space-y-0.5" role="radiogroup" aria-label="导入后怎么翻">
              {PLANS.map(item => (
                <label key={item.id} className={cn('flex cursor-pointer items-start gap-2 rounded-md px-2 py-1.5', plan === item.id && 'bg-white')}>
                  <input type="radio" name="plan" checked={plan === item.id} onChange={() => setPlan(item.id)} className="mt-1 accent-[var(--color-primary-500)]" />
                  <span className="text-sm text-text-primary">
                    {item.label}
                    <span className="block text-xs text-text-muted">{item.note}</span>
                  </span>
                </label>
              ))}
            </div>
            {runsAgent(plan) && (
              <div className="mt-2 flex flex-wrap items-center gap-1.5 px-2">
                <span className="text-xs text-text-muted">Agent 用</span>
                <ArticleAgentChoice value={harness} onChange={setHarness} disabled={busy} />
                {harness === 'claude' && article.is_paid && <span className="text-xs text-warning">付费文章 Claude 通常不肯全文翻译，只给导读</span>}
              </div>
            )}
            <Button className="mt-4 w-full" onClick={start} disabled={busy}>
              {busy ? <><Loader2 className="animate-spin" /> 导入中…</> : plan === 'import' ? '导入' : '导入并翻译'}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
