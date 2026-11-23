import { useState, useEffect } from 'react';
import { useConvertTimezone } from '../hooks';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { ChevronRight, RotateCw } from 'lucide-react';
import type { TimezoneConvertResult } from '@/shared/types';
import { PANE, PANE_HEADER } from '@/shared/ui/pane';

// 与后端 src/api/utils/timezone.py 的解析规则一一对应，改那边要同步改这里
const INPUT_FORMATS = [
  { label: '今天 / 明天', examples: '今天下午3点、明天上午9点半、明天 15:30' },
  { label: '月/日[/年]', examples: '1/26 4pm、1/26/26 4:30 pm、1/26 16:00' },
  { label: '年-月-日', examples: '2026-01-26 14:00' },
  { label: '英文月份', examples: 'Jan 26, 2026 4pm' },
];

const WEEKDAY_LABELS: Record<string, string> = {
  Sun: '周日',
  Mon: '周一',
  Tue: '周二',
  Wed: '周三',
  Thu: '周四',
  Fri: '周五',
  Sat: '周六',
};

// C38: 用 Intl.DateTimeFormat 直接按目标时区格式化，避免
// new Date(now.toLocaleString('en-US', { timeZone })) 在不同浏览器下解析不一致的问题。
function formatTimeInZone(now: Date, timeZone: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(now);
}

function formatDateInZone(now: Date, timeZone: string): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    weekday: 'short',
  }).formatToParts(now);

  const lookup = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find(part => part.type === type)?.value ?? '';

  const year = lookup('year');
  const month = lookup('month');
  const day = lookup('day');
  const weekday = WEEKDAY_LABELS[lookup('weekday')] ?? '';

  return `${year}/${month}/${day} ${weekday}`.trim();
}

// 「现在」一栏的一行：左边地名和日期，右边大号时间
function LiveTimeRow({ title, timeZone }: { title: string; timeZone: string }) {
  const [time, setTime] = useState('');
  const [date, setDate] = useState('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      setTime(formatTimeInZone(now, timeZone));
      setDate(formatDateInZone(now, timeZone));
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [timeZone]);

  return (
    <div className="flex items-center justify-between gap-4 px-5 py-5">
      <div className="min-w-0">
        <div className="text-sm font-medium text-text-secondary">{title}</div>
        <div className="mt-1 text-xs tabular-nums text-text-muted">{date}</div>
      </div>
      <div className="text-[28px] font-semibold leading-none tabular-nums text-text-primary sm:text-[32px]" style={{ fontFamily: 'var(--font-display)' }}>
        {time || <Skeleton className="h-8 w-28" />}
      </div>
    </div>
  );
}

const RESULT_ROWS = [
  { label: '北京时间', key: 'beijing' },
  { label: '美东时间', key: 'est' },
  { label: '美中时间', key: 'cst' },
  { label: '美山时间', key: 'mst' },
  { label: '美西时间', key: 'pst' },
] as const;

export function TimezoneConverter() {
  const timezoneMutation = useConvertTimezone();
  const [input, setInput] = useState('');
  const [result, setResult] = useState<TimezoneConvertResult | null>(null);

  const handleConvert = async () => {
    if (!input.trim()) return;
    try {
      const res = await timezoneMutation.mutateAsync({
        input,
        source_timezone: 'auto',
      });
      setResult(res);
    } catch {
      // Mutation hook owns the user-facing error message.
    }
  };

  // 版式和文本翻译一样的两张「纸」：左边现在几点，右边换算；内容少，高度随内容
  return (
    <div className="grid min-w-0 items-start gap-5 md:grid-cols-2">
      <section className={PANE} aria-labelledby="timezone-now-label">
        <header className={PANE_HEADER}>
          <h2 id="timezone-now-label" className="text-[13px] font-semibold text-text-secondary">现在</h2>
        </header>
        <div className="divide-y divide-border-subtle">
          <LiveTimeRow title="北京时间" timeZone="Asia/Shanghai" />
          <LiveTimeRow title="美中时间" timeZone="America/Chicago" />
          <LiveTimeRow title="美西时间" timeZone="America/Los_Angeles" />
        </div>
      </section>

      <section className={PANE} aria-labelledby="timezone-convert-label">
        <header className={PANE_HEADER}>
          <label id="timezone-convert-label" htmlFor="timezone-input" className="text-[13px] font-semibold text-text-secondary">换算一个时间</label>
        </header>
        {/* 输入框和按钮同一行，回车也能换算 */}
        <div className="flex gap-2 border-b border-border-subtle p-3">
          <Input
            id="timezone-input"
            placeholder="例如：今天下午3点、1/26 4pm PT"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void handleConvert();
            }}
            aria-describedby="timezone-input-help"
            className="h-10 min-w-0 flex-1"
          />
          <Button
            onClick={handleConvert}
            disabled={!input.trim() || timezoneMutation.isPending}
            className="h-10 shrink-0"
          >
            <RotateCw className={timezoneMutation.isPending ? 'animate-spin' : undefined} />
            换算
          </Button>
        </div>
        {/* 结果一直占位，没换算时显示「—」；北京时间放最前、最醒目 */}
        <dl className={`divide-y divide-border-subtle ${timezoneMutation.isPending ? 'opacity-60' : ''}`} aria-live="polite">
          {RESULT_ROWS.map((row, i) => (
            <div
              key={row.key}
              className={i === 0
                ? 'flex items-baseline justify-between gap-3 bg-primary-50/50 px-4 py-3'
                : 'flex items-baseline justify-between gap-3 px-4 py-2.5 text-sm'}
            >
              <dt className={i === 0 ? 'text-xs font-medium text-primary-700' : 'text-text-muted'}>{row.label}</dt>
              <dd className={i === 0 ? 'text-lg font-semibold tabular-nums text-text-primary' : 'tabular-nums text-text-primary'}>
                {result?.[row.key] || '—'}
              </dd>
            </div>
          ))}
        </dl>
        <details className="group border-t border-border-subtle bg-bg-tertiary/40 px-4 py-2 text-xs leading-relaxed text-text-muted">
          <summary className="inline-flex cursor-pointer select-none list-none items-center gap-1 py-1 text-text-secondary hover:text-text-primary [&::-webkit-details-marker]:hidden">
            <ChevronRight className="h-3.5 w-3.5 transition-transform group-open:rotate-90" />
            支持哪些写法？
          </summary>
          <div id="timezone-input-help" className="mt-1 space-y-2 pb-2">
          <p>
            要带日期；结尾可以加时区，不加按<span className="font-medium text-text-secondary">美中时间</span>算。
            「今天」「明天」也按这个时区的日期算。
          </p>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            {INPUT_FORMATS.map(format => (
              <div key={format.label} className="contents">
                <dt className="text-text-secondary">{format.label}</dt>
                <dd>{format.examples}</dd>
              </div>
            ))}
          </dl>
          <p>
            时区：ET / EST / EDT 美东，CT / CST / CDT 美中，MT / MST / MDT 美山，PT / PST / PDT 美西，还有 UTC、BEIJING，
            例如 1/26 4pm PT。夏令时自动处理，EST、EDT 写哪个都按当天实际时间算。
          </p>
          <p>不支持：只写时间不写日期（3pm EST）、星期（Thursday 3pm）、「晚上8点」（请写「下午8点」或 20:00）。</p>
          </div>
        </details>
      </section>
    </div>
  );
}
