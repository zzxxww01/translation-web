import { useState, useEffect } from 'react';
import { useConvertTimezone } from '../hooks';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { RotateCw } from 'lucide-react';
import type { TimezoneConvertResult } from '@/shared/types';

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
      <CardContent className="pt-4 text-center">
        <div className="mb-1 text-sm text-muted-foreground">{title}</div>
        <div className="text-2xl font-bold tabular-nums">{time || <Skeleton className="h-8 w-24 mx-auto" />}</div>
        <div className="text-sm text-muted-foreground">{date}</div>
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
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        <LiveTimeCard title="北京时间" timeZone="Asia/Shanghai" />
        <LiveTimeCard title="美中时间" timeZone="America/Chicago" />
        <LiveTimeCard title="美西时间" timeZone="America/Los_Angeles" />
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">输入时间</label>
        <Input
          placeholder="例如: 今天下午3点、1/26/26 4pm cdt、2024-01-15 14:00"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleConvert()}
        />
        <p className="text-xs text-muted-foreground">
          支持: 今天下午3点、1/26/26 4pm、M/D/YY h:mm am/pm、YYYY-MM-DD HH:mm，默认 CDT
        </p>
      </div>

      <Button
        onClick={handleConvert}
        disabled={!input.trim() || timezoneMutation.isPending}
        className="w-full"
      >
        {timezoneMutation.isPending ? <RotateCw className="h-4 w-4 animate-spin" /> : <RotateCw className="h-4 w-4" />}
        转换
      </Button>

      {result && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold">转换结果</h4>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: '美东时间', value: result.est },
              { label: '美中时间', value: result.cst },
              { label: '美山时间', value: result.mst },
              { label: '美西时间', value: result.pst },
            ].map(item => (
              <Card key={item.label}>
                <CardContent className="p-3">
                  <div className="text-xs text-muted-foreground">{item.label}</div>
                  <div className="font-semibold">{item.value || '--'}</div>
                </CardContent>
              </Card>
            ))}
            <Card className="col-span-2 border-primary/30 bg-primary/5">
              <CardContent className="p-3">
                <div className="text-xs text-primary">北京时间</div>
                <div className="text-lg font-semibold text-primary">{result.beijing || '--'}</div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
