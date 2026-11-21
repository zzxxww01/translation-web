import { useMemo } from 'react';
import { useQueries, useQuery } from '@tanstack/react-query';
import { slackInboxApi } from './api';
import type { SlackMessage } from './types';

// 后端一次最多 40 条；按 20 条一批，单次模型调用更快、不容易超时，中文也出得早
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

/** 一条消息里要翻的文字：正文 + 每张链接卡片的正文。key 用来把译文对回去。 */
interface Piece {
  key: string;
  text: string;
}

export function cardKey(ts: string, index: number) {
  return `${ts}#card${index}`;
}

/** 自己发的消息不翻；正文和链接卡片各算一段 */
export function piecesOf(message: SlackMessage): Piece[] {
  if (message.is_me) return [];
  const pieces: Piece[] = [];
  if (message.text.trim()) pieces.push({ key: message.ts, text: message.text });
  message.attachments.forEach((a, i) => {
    if (a.text?.trim()) pieces.push({ key: cardKey(message.ts, i), text: a.text });
  });
  return pieces;
}

/** 中文结果：消息 ts -> 正文中文；cardKey(ts, i) -> 第 i 张卡片的中文 */
export type ZhMap = Map<string, string>;

function useZh(pieces: Piece[], enabled: boolean, context: string | null | undefined) {
  const batches = useMemo(() => chunk(pieces, ZH_BATCH), [pieces]);
  const results = useQueries({
    queries: batches.map(batch => {
      const texts = batch.map(p => p.text);
      return {
        queryKey: ['slack-zh', hashTexts(texts), hashTexts([context ?? ''])],
        queryFn: () => slackInboxApi.translate(texts, context),
        enabled,
        staleTime: Infinity,
        gcTime: 30 * 60_000,
        retry: 1,
      };
    }),
  });
  const map: ZhMap = new Map();
  results.forEach((r, i) => {
    r.data?.translations.forEach((zh, j) => {
      if (zh) map.set(batches[i][j].key, zh);
    });
  });
  return {
    zh: map,
    loading: enabled && results.some(r => r.isLoading),
    failed: results.some(r => r.isError),
    done: enabled && results.length > 0 && results.every(r => r.isSuccess),
  };
}

/** 单条消息点「译」：正文和链接卡片一起翻（和整段翻译共用后端缓存） */
export function useOneZh(message: SlackMessage, enabled: boolean, context?: string | null) {
  const pieces = useMemo(() => piecesOf(message), [message]);
  return useZh(pieces, enabled && pieces.length > 0, context);
}

/** thread「翻译全部」：整个 thread 的消息（不含我自己的），根帖作为背景 */
export function useThreadZh(messages: SlackMessage[], enabled: boolean, context?: string | null) {
  const pieces = useMemo(() => messages.flatMap(piecesOf), [messages]);
  return useZh(pieces, enabled, context);
}

/** thread 摘要；latestTs 变了（有新回复）就是另一条缓存，后端也按它缓存。 */
export function useThreadSummary(channelId: string, threadTs: string, latestTs: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ['slack-summary', channelId, threadTs, latestTs],
    queryFn: () => slackInboxApi.threadSummary(channelId, threadTs),
    enabled: enabled && !!latestTs,
    staleTime: Infinity,
    retry: 1,
  });
}
