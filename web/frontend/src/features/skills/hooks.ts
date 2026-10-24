import { useQuery } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { ApiErrorWrapper } from '../../shared/api/client';
import { eventsUrl, skillsApi } from './api';
import { mergeEvents } from './state';
import type { RunStatus, SkillEvent } from './types';

export const skillKeys = {
  me: ['skills', 'me'] as const,
  catalog: ['skills', 'catalog'] as const,
  runs: ['skills', 'runs'] as const,
  files: (runId: string) => ['skills', 'files', runId] as const,
};

export function isUnauthorized(error: unknown): boolean {
  return error instanceof ApiErrorWrapper && error.status === 401;
}

export function useSkillsAuth() {
  return useQuery({ queryKey: skillKeys.me, queryFn: skillsApi.me, retry: false, staleTime: 60_000 });
}

export function useCatalog(enabled: boolean) {
  return useQuery({ queryKey: skillKeys.catalog, queryFn: skillsApi.catalog, enabled, staleTime: 5 * 60_000 });
}

export function useRuns(enabled: boolean) {
  // 列表上的状态靠轮询更新；当前打开的运行另有实时事件流
  return useQuery({ queryKey: skillKeys.runs, queryFn: skillsApi.runs, enabled, refetchInterval: 10_000 });
}

export function useRunFiles(runId: string, status: RunStatus | null) {
  const busy = status === 'running' || status === 'waiting';
  return useQuery({
    queryKey: skillKeys.files(runId),
    queryFn: () => skillsApi.files(runId),
    refetchInterval: busy ? 5_000 : false,
  });
}

const FLUSH_MS = 60;
const RECONNECT_MS = 5_000;

/**
 * 订阅一次运行的事件流。组件按 runId 加 key 挂载，换运行时整个重建，所以这里不需要重置状态。
 * EventSource 自己会带 Last-Event-ID 重连；只有被服务器拒绝（401、502 等）时浏览器才放弃，这时隔几秒再从
 * 已有的最后一条接着订阅。
 */
export function useRunEvents(runId: string) {
  const [events, setEvents] = useState<SkillEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const eventsRef = useRef<SkillEvent[]>([]);

  useEffect(() => {
    let source: EventSource | null = null;
    let buffer: SkillEvent[] = [];
    let flushTimer: ReturnType<typeof setTimeout> | undefined;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let disposed = false;

    const flush = () => {
      flushTimer = undefined;
      const merged = mergeEvents(eventsRef.current, buffer);
      buffer = [];
      if (merged !== eventsRef.current) {
        eventsRef.current = merged;
        setEvents(merged);
      }
    };

    const connect = () => {
      const after = eventsRef.current.length ? eventsRef.current[eventsRef.current.length - 1].seq : 0;
      source = new EventSource(eventsUrl(runId, after));
      source.onopen = () => setConnected(true);
      source.onmessage = message => {
        try {
          buffer.push(JSON.parse(message.data) as SkillEvent);
        } catch {
          return;
        }
        // 攒一小批再渲染：子代理并行时一秒能来几十条
        flushTimer ??= setTimeout(flush, FLUSH_MS);
      };
      source.onerror = () => {
        setConnected(false);
        if (source?.readyState === EventSource.CLOSED && !disposed) {
          source.close();
          flush();
          retryTimer = setTimeout(connect, RECONNECT_MS);
        }
      };
    };

    connect();
    return () => {
      disposed = true;
      source?.close();
      clearTimeout(flushTimer);
      clearTimeout(retryTimer);
    };
  }, [runId]);

  return { events, connected };
}
