import { useMemo } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { slackInboxApi } from './api';
import type { SlackMessage, SlackThread } from './types';

// 后端一次最多 40 条；消息翻译按 20 条一批，单次模型调用更快、不容易超时，中文也出得早
const BATCH = 40;
const ZH_BATCH = 20;

/** 短字符串哈希，只用来做 query key，不需要抗碰撞。 */
export function hashTexts(texts: string[]): string {
  let h = 5381;
  for (const t of texts) {
    for (let i = 0; i < t.length; i++) h = ((h << 5) + h + t.charCodeAt(i)) | 0;
    h = ((h << 5) + h + 31) | 0;
  }
  return (h >>> 0).toString(36);
}

export function chunk<T>(items: T[], size = BATCH): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

/** 「全部显示中文」开关：频道、thread、私信共用一个，记在本机；默认关（单条消息可以点「译」）。 */
export const useShowZh = create<{ showZh: boolean; toggleZh: () => void }>()(
  // 换了名字：之前默认开，存过的偏好不再沿用
  persist(set => ({ showZh: false, toggleZh: () => set(state => ({ showZh: !state.showZh })) }), { name: 'slack-show-zh-v2' })
);

/** 单条消息按需翻译（悬停工具条上的「译」）。和批量翻译共用后端缓存。 */
export function useOneZh(text: string, enabled: boolean) {
  return useQuery({
    queryKey: ['slack-zh-one', hashTexts([text])],
    queryFn: () => slackInboxApi.translate([text]),
    enabled: enabled && !!text.trim(),
    staleTime: Infinity,
    retry: 1,
    select: data => data.translations[0] ?? null,
  });
}

/** 一组消息的中文：按 40 条一批请求，后端按内容缓存。返回 ts -> 中文（不需要翻的没有）。 */
export function useMessageZh(messages: SlackMessage[], enabled: boolean) {
  const withText = useMemo(() => messages.filter(m => m.text.trim()), [messages]);
  const batches = useMemo(() => chunk(withText, ZH_BATCH), [withText]);
  const results = useQueries({
    queries: batches.map(batch => {
      const texts = batch.map(m => m.text);
      return {
        queryKey: ['slack-zh', hashTexts(texts)],
        queryFn: () => slackInboxApi.translate(texts),
        enabled,
        staleTime: Infinity,
        gcTime: 30 * 60_000,
        retry: 1,
      };
    }),
  });
  const map = new Map<string, string>();
  results.forEach((r, i) => {
    r.data?.translations.forEach((zh, j) => {
      if (zh) map.set(batches[i][j].ts, zh);
    });
  });
  return { zh: map, loading: enabled && results.some(r => r.isLoading), failed: results.some(r => r.isError) };
}

/** 侧栏 thread 的中文短标题：thread_ts -> 标题。 */
export function useThreadTitles(threads: SlackThread[] | undefined, enabled = true) {
  const items = useMemo(() => {
    const out: Record<string, string> = {};
    for (const t of (threads ?? []).slice(0, BATCH)) {
      const text = [t.root.text, ...t.root.attachments.map(a => a.title)].filter(Boolean).join('\n');
      if (text.trim()) out[t.thread_ts] = text;
    }
    return out;
  }, [threads]);
  const keys = Object.keys(items);
  const query = useQuery({
    queryKey: ['slack-titles', hashTexts(keys.map(k => k + items[k]))],
    queryFn: () => slackInboxApi.threadTitles(items),
    enabled: enabled && keys.length > 0,
    staleTime: Infinity,
    gcTime: 30 * 60_000,
    retry: 1,
    select: data => data.titles,
  });
  return query.data ?? {};
}

/** thread 摘要；latestTs 变了（有新回复）就重新取，后端也按它缓存。 */
export function useThreadSummary(channelId: string, threadTs: string, latestTs: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['slack-summary', channelId, threadTs, latestTs],
    queryFn: () => slackInboxApi.threadSummary(channelId, threadTs),
    enabled: enabled && !!latestTs,
    staleTime: Infinity,
    retry: 1,
  });
}
