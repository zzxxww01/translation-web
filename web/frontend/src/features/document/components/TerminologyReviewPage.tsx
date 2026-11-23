import { Fragment, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Clock3 } from 'lucide-react';
import { Button } from '@/components/ui/button-extended';
import { cn } from '@/lib/utils';
import type {
  TermReviewCandidate,
  TermReviewDecision,
  TermReviewPayload,
} from '../../confirmation/types';

interface TerminologyReviewPageProps {
  review: TermReviewPayload;
  isSubmitting?: boolean;
  autoContinueSeconds?: number;
  onSubmit: (decisions: TermReviewDecision[]) => Promise<void> | void;
  onCancel: () => void;
}

interface DecisionState {
  translation: string;
  skip: boolean;
}

/** 为什么要你看这个词：一两个字说清，和出现次数写在同一行小字里 */
const reasonLabels: Record<string, string> = {
  needs_decision: '译法要定',
  title: '标题里有',
  high_frequency: '高频',
  ambiguous: '有多种译法',
};

// 术语原文可能含空格等字符，统一编码后再做 DOM id，供「跳到第一个没填的」定位
const termAnchorId = (term: string) => `term-card-${encodeURIComponent(term)}`;
const termInputId = (term: string) => `term-input-${encodeURIComponent(term)}`;

const escapeRegExp = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** 上下文里把术语标出来，一眼看到它在句子里怎么用 */
function highlight(context: string, term: string): ReactNode {
  if (!term.trim()) return context;
  const parts = context.split(new RegExp(`(${escapeRegExp(term)})`, 'gi'));
  return parts.map((part, index) => index % 2 === 1
    ? <mark key={index} className="rounded-sm bg-primary-100 font-medium text-text-primary">{part}</mark>
    : <Fragment key={index}>{part}</Fragment>);
}

/**
 * 术语确认（2026-11-23 用户：原来的页面看不懂、没信息量）。
 * 一个词一行：左边原文和「出现几次、首次在哪章、为什么要看」，右边直接是译法输入框（预填建议），
 * 下面一句带高亮的原文上下文、术语库里相近的词（点了就用）。不改 = 采用建议，改了 = 自定义，勾「跳过」= 不预设。
 */
export function TerminologyReviewPage({
  review,
  isSubmitting = false,
  autoContinueSeconds = 600,
  onSubmit,
  onCancel,
}: TerminologyReviewPageProps) {
  const candidates = useMemo(
    () => review.sections.flatMap(section => section.candidates.map(candidate => ({ candidate, sectionTitle: section.section_title }))),
    [review.sections],
  );
  const [decisions, setDecisions] = useState<Record<string, DecisionState>>(() =>
    Object.fromEntries(candidates.map(({ candidate }) => [candidate.term, { translation: candidate.suggested_translation, skip: false }]))
  );
  const [autoContinueDeadline] = useState(() => Date.now() + Math.max(0, autoContinueSeconds) * 1000);
  const [clockTime, setClockTime] = useState(() => Date.now());
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const intervalId = window.setInterval(() => setClockTime(Date.now()), 1000);
    return () => window.clearInterval(intervalId);
  }, []);

  const remainingSeconds = Math.max(0, Math.ceil((autoContinueDeadline - clockTime) / 1000));
  const remainingLabel = `${Math.floor(remainingSeconds / 60)}:${String(remainingSeconds % 60).padStart(2, '0')}`;

  // 保留术语顺序，既用于禁用提交，也用于「跳到第一个没填的」
  const invalidTerms = useMemo(
    () => Object.entries(decisions).filter(([, item]) => !item.skip && !item.translation.trim()).map(([term]) => term),
    [decisions]
  );
  const changed = candidates.filter(({ candidate }) => {
    const decision = decisions[candidate.term];
    return decision.skip || decision.translation.trim() !== candidate.suggested_translation;
  }).length;

  const jumpToFirstInvalid = () => {
    const term = invalidTerms[0];
    if (!term) return;
    document.getElementById(termAnchorId(term))?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    document.getElementById(termInputId(term))?.focus();
  };

  const updateDecision = (term: string, next: Partial<DecisionState>) => {
    setDecisions(current => ({ ...current, [term]: { ...current[term], ...next } }));
  };

  const handleSubmit = async () => {
    const payload: TermReviewDecision[] = candidates.map(({ candidate }) => {
      const decision = decisions[candidate.term];
      const translation = decision.translation.trim();
      // 不再用建议译法回填用户清空的输入——那正是用户手动改写的意图；空值在提交前就拦下了。
      const action = decision.skip ? 'skip' : translation === candidate.suggested_translation ? 'accept' : 'custom';
      return {
        term: candidate.term,
        action,
        translation: decision.skip ? undefined : translation,
        first_occurrence: candidate.first_occurrence ?? candidate.related_sections[0]?.section_id,
      };
    });
    setSubmitting(true);
    try {
      await onSubmit(payload);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col">
      <div className="sticky top-0 z-10 flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-border-subtle bg-white/95 px-5 py-3 backdrop-blur">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text-primary">
            {candidates.length} 个术语等你定译法
            {changed > 0 && <span className="ml-2 font-normal text-text-muted">改了 {changed} 个</span>}
          </p>
          <p className="mt-0.5 flex items-center gap-1 text-xs text-text-muted">
            <Clock3 className="h-3.5 w-3.5" />
            {remainingLabel} 后自动按建议译法继续翻译
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={onCancel}>稍后再说</Button>
        <Button size="sm" onClick={handleSubmit} isLoading={isSubmitting || submitting} disabled={invalidTerms.length > 0}>
          确认，继续翻译
        </Button>
        {invalidTerms.length > 0 && (
          <p className="w-full text-xs text-error">
            {invalidTerms.length} 个术语没填译法（不想定就勾「跳过」）
            <button type="button" onClick={jumpToFirstInvalid} className="ml-2 underline underline-offset-2">去填</button>
          </p>
        )}
      </div>

      {review.is_partial && (
        <p className="mx-5 mt-3 rounded-md bg-warning/10 px-3 py-2 text-xs text-warning-text">
          只扫了 {review.scanned_sections ?? '?'} / {review.total_sections ?? '?'} 章，没扫到的章节里可能还有新术语。
        </p>
      )}

      <ul className="divide-y divide-border-subtle">
        {candidates.map(({ candidate, sectionTitle }) => (
          <TermRow
            key={candidate.term}
            candidate={candidate}
            sectionTitle={candidate.related_sections[0]?.section_title || sectionTitle}
            decision={decisions[candidate.term]}
            onChange={next => updateDecision(candidate.term, next)}
          />
        ))}
      </ul>
    </div>
  );
}

