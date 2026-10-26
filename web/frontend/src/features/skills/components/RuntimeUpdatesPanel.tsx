import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/Button';
import { skillsApi } from '../api';
import type { Harness } from '../harness';

const KEY = ['skills', 'runtime'] as const;

export function RuntimeUpdatesPanel() {
  const client = useQueryClient();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const query = useQuery({
    queryKey: KEY, queryFn: skillsApi.runtimeStatus, retry: false,
    refetchInterval: query => query.state.data?.active || query.state.data?.checking ? 1500 : false,
  });
  const busy = pending || query.data?.active || query.data?.checking;
  const updated = query.data?.runtimes.filter(runtime => runtime.status === 'succeeded')
    .map(runtime => `${runtime.harness}:${runtime.updated_at}`).join(',');
  useEffect(() => {
    if (updated) void client.invalidateQueries({ queryKey: ['skills', 'models'] });
  }, [updated, client]);

  const perform = async (harness?: Harness) => {
    setPending(true);
    setError(null);
    try {
      const data = harness ? await skillsApi.updateRuntime(harness) : await skillsApi.checkUpdates();
      client.setQueryData(KEY, data);
    } catch (error) {
      setError(error instanceof Error ? error.message : '操作失败，请重试');
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm leading-relaxed text-text-muted">检查服务器上的 Codex、Claude Code 和 Antigravity 版本。有对话正在运行或等待确认时，请先结束任务再更新。</p>
      <Button variant="outline" size="sm" disabled={Boolean(busy)} onClick={() => void perform()}>
        {pending && !query.data?.active ? '处理中…' : '检查更新'}
      </Button>
      {query.isPending && <p className="text-sm text-text-muted">读取版本信息…</p>}
      {(error || query.error) && <p role="alert" className="text-sm text-error">{error || query.error?.message}</p>}
      {query.error && <Button variant="outline" size="sm" onClick={() => void query.refetch()}>重新读取</Button>}
      {query.data?.runtimes.map(runtime => (
        <div key={runtime.harness} className="rounded-lg border border-border-subtle bg-bg-secondary p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-medium text-text-primary">{runtime.label}</h3>
              <p className="mt-1 text-xs text-text-muted">当前 {runtime.current ?? '未检查'} · 最新 {runtime.latest ?? '未检查'}</p>
            </div>
            <Button size="sm" variant="outline" aria-label={`更新 ${runtime.label}`}
              disabled={Boolean(busy || !runtime.can_update || !runtime.update_available)}
              onClick={() => void perform(runtime.harness)}>
              {runtime.status === 'updating' ? '更新中…' : runtime.current && runtime.current === runtime.latest ? '已是最新' : '更新'}
            </Button>
          </div>
          {runtime.message && <p role="status" className="mt-2 text-xs text-text-secondary">{runtime.message}</p>}
          {runtime.reason && <p className="mt-2 text-xs text-text-muted">{runtime.reason}</p>}
          {runtime.error && <p role="alert" className="mt-2 break-words text-xs text-error">{runtime.error}</p>}
        </div>
      ))}
    </div>
  );
}
