import { useState, useEffect } from 'react';
import { useConvertTimezone } from '../hooks';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { RotateCw } from 'lucide-react';
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
      <div className="grid grid-cols-4 gap-4">
        <LiveTimeCard title="北京时间" timeZone="Asia/Shanghai" />
        <LiveTimeCard title="美东时间" timeZone="America/New_York" />
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
