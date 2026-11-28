import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { ArrowRight, Loader2 } from 'lucide-react';
import { useConvertTimezone } from '../hooks';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import type { TimezoneConvertResult } from '@/shared/types';
import { cn } from '@/lib/utils';
import { PANE, PANE_HEADER } from '@/shared/ui/pane';
import { addDays, BEIJING, dateIn, describe, diffFromBeijing, ZONES, zonedToInstant } from '../lib/zones';

/** 顶上一排的实时时钟 */
const CLOCKS = ['Asia/Shanghai', 'America/New_York', 'America/Chicago', 'America/Los_Angeles'];
/** 换算的来源时区：美中排第一、默认选它（同事排期一般按美中说） */
const SOURCES = ['America/Chicago', 'America/New_York', 'America/Los_Angeles', 'Asia/Shanghai', 'UTC'];
const zone = (id: string) => ZONES.find(z => z.id === id)!;

function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), intervalMs);
    return () => window.clearInterval(id);
  }, [intervalMs]);
  return now;
}

function Clock({ id, now }: { id: string; now: Date }) {
  const d = describe(now, id, now);
  return (
    <div className={cn('rounded-xl border px-4 py-3', id === BEIJING ? 'border-primary-100 bg-primary-50/60' : 'border-border-subtle bg-white')}>
      <div className="text-[13px] font-medium text-text-secondary">{zone(id).label}</div>
      <div className="mt-1 text-[28px] font-semibold leading-tight tabular-nums text-text-primary [font-family:var(--font-display)]">{d.time}</div>
      <div className="text-xs tabular-nums text-text-muted">{d.date} {d.weekday}</div>
      <div className="mt-0.5 text-[11px] text-text-muted">{id === BEIJING ? '基准' : diffFromBeijing(now, id)}</div>
    </div>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" onClick={onClick} aria-pressed={active}
      className={cn('h-8 rounded-full px-3 text-[13px] transition-colors',
        active ? 'bg-primary-600 font-medium text-white' : 'bg-bg-tertiary text-text-secondary hover:bg-primary-50 hover:text-primary-700')}>
      {children}
    </button>
  );
}

/** 粘贴一句话（例如「1/26 4pm PT」）走后端解析：同事消息里的写法直接贴进来 */
function PasteConvert() {
  const mutation = useConvertTimezone();
  const [input, setInput] = useState('');
  const [result, setResult] = useState<TimezoneConvertResult | null>(null);
  const run = async () => {
    if (!input.trim() || mutation.isPending) return;
    try {
      setResult(await mutation.mutateAsync({ input, source_timezone: 'auto' }));
    } catch {
      // 错误提示由 mutation hook 给
    }
  };
  return (
    <div className="border-t border-border-subtle px-4 py-3">
      <label htmlFor="timezone-input" className="text-xs text-text-muted">也可以直接粘贴一句话（不写时区按美中算）</label>
      <div className="mt-1.5 flex gap-2">
        <Input id="timezone-input" value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') void run(); }}
          placeholder="1/26 4pm PT、明天上午9点半、Jan 26 4pm" className="h-9 min-w-0 flex-1" />
        <Button variant="outline" onClick={() => void run()} disabled={!input.trim() || mutation.isPending} className="h-9 shrink-0">
          {mutation.isPending ? <Loader2 className="animate-spin" /> : <ArrowRight />} 识别
        </Button>
      </div>
      {result && (
        <p className="mt-2 text-sm text-text-primary" aria-live="polite">
          北京时间 <span className="font-semibold tabular-nums">{result.beijing}</span>
          <span className="ml-2 text-xs text-text-muted">美东 {result.est} · 美西 {result.pst}</span>
        </p>
      )}
    </div>
  );
}