function TermRow({ candidate, sectionTitle, decision, onChange }: {
  candidate: TermReviewCandidate;
  sectionTitle: string;
  decision: DecisionState;
  onChange: (next: Partial<DecisionState>) => void;
}) {
  const [allContexts, setAllContexts] = useState(false);
  const missing = !decision.skip && !decision.translation.trim();
  const edited = !decision.skip && decision.translation.trim() !== candidate.suggested_translation;
  const meta = [
    `出现 ${candidate.occurrence_count} 次`,
    sectionTitle && `首次在「${sectionTitle}」`,
    ...candidate.reasons.map(reason => reasonLabels[reason]).filter(Boolean),
  ].filter(Boolean).join(' · ');
  const contexts = allContexts ? candidate.contexts : candidate.contexts.slice(0, 1);
  const similar = candidate.similar_terms.filter(term => term.translation);

  return (
    <li id={termAnchorId(candidate.term)} className={cn('grid gap-x-5 gap-y-2 px-5 py-4 md:grid-cols-[minmax(0,12rem)_minmax(0,1fr)]', decision.skip && 'bg-bg-secondary/60')}>
      <div className="min-w-0">
        <p className={cn('break-words text-[15px] font-semibold text-text-primary', decision.skip && 'text-text-muted')}>{candidate.term}</p>
        <p className="mt-0.5 text-xs leading-5 text-text-muted">{meta}</p>
      </div>

      <div className="min-w-0 space-y-2">
        <div className="flex items-center gap-3">
          <input
            id={termInputId(candidate.term)}
            value={decision.translation}
            disabled={decision.skip}
            onChange={event => onChange({ translation: event.target.value })}
            placeholder="填译法"
            aria-label={`${candidate.term} 的译法`}
            aria-invalid={missing}
            className={cn(
              'h-9 min-w-0 flex-1 rounded-md border bg-white px-3 text-sm text-text-primary outline-none transition-colors focus:border-primary-400 focus:ring-[3px] focus:ring-primary-500/12 disabled:bg-transparent disabled:text-text-disabled',
              missing ? 'border-error' : edited ? 'border-primary-300' : 'border-border'
            )}
          />
          <label className="flex shrink-0 cursor-pointer items-center gap-1.5 text-xs text-text-muted" title="这次不预设译法，也不写进术语表">
            <input type="checkbox" checked={decision.skip} onChange={event => onChange({ skip: event.target.checked })}
              className="h-3.5 w-3.5 accent-[var(--color-primary-500)]" />
            跳过
          </label>
        </div>
        {edited && candidate.suggested_translation && (
          <p className="text-xs text-text-muted">
            建议是「{candidate.suggested_translation}」
            <button type="button" onClick={() => onChange({ translation: candidate.suggested_translation })} className="ml-1.5 text-primary-700 hover:underline">改回</button>
          </p>
        )}

        {contexts.length > 0 && (
          <div className="space-y-1">
            {contexts.map(context => (
              <p key={context} className={cn('text-[13px] leading-relaxed text-text-secondary [font-family:var(--font-source)]', !allContexts && 'line-clamp-2')}>
                {highlight(context, candidate.term)}
              </p>
            ))}
            {candidate.contexts.length > 1 && (
              <button type="button" onClick={() => setAllContexts(open => !open)} className="text-xs text-text-muted hover:text-text-primary">
                {allContexts ? '收起' : `还有 ${candidate.contexts.length - 1} 处原文`}
              </button>
            )}
          </div>
        )}

        {similar.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            <span className="text-text-muted">术语表里相近的：</span>
            {similar.map(term => (
              <button
                key={`${term.scope}-${term.original}`}
                type="button"
                onClick={() => onChange({ translation: term.translation || '', skip: false })}
                title={[term.scope === 'global' ? '全局术语表' : '本文术语表', term.note].filter(Boolean).join('：')}
                className="rounded-md border border-border-subtle bg-white px-2 py-0.5 text-text-secondary hover:border-primary-300 hover:text-primary-700"
              >
                {term.original} → {term.translation}
              </button>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}
