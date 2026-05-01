import { useMemo, useState } from 'react';
import { ArrowLeft, Check, ChevronDown, ChevronRight, X } from 'lucide-react';
import { Button } from '@/components/ui/button-extended';
import type {
  TermReviewCandidate,
  TermReviewDecision,
  TermReviewPayload,
} from '../../confirmation/types';

interface TerminologyReviewPageProps {
  review: TermReviewPayload;
  isSubmitting?: boolean;
  onSubmit: (decisions: TermReviewDecision[]) => Promise<void> | void;
  onCancel: () => void;
}

type DecisionAction = 'accept' | 'custom' | 'skip';

interface DecisionState {
  action: DecisionAction;
  translation: string;
}

interface FlatCandidate extends TermReviewCandidate {
  section_id: string;
  section_title: string;
}

const reasonLabels: Record<string, string> = {
  title: '标题',
  high_frequency: '高频',
  ambiguous: '多译法',
  existing_conflict: '与术语表冲突',
  project_global_conflict: '项目/全局冲突',
};

function candidateKey(candidate: FlatCandidate) {
  return `${candidate.section_id}::${candidate.term}`;
}

function getTranslationOptions(candidate: FlatCandidate) {
  const seen = new Set<string>();
  const options: Array<{ translation: string; count?: number; source: 'suggested' | 'similar' }> = [];

  for (const item of candidate.suggested_translations ?? []) {
    const translation = item.translation.trim();
    if (!translation || seen.has(translation)) {
      continue;
    }
    seen.add(translation);
    options.push({ translation, count: item.count, source: 'suggested' });
  }

  const fallback = candidate.suggested_translation?.trim();
  if (fallback && !seen.has(fallback)) {
    seen.add(fallback);
    options.unshift({ translation: fallback, source: 'suggested' });
  }

  for (const item of candidate.similar_terms.slice(0, 2)) {
    const translation = (item.translation || item.original).trim();
    if (!translation || seen.has(translation)) {
      continue;
    }
    seen.add(translation);
    options.push({ translation, source: 'similar' });
  }

  return options;
}

