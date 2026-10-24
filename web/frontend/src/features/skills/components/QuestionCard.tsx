import { useState } from 'react';
import { HelpCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { skillsApi } from '../api';
import type { Answers, Question } from '../types';
import { AssistantText } from './ChatItems';

interface QuestionCardProps {
  runId: string;
  qid: string;
  questions: Question[];
  answer?: { answers?: Answers; response?: string };
  pending: boolean;
}

function answerText(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value.join('、') : value ?? '';
}

/** Claude 用 AskUserQuestion 提的问题。选项之外总能写自己的答案（键用问题原文，值用自填文字）。 */
export function QuestionCard({ runId, qid, questions, answer, pending }: QuestionCardProps) {
  const [picked, setPicked] = useState<Record<string, string[]>>({});
  const [custom, setCustom] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  if (!pending) {
    return (
      <div className="rounded-lg border border-border-subtle bg-bg-secondary px-4 py-3 text-sm">
        {questions.map(q => (
          <div key={q.question} className="flex flex-wrap gap-x-2 text-text-secondary">
            <span>{q.question}</span>
            <span className="font-medium text-text-primary">
              {answer?.answers ? answerText(answer.answers[q.question]) || '—' : answer?.response ? '（见下方回复）' : '已失效'}
            </span>
          </div>
        ))}
        {answer?.response && <p className="mt-1 whitespace-pre-wrap text-text-primary">{answer.response}</p>}
      </div>
    );
  }

  const valueFor = (q: Question): string | string[] | null => {
    const text = custom[q.question]?.trim();
    const chosen = picked[q.question] ?? [];
    if (q.multiSelect) {
      const all = text ? [...chosen, text] : chosen;
      return all.length ? all : null;
    }
    return text || chosen[0] || null;
  };
  const values = questions.map(valueFor);
  const complete = values.every(v => v !== null);

  const toggle = (q: Question, label: string) => {
    setPicked(prev => {
      const current = prev[q.question] ?? [];
      if (!q.multiSelect) return { ...prev, [q.question]: [label] };
      return {
        ...prev,
        [q.question]: current.includes(label) ? current.filter(l => l !== label) : [...current, label],
      };
    });
    if (!q.multiSelect) setCustom(prev => ({ ...prev, [q.question]: '' }));
  };

  const submit = async () => {
    if (!complete) return;
    const answers: Answers = {};
    questions.forEach((q, i) => {
      answers[q.question] = values[i] as string | string[];
    });
    setSubmitting(true);
    try {
      await skillsApi.answer(runId, qid, { answers });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '提交失败');
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50/60 px-4 py-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-medium text-amber-800">
        <HelpCircle className="h-4 w-4" /> 需要你确认
      </div>
      <div className="space-y-4">
        {questions.map(q => (
          <div key={q.question}>
            <div className="mb-2 text-sm text-text-primary">
              {(q.header || q.multiSelect) && (
                <div className="mb-1 flex items-center gap-2">
                  {q.header && <span className="rounded bg-white px-1.5 py-0.5 text-xs text-text-secondary">{q.header}</span>}
                  {q.multiSelect && <span className="text-xs text-text-muted">可多选</span>}
                </div>
              )}
              {/* 问题里偶尔会带表格或列表，按 Markdown 渲染 */}
              <AssistantText text={q.question} />
            </div>
            <div className="flex flex-wrap gap-2">
              {q.options.map(option => {
                const selected = (picked[q.question] ?? []).includes(option.label);
                return (
                  <button
                    key={option.label}
                    type="button"
                    onClick={() => toggle(q, option.label)}
                    title={option.description}
                    className={cn(
                      'rounded-md border px-3 py-1.5 text-left text-sm transition-colors',
                      selected ? 'border-primary-400 bg-white text-primary-700' : 'border-border bg-white text-text-primary hover:border-primary-200'
                    )}
                  >
                    {option.label}
                    {option.description && <span className="block text-xs text-text-muted">{option.description}</span>}
                  </button>
                );
              })}
            </div>
            <Input
              className="mt-2"
              placeholder="都不合适？写你的答案"
              value={custom[q.question] ?? ''}
              onChange={event => {
                const text = event.target.value;
                setCustom(prev => ({ ...prev, [q.question]: text }));
                if (!q.multiSelect && text) setPicked(prev => ({ ...prev, [q.question]: [] }));
              }}
            />
          </div>
        ))}
      </div>
      <div className="mt-4 flex justify-end">
        <Button onClick={submit} disabled={!complete || submitting}>
          {submitting ? '提交中…' : '提交回答'}
        </Button>
      </div>
    </div>
  );
}
