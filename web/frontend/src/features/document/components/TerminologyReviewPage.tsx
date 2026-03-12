import { useMemo, useState } from 'react';
import { AlertTriangle, ArrowLeft, CheckCircle2, Languages, Sparkles } from 'lucide-react';
import { Button } from '../../../components/ui';
import type {
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

const reasonLabels: Record<string, string> = {
  title: '标题/小标题命中',
  high_frequency: '全文高频',
  ambiguous: '存在歧义或多种译法',
};

export function TerminologyReviewPage({
  review,
  isSubmitting = false,
  onSubmit,
  onCancel,
}: TerminologyReviewPageProps) {
  const [decisions, setDecisions] = useState<Record<string, DecisionState>>(() => {
    const entries = review.sections.flatMap(section =>
      section.candidates.map(candidate => [
        candidate.term,
        {
          action: 'accept' as DecisionAction,
          translation: candidate.suggested_translation,
        },
      ])
    );

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
    term: string,
    next: Partial<DecisionState>
  ) => {
    setDecisions(current => ({
      ...current,
      [term]: {
        ...current[term],
        ...next,
      },
    }));
  };

  const handleSubmit = async () => {
    const payload: TermReviewDecision[] = review.sections.flatMap(section =>
      section.candidates.map(candidate => {
        const decision = decisions[candidate.term];
        return {
          term: candidate.term,
          action: decision.action,
          translation:
            decision.action === 'skip'
              ? undefined
              : (decision.translation || candidate.suggested_translation).trim(),
          first_occurrence: candidate.first_occurrence ?? candidate.related_sections[0]?.section_id,
        };
      })
    );
    await onSubmit(payload);
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-sm text-warning">
            <AlertTriangle className="h-4 w-4" />
            术语预检
          </div>
          <h1 className="text-2xl font-bold text-text-primary">{review.project_title}</h1>
          <p className="mt-2 text-sm text-text-muted">
            正式开始全文四步法翻译前，先确认高优先级新术语。系统只拦截标题命中、高频和明显歧义的术语。
          </p>
        </div>
        <Button variant="secondary" onClick={onCancel} leftIcon={<ArrowLeft className="h-4 w-4" />}>
          暂不翻译
        </Button>
      </div>

      <div className="mb-6 grid gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-border-subtle bg-bg-secondary p-4">
          <div className="text-sm text-text-muted">待确认术语</div>
          <div className="mt-2 text-2xl font-semibold text-text-primary">{review.total_candidates}</div>
        </div>
        <div className="rounded-xl border border-border-subtle bg-bg-secondary p-4">
          <div className="text-sm text-text-muted">采用建议</div>
          <div className="mt-2 text-2xl font-semibold text-success">{stats.accept}</div>
        </div>
        <div className="rounded-xl border border-border-subtle bg-bg-secondary p-4">
          <div className="text-sm text-text-muted">自定义译法</div>
          <div className="mt-2 text-2xl font-semibold text-primary-600">{stats.custom}</div>
        </div>
        <div className="rounded-xl border border-border-subtle bg-bg-secondary p-4">
          <div className="text-sm text-text-muted">先跳过</div>
          <div className="mt-2 text-2xl font-semibold text-warning">{stats.skip}</div>
        </div>
      </div>

      <div className="space-y-6">
        {review.sections.map(section => (
          <section
            key={section.section_id}
            className="rounded-2xl border border-border-subtle bg-bg-secondary p-5"
          >
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-full bg-primary-500/10 p-2 text-primary-600">
                <Languages className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-text-primary">{section.section_title}</h2>
                <p className="text-sm text-text-muted">
                  本章共 {section.candidates.length} 个高优先级新术语候选
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {section.candidates.map(candidate => {
                const decision = decisions[candidate.term];
                return (
                  <div
                    key={candidate.term}
                    className="rounded-xl border border-border-subtle bg-bg-primary p-4"
                  >
                    <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <div className="text-lg font-semibold text-text-primary">{candidate.term}</div>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-text-muted">
                          <span>建议译法：{candidate.suggested_translation || '未提供'}</span>
                          <span>出现次数：{candidate.occurrence_count}</span>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {candidate.reasons.map(reason => (
                          <span
                            key={reason}
                            className="rounded-full bg-warning/10 px-2.5 py-1 text-xs text-warning"
                          >
                            {reasonLabels[reason] || reason}
                          </span>
                        ))}
                      </div>
                    </div>

                    {candidate.contexts.length > 0 && (
                      <div className="mb-3 rounded-lg bg-bg-secondary px-3 py-2 text-sm text-text-secondary">
                        <div className="mb-1 font-medium text-text-primary">上下文</div>
                        {candidate.contexts.map(context => (
                          <p key={context} className="line-clamp-2">
                            {context}
                          </p>
                        ))}
                      </div>
                    )}

                    {candidate.similar_terms.length > 0 && (
                      <div className="mb-4">
                        <div className="mb-2 flex items-center gap-2 text-sm font-medium text-text-primary">
                          <Sparkles className="h-4 w-4 text-primary-500" />
                          相似术语推荐
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {candidate.similar_terms.map(term => (
                            <button
                              key={`${candidate.term}-${term.original}`}
                              type="button"
                              onClick={() =>
                                updateDecision(candidate.term, {
                                  action: 'custom',
                                  translation: term.translation || '',
                                })
                              }
                              className="rounded-lg border border-border-subtle px-3 py-2 text-left text-xs hover:border-primary-400 hover:bg-primary-500/5"
                            >
                              <div className="font-medium text-text-primary">
                                {term.original} → {term.translation || '保留原文'}
                              </div>
                              {term.note ? (
                                <div className="mt-1 text-text-muted">
                                  词义说明：{term.note}
                                </div>
                              ) : null}
                              <div className="mt-1 text-text-muted">
                                {term.scope === 'global' ? '全局术语' : '项目术语'} · 相似度 {term.similarity}
                              </div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="grid gap-3 md:grid-cols-3">
                      <button
                        type="button"
                        onClick={() =>
                          updateDecision(candidate.term, {
                            action: 'accept',
                            translation: candidate.suggested_translation,
                          })
                        }
                        className={`rounded-xl border px-4 py-3 text-left transition-colors ${
                          decision.action === 'accept'
                            ? 'border-success bg-success/10'
                            : 'border-border-subtle hover:border-success/50'
                        }`}
                      >
                        <div className="mb-1 flex items-center gap-2 font-medium text-text-primary">
                          <CheckCircle2 className="h-4 w-4 text-success" />
                          采用建议
                        </div>
                        <div className="text-sm text-text-muted">
                          {candidate.suggested_translation || '使用系统建议译法'}
                        </div>
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          updateDecision(candidate.term, {
                            action: 'custom',
                            translation: decision.translation || candidate.suggested_translation,
                          })
                        }
                        className={`rounded-xl border px-4 py-3 text-left transition-colors ${
                          decision.action === 'custom'
                            ? 'border-primary-500 bg-primary-500/10'
                            : 'border-border-subtle hover:border-primary-500/50'
                        }`}
                      >
                        <div className="mb-1 font-medium text-text-primary">自定义译法</div>
                        <input
                          value={decision.translation}
                          onChange={event =>
                            updateDecision(candidate.term, {
                              action: 'custom',
                              translation: event.target.value,
                            })
                          }
                          placeholder="输入你的项目术语译法"
                          className="mt-2 w-full rounded-lg border border-border-subtle bg-bg-primary px-3 py-2 text-sm text-text-primary outline-none focus:border-primary-500"
                        />
                      </button>

                      <button
                        type="button"
                        onClick={() =>
                          updateDecision(candidate.term, {
                            action: 'skip',
                            translation: candidate.suggested_translation,
                          })
                        }
                        className={`rounded-xl border px-4 py-3 text-left transition-colors ${
                          decision.action === 'skip'
                            ? 'border-warning bg-warning/10'
                            : 'border-border-subtle hover:border-warning/50'
                        }`}
                      >
                        <div className="mb-1 font-medium text-text-primary">先跳过</div>
                        <div className="text-sm text-text-muted">
                          本次翻译先沿用系统建议，但不写入项目术语库。
                        </div>
                      </button>
                    </div>

                    {candidate.related_sections.length > 1 && (
                      <div className="mt-3 flex items-center gap-2 text-xs text-text-muted">
                        <ArrowLeft className="h-3.5 w-3.5 rotate-180" />
                        后续还会出现在：
                        {candidate.related_sections.slice(1).map(sectionItem => sectionItem.section_title).join('、')}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        ))}
      </div>

      <div className="sticky bottom-0 mt-6 flex items-center justify-between rounded-2xl border border-border-subtle bg-bg-secondary/95 px-5 py-4 backdrop-blur">
        <div className="text-sm text-text-muted">
          确认结果会优先写入项目术语库，后续你可以在术语管理页里再提升到全局。
        </div>
        <div className="flex gap-3">
          <Button variant="secondary" onClick={onCancel}>
            取消
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            isLoading={isSubmitting}
            disabled={hasInvalidCustom}
          >
            保存术语并开始全文翻译
          </Button>
        </div>
      </div>
    </div>
  );
}
