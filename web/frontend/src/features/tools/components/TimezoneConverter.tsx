import { useState, useEffect } from 'react';
import { useConvertTimezone } from '../hooks';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { RotateCw } from 'lucide-react';
import type { TimezoneConvertResult } from '@/shared/types';

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

function LiveTimeCard({ title, timeZone }: { title: string; timeZone: string }) {
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
    <Card>
      <CardContent className="px-2 py-3 text-center sm:py-5">
        <div className="mb-1.5 text-[11px] font-medium text-text-muted sm:mb-2 sm:text-xs">{title}</div>
        <div className="text-lg font-semibold leading-none tabular-nums text-text-primary sm:text-[30px]" style={{ fontFamily: 'var(--font-display)' }}>
          {time || <Skeleton className="h-8 w-24 mx-auto" />}
        </div>
        <div className="mt-2 text-[11px] text-text-muted sm:text-xs">{date}</div>
      </CardContent>
    </Card>
  );
}

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

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-2 sm:gap-4">
        <LiveTimeCard title="北京时间" timeZone="Asia/Shanghai" />
        <LiveTimeCard title="美中时间" timeZone="America/Chicago" />
        <LiveTimeCard title="美西时间" timeZone="America/Los_Angeles" />
      </div>

      <div className="space-y-2">
        <label htmlFor="timezone-input" className="text-[13px] font-semibold text-text-secondary">换算一个时间</label>
        {/* 输入框和按钮同一行，回车也能换算 */}
        <div className="flex gap-2">
          <Input
            id="timezone-input"
            placeholder="例如：今天下午3点、1/26 4pm PT、2026-01-26 14:00 EST"
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
            {timezoneMutation.isPending ? <RotateCw className="animate-spin" /> : <RotateCw />}
            换算
          </Button>
        </div>
        <details className="text-xs leading-relaxed text-text-muted">
          <summary className="cursor-pointer select-none py-1 text-text-secondary hover:text-text-primary">支持哪些写法？</summary>
          <div id="timezone-input-help" className="mt-1 space-y-2 rounded-lg bg-bg-tertiary px-3 py-2.5">
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
      </div>

      {result && (
        // 结果：北京时间放最前、最大，其余美国四个时区一行一个
        <div className="overflow-hidden rounded-xl border border-border-subtle bg-white" aria-live="polite">
          <div className="flex items-baseline justify-between gap-3 border-b border-border-subtle bg-primary-50/50 px-4 py-3">
            <span className="text-xs font-medium text-primary-700">北京时间</span>
            <span className="text-lg font-semibold tabular-nums text-text-primary">{result.beijing || '--'}</span>
          </div>
          <dl className="divide-y divide-border-subtle">
            {[
              { label: '美东时间', value: result.est },
              { label: '美中时间', value: result.cst },
              { label: '美山时间', value: result.mst },
              { label: '美西时间', value: result.pst },
            ].map(item => (
              <div key={item.label} className="flex items-baseline justify-between gap-3 px-4 py-2.5 text-sm">
                <dt className="text-text-muted">{item.label}</dt>
                <dd className="tabular-nums text-text-primary">{item.value || '--'}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
}