export function TerminologyReviewPage({
  review,
  isSubmitting = false,
  onSubmit,
  onCancel,
}: TerminologyReviewPageProps) {
  const candidates = useMemo<FlatCandidate[]>(
    () =>
      review.sections.flatMap(section =>
        section.candidates.map(candidate => ({
          ...candidate,
          section_id: section.section_id,
          section_title: section.section_title,
        }))
      ),
    [review.sections]
  );

  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [decisions, setDecisions] = useState<Record<string, DecisionState>>(() => {
    const entries = candidates.map(candidate => [
      candidateKey(candidate),
      {
        action: 'accept' as DecisionAction,
        translation: candidate.suggested_translation || candidate.term,
      },
    ]);

    return Object.fromEntries(entries);
  });

  const stats = useMemo(() => {
    const values = Object.values(decisions);
    return {
      accept: values.filter(item => item.action === 'accept').length,
      custom: values.filter(item => item.action === 'custom').length,
      skip: values.filter(item => item.action === 'skip').length,
    };
  }, [decisions]);

  const hasInvalidCustom = useMemo(
    () =>
      Object.values(decisions).some(
        item => item.action === 'custom' && !item.translation.trim()
      ),
    [decisions]
  );

  const updateDecision = (
    key: string,
    next: Partial<DecisionState>
  ) => {
    setDecisions(current => ({
      ...current,
      [key]: {
        ...current[key],
        ...next,
      },
    }));
  };

  const handleSubmit = async () => {
    const payload: TermReviewDecision[] = candidates.map(candidate => {
      const key = candidateKey(candidate);
      const decision = decisions[key];
      return {
        term: candidate.term,
        action: decision.action,
        translation:
          decision.action === 'skip'
            ? undefined
            : (decision.translation || candidate.suggested_translation || candidate.term).trim(),
        first_occurrence: candidate.first_occurrence ?? candidate.section_id,
      };
    });
    await onSubmit(payload);
  };

  return (
    <div className="mx-auto max-w-6xl px-5 py-5">
      <div className="mb-4 flex items-center justify-between gap-4 border-b border-border-subtle pb-4">
        <div className="min-w-0">
          <div className="text-xs font-medium uppercase text-text-muted">术语预检</div>
          <h1 className="truncate text-xl font-semibold text-text-primary">
            {review.project_title}
          </h1>
        </div>
        <Button variant="outline" onClick={onCancel} leftIcon={<ArrowLeft className="h-4 w-4" />}>
          返回
        </Button>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-3 text-sm text-text-muted">
        <span>共 {review.total_candidates} 个</span>
        <span>采用 {stats.accept}</span>
        <span>自定义 {stats.custom}</span>
        <span>跳过 {stats.skip}</span>
      </div>

      <div className="overflow-hidden border-y border-border-subtle">
        <div className="grid grid-cols-[minmax(130px,1fr)_minmax(220px,1.4fr)_minmax(190px,1fr)_88px_36px] gap-3 border-b border-border-subtle bg-bg-secondary px-3 py-2 text-xs font-medium uppercase text-text-muted max-lg:hidden">
          <div>原词</div>
          <div>选择译法</div>
          <div>自定义</div>
          <div>动作</div>
          <div />
        </div>

        {candidates.map(candidate => {
          const key = candidateKey(candidate);
          const decision = decisions[key];
          const options = getTranslationOptions(candidate);
          const isExpanded = Boolean(expanded[key]);

          return (
            <div key={key} className="border-b border-border-subtle last:border-b-0">
              <div className="grid items-center gap-3 px-3 py-3 lg:grid-cols-[minmax(130px,1fr)_minmax(220px,1.4fr)_minmax(190px,1fr)_88px_36px]">
                <div className="min-w-0">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="truncate text-base font-semibold text-text-primary">
                      {candidate.term}
                    </span>
                    <span className="shrink-0 text-xs text-text-muted">
                      {candidate.occurrence_count} 次
                    </span>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {candidate.reasons.map(reason => (
                      <span
                        key={reason}
                        className="rounded border border-border-subtle px-1.5 py-0.5 text-[11px] text-text-muted"
                      >
                        {reasonLabels[reason] || reason}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  {options.length > 0 ? (
                    options.map(option => {
                      const selected =
                        decision.action !== 'skip' && decision.translation === option.translation;
                      return (
                        <button
                          key={`${key}-${option.translation}`}
                          type="button"
                          onClick={() =>
                            updateDecision(key, {
                              action: option.translation === candidate.suggested_translation ? 'accept' : 'custom',
                              translation: option.translation,
                            })
                          }
                          className={`min-h-8 max-w-full rounded border px-2.5 py-1 text-left text-sm transition-colors ${
                            selected
                              ? 'border-primary-500 bg-primary-500/10 text-text-primary'
                              : 'border-border-subtle text-text-secondary hover:border-primary-400'
                          }`}
                          title={option.translation}
                        >
                          <span className="inline-flex max-w-[260px] items-center gap-1 truncate">
                            {selected ? <Check className="h-3.5 w-3.5 shrink-0" /> : null}
                            <span className="truncate">{option.translation}</span>
                            {option.count ? (
                              <span className="shrink-0 text-xs text-text-muted">x{option.count}</span>
                            ) : null}
                          </span>
                        </button>
                      );
                    })
                  ) : (
                    <span className="text-sm text-text-muted">无建议译法</span>
                  )}
                </div>

                <input
                  value={decision.translation}
                  onChange={event =>
                    updateDecision(key, {
                      action: 'custom',
                      translation: event.target.value,
                    })
                  }
                  placeholder="输入译法"
                  className="h-9 w-full rounded border border-border-subtle bg-bg-primary px-2.5 text-sm text-text-primary outline-none focus:border-primary-500"
                />

                <button
                  type="button"
                  onClick={() =>
                    updateDecision(key, {
                      action: decision.action === 'skip' ? 'accept' : 'skip',
                      translation: candidate.suggested_translation || candidate.term,
                    })
                  }
                  className={`inline-flex h-9 items-center justify-center gap-1 rounded border px-2 text-sm transition-colors ${
                    decision.action === 'skip'
                      ? 'border-warning bg-warning/10 text-warning'
                      : 'border-border-subtle text-text-secondary hover:border-warning'
                  }`}
                >
                  {decision.action === 'skip' ? <X className="h-4 w-4" /> : null}
                  {decision.action === 'skip' ? '已跳过' : '跳过'}
                </button>

                <button
                  type="button"
                  onClick={() => setExpanded(current => ({ ...current, [key]: !current[key] }))}
                  className="flex h-9 w-9 items-center justify-center rounded border border-border-subtle text-text-muted hover:text-text-primary"
                  aria-label={isExpanded ? '收起上下文' : '展开上下文'}
                >
                  {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </button>
              </div>

              {isExpanded ? (
                <div className="bg-bg-secondary px-3 pb-3 pt-1 text-sm text-text-secondary">
                  <div className="grid gap-3 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
                    <div>
                      <div className="mb-1 text-xs font-medium uppercase text-text-muted">上下文</div>
                      <div className="space-y-1">
                        {(candidate.contexts.length > 0 ? candidate.contexts : ['暂无上下文']).slice(0, 3).map(context => (
                          <p key={context} className="leading-relaxed">
                            {context}
                          </p>
                        ))}
                      </div>
                    </div>
                    <div>
                      <div className="mb-1 text-xs font-medium uppercase text-text-muted">来源与相似词</div>
                      <p>
                        首次出现：{candidate.related_sections[0]?.section_title || candidate.section_title}
                      </p>
                      {candidate.similar_terms.length > 0 ? (
                        <p className="mt-1">
                          相似：{candidate.similar_terms.slice(0, 3).map(item => `${item.original} → ${item.translation || item.original}${item.scope ? `（${item.scope}）` : ''}`).join('；')}
                        </p>
                      ) : (
                        <p className="mt-1 text-text-muted">无相似术语</p>
                      )}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="sticky bottom-0 mt-4 flex items-center justify-between gap-3 border border-border-subtle bg-white px-4 py-3 shadow-sm">
        <div className="text-sm text-text-muted">
          保存后写入项目术语库，并继续全文翻译。
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onCancel}>
            取消
          </Button>
          <Button
            variant="default"
            onClick={handleSubmit}
            isLoading={isSubmitting}
            disabled={hasInvalidCustom}
          >
            保存并开始
          </Button>
        </div>
      </div>
    </div>
  );
}
