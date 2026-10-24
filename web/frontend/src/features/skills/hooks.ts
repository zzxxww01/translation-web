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
// 服务端空闲时每 15 秒发一次 ping；连续这么久什么都没收到，就当连接卡死了
export const STALL_MS = 40_000;
const WATCHDOG_MS = 5_000;

export function isStalled(lastActivity: number, now: number, limit = STALL_MS): boolean {
  return now - lastActivity > limit;
}

/**
 * 订阅一次运行的事件流。组件按 runId 加 key 挂载，换运行时整个重建，所以这里不需要重置状态。
 * 三种断法分别处理：
 * - 普通断线：EventSource 自己会带 Last-Event-ID 重连；
 * - 被服务器拒绝（401、502 等）：浏览器放弃重连，隔几秒再从已有的最后一条接着订阅；
 * - 连接卡住却没断开（经代理、隧道时实测出现过，作答后页面再也收不到事件）：浏览器察觉不到，
 *   靠看门狗发现长时间连心跳都没有，主动重连。
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
    let lastActivity = Date.now();

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
      // 重连前把还没渲染的事件并进去，after 才是真正收到的最后一条
      if (buffer.length) {
        clearTimeout(flushTimer);
        flush();
      }
      const after = eventsRef.current.length ? eventsRef.current[eventsRef.current.length - 1].seq : 0;
      lastActivity = Date.now();
      source = new EventSource(eventsUrl(runId, after));
      source.onopen = () => {
        lastActivity = Date.now();
        setConnected(true);
      };
      source.addEventListener('ping', () => {
        lastActivity = Date.now();
      });
      source.onmessage = message => {
        lastActivity = Date.now();
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
          retryTimer = setTimeout(() => {
            retryTimer = undefined;
            connect();
          }, RECONNECT_MS);
        }
      };
    };

    connect();
    const watchdog = setInterval(() => {
      if (disposed || retryTimer || !source || source.readyState === EventSource.CLOSED) return;
      if (isStalled(lastActivity, Date.now())) {
        setConnected(false);
        source.close();
        connect();
      }
    }, WATCHDOG_MS);
    return () => {
      disposed = true;
      source?.close();
      clearInterval(watchdog);
      clearTimeout(flushTimer);
      clearTimeout(retryTimer);
    };
  }, [runId]);

  return { events, connected };
}