export function TimezoneConverter() {
  const now = useNow();
  const [source, setSource] = useState('America/Chicago');
  const [date, setDate] = useState(() => dateIn(new Date(), 'America/Chicago'));
  const [time, setTime] = useState('09:00');
  const today = dateIn(now, source);
  const instant = useMemo(() => zonedToInstant(date, time, source), [date, time, source]);

  const pickSource = (id: string) => {
    // 换来源时区时，「今天 / 明天」跟着那个时区走
    const offset = Math.round((Date.parse(date) - Date.parse(dateIn(new Date(), source))) / 86400000);
    setSource(id);
    setDate(addDays(dateIn(new Date(), id), offset));
  };

  const beijing = instant ? describe(instant, BEIJING, now) : null;
  const targets = ZONES.filter(z => z.id !== BEIJING && z.id !== source && z.id !== 'UTC');

  return (
    <div className="space-y-5">
      <section aria-label="现在各地时间" className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {CLOCKS.map(id => <Clock key={id} id={id} now={now} />)}
      </section>

      <section className={PANE} aria-labelledby="timezone-convert-label">
        <header className={PANE_HEADER}>
          <h2 id="timezone-convert-label" className="text-[13px] font-semibold text-text-secondary">换算一个时间</h2>
          <span className="text-xs text-text-muted">改了马上出结果，夏令时自动算</span>
        </header>
        <div className="grid gap-5 p-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
          {/* 左：哪个时区的几号几点 */}
          <div className="space-y-4">
            <div>
              <div className="mb-1.5 text-xs text-text-muted">原来的时区</div>
              <div className="flex flex-wrap gap-1.5" role="group" aria-label="原来的时区">
                {SOURCES.map(id => <Chip key={id} active={source === id} onClick={() => pickSource(id)}>{zone(id).short}</Chip>)}
              </div>
            </div>
            <div>
              <div className="mb-1.5 text-xs text-text-muted">日期（{zone(source).short}）</div>
              <div className="flex flex-wrap items-center gap-1.5">
                {['今天', '明天', '后天'].map((label, i) => (
                  <Chip key={label} active={date === addDays(today, i)} onClick={() => setDate(addDays(today, i))}>{label}</Chip>
                ))}
                <input type="date" value={date} onChange={e => e.target.value && setDate(e.target.value)} aria-label="日期"
                  className="h-8 rounded-full border border-border-subtle bg-white px-3 text-[13px] tabular-nums text-text-primary outline-none focus:border-primary-200" />
              </div>
            </div>
            <div>
              <label htmlFor="timezone-time" className="mb-1.5 block text-xs text-text-muted">时间（{zone(source).short}）</label>
              <input id="timezone-time" type="time" value={time} onChange={e => setTime(e.target.value)}
                className="h-11 w-40 rounded-lg border border-border-subtle bg-white px-3 text-xl font-semibold tabular-nums text-text-primary outline-none focus:border-primary-200 focus:ring-2 focus:ring-primary-50" />
            </div>
          </div>

          {/* 右：北京时间最大，其他时区列在下面 */}
          <div aria-live="polite">
            {source !== BEIJING && (
              <div className="rounded-xl bg-primary-50/70 px-4 py-3">
                <div className="text-xs font-medium text-primary-700">北京时间</div>
                {beijing ? (
                  <div className="mt-1 flex flex-wrap items-baseline gap-x-2">
                    <span className="text-[32px] font-semibold leading-tight tabular-nums text-text-primary [font-family:var(--font-display)]">{beijing.time}</span>
                    <span className="text-sm text-text-secondary">{beijing.date} {beijing.weekday}</span>
                    {beijing.relative && <span className="rounded-full bg-white px-2 py-0.5 text-xs text-primary-700">{beijing.relative}</span>}
                  </div>
                ) : <div className="mt-1 text-lg text-text-muted">—</div>}
              </div>
            )}
            <dl className="mt-2 divide-y divide-border-subtle">
              {targets.map(z => {
                const d = instant ? describe(instant, z.id, now) : null;
                return (
                  <div key={z.id} className="flex items-baseline justify-between gap-3 px-1 py-2 text-sm">
                    <dt className="text-text-muted">{z.label}</dt>
                    <dd className="tabular-nums text-text-primary">
                      {d ? <>{d.date} {d.weekday} <span className="font-semibold">{d.time}</span>{d.relative && <span className="ml-1.5 text-xs text-text-muted">{d.relative}</span>}</> : '—'}
                    </dd>
                  </div>
                );
              })}
            </dl>
          </div>
        </div>
        <PasteConvert />
      </section>
    </div>
  );
}
