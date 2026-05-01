import { useState, useEffect } from 'react';
import { useConvertTimezone } from '../hooks';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowRight, Clock3, RotateCw } from 'lucide-react';
import type { TimezoneConvertResult } from '@/shared/types';

function formatTime(date: Date): string {
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
}

function formatDate(date: Date): string {
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  const y = date.getFullYear();
  const m = (date.getMonth() + 1).toString().padStart(2, '0');
  const d = date.getDate().toString().padStart(2, '0');
  return `${y}/${m}/${d} ${weekdays[date.getDay()]}`;
}

function LiveTimeCard({ title, timeZone }: { title: string; timeZone: string }) {
  const [time, setTime] = useState('');
  const [date, setDate] = useState('');

  useEffect(() => {
    const update = () => {
      const now = new Date();
      const local = new Date(now.toLocaleString('en-US', { timeZone }));
      setTime(formatTime(local));
      setDate(formatDate(local));
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [timeZone]);

  return (
    <Card className="rounded-lg">
      <CardContent className="p-3">
        <div className="flex items-start justify-between gap-3 sm:block sm:text-center">
          <div className="text-sm font-medium text-slate-500">{title}</div>
          <div className="text-right sm:text-center">
            <div className="text-xl font-semibold tabular-nums text-slate-950 sm:mt-1 sm:text-2xl">
              {time || <Skeleton className="h-8 w-24 mx-auto" />}
            </div>
            <div className="text-xs text-slate-500 sm:text-sm">{date}</div>
          </div>
        </div>
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
    const res = await timezoneMutation.mutateAsync({
      input,
      source_timezone: 'auto',
    });
    setResult(res);
  };

  return (
    <div className="space-y-4 md:space-y-5">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3 sm:gap-3">
        <LiveTimeCard title="北京时间" timeZone="Asia/Shanghai" />
        <LiveTimeCard title="美中时间" timeZone="America/Chicago" />
        <LiveTimeCard title="美西时间" timeZone="America/Los_Angeles" />
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-stretch">
          <div className="relative min-w-0 flex-1">
            <div className="pointer-events-none absolute left-3 top-1/2 flex -translate-y-1/2 items-center gap-2 text-slate-400">
              <Clock3 className="h-4 w-4" />
            </div>
            <Input
              aria-label="输入时间"
              placeholder="输入时间，例如 今天下午3点 / 1/26/26 4pm cdt / 2024-01-15 14:00"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleConvert()}
              className="h-12 w-full rounded-md border-slate-200 bg-slate-50 pl-10 pr-4 font-medium shadow-none focus:bg-white"
            />
          </div>

          <Button
            onClick={handleConvert}
            disabled={!input.trim() || timezoneMutation.isPending}
            className="h-12 rounded-md px-5 md:w-28"
          >
            {timezoneMutation.isPending ? (
              <RotateCw className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowRight className="h-4 w-4" />
            )}
            转换
          </Button>
        </div>
      </section>

      {result && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-slate-950">转换结果</h4>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {[
              { label: '美东时间', value: result.est },
              { label: '美中时间', value: result.cst },
              { label: '美山时间', value: result.mst },
              { label: '美西时间', value: result.pst },
            ].map(item => (
              <Card key={item.label}>
                <CardContent className="flex items-center justify-between gap-3 p-3">
                  <div className="text-sm font-medium text-slate-500">{item.label}</div>
                  <div className="text-right font-semibold tabular-nums text-slate-950">{item.value || '--'}</div>
                </CardContent>
              </Card>
            ))}
            <Card className="border-slate-300 bg-slate-950 text-white sm:col-span-2">
              <CardContent className="flex items-center justify-between gap-3 p-3">
                <div className="text-sm font-medium text-slate-300">北京时间</div>
                <div className="text-right text-lg font-semibold tabular-nums text-white">{result.beijing || '--'}</div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
