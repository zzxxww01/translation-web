import { useState, type ReactNode } from 'react';
import { ExternalLink, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { isCookieError, type SubstackArticle } from '@/features/substack/api';
import { CookieForm } from '@/features/substack/components/CookieForm';
import { ARTICLE_HARNESSES, loadAgentChoice, saveAgentChoice, type AgentChoice } from '../lib/agentChoice';
import { importAndTranslate } from '../lib/importFlow';
import { AgentChoiceFields } from './AgentCards';

const longDate = new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' });

interface ArticlePreviewProps {
  article: SubstackArticle;
  onImported: (projectId: string) => void;
}

export function ArticlePreview({ article, onImported }: ArticlePreviewProps) {
  const queryClient = useQueryClient();
  const [web, setWeb] = useState(true);
  const [useAgent, setUseAgent] = useState(true);
  const [choice, setChoice] = useState<AgentChoice>(() => loadAgentChoice());
  const [busy, setBusy] = useState(false);
  const [needCookie, setNeedCookie] = useState(false);
  const date = Date.parse(article.post_date);

  const start = async () => {
    setBusy(true);
    try {
      const projectId = await importAndTranslate(article, { web, agent: useAgent ? choice : null });
      if (useAgent) saveAgentChoice(choice);
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
            <div className="mt-2 space-y-1">
              <Check checked={web} onChange={setWeb} label="网页版" note="网站自己的翻译流程" disabled={busy} />
              <Check checked={useAgent} onChange={setUseAgent} label="Agent" note="在服务器上跑，关掉页面也不会停" disabled={busy}>
                {useAgent && (
                  <div className="mt-2.5">
                    <AgentChoiceFields options={ARTICLE_HARNESSES.map(item => item.id)} value={choice} onChange={setChoice} disabled={busy} />
                  </div>
                )}
              </Check>
            </div>
            <Button className="mt-4 w-full" onClick={start} disabled={busy}>
              {busy ? <><Loader2 className="animate-spin" /> 导入中…</> : web || useAgent ? '导入并翻译' : '导入'}
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

function Check({ checked, onChange, label, note, disabled, children }: {
  checked: boolean; onChange: (value: boolean) => void; label: string; note: string; disabled: boolean; children?: ReactNode;
}) {
  return (
    <div className="rounded-lg px-2 py-2">
      <label className="flex cursor-pointer items-start gap-2.5">
        <input type="checkbox" checked={checked} disabled={disabled} onChange={event => onChange(event.target.checked)}
          className="mt-1 h-4 w-4 accent-[var(--color-primary-500)]" />
        <span className="text-sm text-text-primary">
          {label}
          <span className="block text-xs text-text-muted">{note}</span>
        </span>
      </label>
      {children && <div className="pl-[26px]">{children}</div>}
    </div>
  );
}
