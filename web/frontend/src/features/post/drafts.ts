import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { apiClient, ApiErrorWrapper } from '@/shared/api/client';
import { postSnapshot, type PostSnapshot, type PostStoreHook } from '@/shared/stores/postStore';

/** 翻译记录列表里的一行（后端 summarize） */
export interface DraftSummary {
  id: string;
  source: 'manual' | 'slack';
  status: 'draft' | 'done';
  /** 标记已发送的时间（秒）；和 status 无关。旧后端没有 */
  sent_at?: number | null;
  /** 算不算已发送：手动标过，或没标过但建了超过两周（sent_auto） */
  sent?: boolean;
  sent_auto?: boolean;
  /** 标了已发送之后当前译文又变了 */
  sent_changed?: boolean;
  auto: boolean;
  seen: boolean;
  title: string;
  preview: string;
  source_preview: string;
  versions: number;
  images: string[];
  image_count: number;
  slack: { channel_id: string; thread_ts: string; channel_name?: string; title?: string } | null;
  created_at: number;
  updated_at: number;
}

export interface DraftImage {
  id: string;
  name: string;
}

export interface DraftExtraction {
  has_post: boolean;
  note: string;
  message_ts: string[];
  candidates: { label: string; source_text: string; message_ts: string[]; image_ids: string[] }[];
  instruction: string;
  extracted_at: number;
  latest_ts: string;
}

/** 建议发送时间：后端从 Slack thread 里摘出来、换算成上海时间（src/services/send_time.py） */
export interface SendTime {
  /** 上海时间 ISO（带 +08:00）；只说了日期没说几点时为 null */
  shanghai: string | null;
  /** 11月29日 周日 23:00 */
  shanghai_label: string;
  date_only: boolean;
  /** 原文时区的钟点：2026-11-29 09:00 */
  source_local: string;
  /** 美中 / 美东… */
  source_label: string;
  /** 原话：post tmw 9am */
  text: string;
  /** 原文没写时区，按美中算的 */
  tz_assumed?: boolean;
}

/** 列表里的短写法：11/29 23:00；只有日期时写 11/29 */
export function sendTimeShort(sendTime: SendTime): string {
  const iso = sendTime.shanghai ?? sendTime.source_local;
  const m = /^\d{4}-(\d{2})-(\d{2})(?:[T ](\d{2}:\d{2}))?/.exec(iso ?? '');
  if (!m) return sendTime.shanghai_label;
  const day = `${Number(m[1])}/${Number(m[2])}`;
  return sendTime.date_only || !m[3] ? day : `${day} ${m[3]}`;
}

/** 悬停说明：原话、按什么时区换算的 */
export function sendTimeHint(sendTime: SendTime): string {
  const basis = sendTime.tz_assumed ? '没写时区，按美中时间算' : `按${sendTime.source_label}时间算`;
  return `原话：「${sendTime.text}」\n${basis}：${sendTime.source_local} → 上海 ${sendTime.shanghai_label}`;
}

export interface DraftDoc {
  id: string;
  source: 'manual' | 'slack';
  status: 'draft' | 'done';
  sent_at?: number | null;
  sent?: boolean;
  sent_auto?: boolean;
  sent_changed?: boolean;
  auto: boolean;
  seen: boolean;
  rev: number;
  state: PostSnapshot;
  images: DraftImage[];
  slack?: { channel_id: string; thread_ts: string; channel_name: string; title: string; permalink: string; latest_ts: string } | null;
  extraction?: DraftExtraction;
  send_time?: SendTime | null;
  created_at: number;
  updated_at: number;
}

export interface DraftExtra {
  images?: DraftImage[];
  status?: 'draft' | 'done';
  seen?: boolean;
}

export const draftsApi = {
  list: (q = '', source = '', sent: SentFilter = '') =>
    apiClient.get<{ items: DraftSummary[] }>('/post-drafts', { params: { q, source, sent }, retry: false }),
  get: (id: string) => apiClient.get<DraftDoc>(`/post-drafts/${id}`, { retry: false }),
  create: (body: { state: PostSnapshot } & DraftExtra) => apiClient.post<DraftDoc>('/post-drafts', body, { retry: false }),
  save: (id: string, body: { state: PostSnapshot; rev: number | null } & DraftExtra) =>
    apiClient.put<DraftDoc>(`/post-drafts/${id}`, body, { retry: false }),
  slack: (channelId: string, threadTs: string) =>
    apiClient.get<{ draft: DraftDoc | null; running?: boolean }>(`/post-drafts/slack/${channelId}/${threadTs}`, { retry: false }),
  runSlack: (channelId: string, threadTs: string, instruction?: string) =>
    apiClient.post<DraftDoc>(`/post-drafts/slack/${channelId}/${threadTs}/run`, { instruction: instruction || null }, {
      retry: false,
      timeout: 300_000,
    }),
  /** 已发送：单独一个接口，不动 rev，正在编辑也不会冲突 */
  setSent: (id: string, sent: boolean) =>
    apiClient.put<{ ok: boolean; sent: boolean; sent_at: number | null; sent_auto: boolean; sent_changed: boolean }>(`/post-drafts/${id}/sent`, { sent }, { retry: false }),
  imagesZipUrl: (id: string) => `/api/post-drafts/${id}/images.zip`,
};

/** 「已发送」按钮的提示：手动标的写时间；没标过的是超过两周默认已发送 */
export function sentTitle(sent: boolean, sentAt: number | null): string {
  if (!sent) return '在 Slack 等地方发出去之后点一下';
  if (!sentAt) return '超过两周，默认算已发送；点一下改成未发送';
  return `发送于 ${new Date(sentAt * 1000).toLocaleString('zh-CN')}，点一下撤销`;
}

/** 翻译记录筛选：yes 已发送（含超两周默认的），no 未发送（只剩两周内的） */
export type SentFilter = '' | 'yes' | 'no';

export const draftKeys = {
  list: (q: string, sent: SentFilter = '') => ['post-drafts', 'list', q, sent] as const,
  slack: (channelId: string, threadTs: string) => ['post-drafts', 'slack', channelId, threadTs] as const,
};

export function useDraftList(q: string, sent: SentFilter = '') {
  return useQuery({
    queryKey: draftKeys.list(q, sent),
    queryFn: () => draftsApi.list(q, '', sent),
    select: data => data.items,
    staleTime: 10_000,
  });
}

const SAVE_DELAY_MS = 800;
const SNAPSHOT_FIELDS = [
  'originalText', 'sourceRevision', 'versions', 'currentVersionId', 'versionMetadata',
  'generatedTitles', 'selectedTitle', 'titleContentIdentity',
] as const;

/**
 * 把工作区 store 自动存到服务器翻译稿：内容变了 0.8 秒后存一次。
 * - 帖子翻译页（manual）：出过第一版译文才建稿；
 * - Slack：稿子已经由后端流程建好，这里只管保存修改。
 * 存的时候别处改过（409）：载入服务器上的最新版。
 */
export function useDraftSync(
  useStore: PostStoreHook,
  { enabled = true, extra }: { enabled?: boolean; extra?: () => DraftExtra } = {}
) {
  const queryClient = useQueryClient();
  const [saving, setSaving] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const lastSaved = useRef<string>('');
  const timer = useRef<number | null>(null);
  const extraRef = useRef(extra);
  useEffect(() => {
    extraRef.current = extra;
  });

  const payload = useCallback(() => {
    const state = useStore.getState();
    return { state: postSnapshot(state), ...(extraRef.current?.() ?? {}) };
  }, [useStore]);

  const flush = useCallback(async () => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = null;
    const state = useStore.getState();
    const body = payload();
    const key = JSON.stringify(body);
    if (key === lastSaved.current) return;
    if (!state.draftId && body.state.versions.length === 0) return;
    if (state.pendingAction) return; // 请求结束后会再触发一次
    setSaving(true);
    try {
      const doc = state.draftId
        ? await draftsApi.save(state.draftId, { ...body, rev: state.draftRev })
        : await draftsApi.create(body);
      lastSaved.current = key;
      useStore.getState().setDraft(doc.id, doc.rev);
      setSavedAt(Date.now());
      void queryClient.invalidateQueries({ queryKey: ['post-drafts'] });
    } catch (error) {
      if (error instanceof ApiErrorWrapper && error.status === 409 && state.draftId) {
        const latest = await draftsApi.get(state.draftId);
        useStore.getState().loadSnapshot(latest.state, latest.id, latest.rev);
        lastSaved.current = JSON.stringify({ state: postSnapshot(useStore.getState()), ...(extraRef.current?.() ?? {}) });
        toast.info('这份翻译稿在别处改过，已载入最新内容');
      } else {
        toast.error(error instanceof Error ? `翻译稿没存上：${error.message}` : '翻译稿没存上');
      }
    } finally {
      setSaving(false);
    }
  }, [payload, queryClient, useStore]);

  const schedule = useCallback(() => {
    if (!enabled) return;
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => void flush(), SAVE_DELAY_MS);
  }, [enabled, flush]);

  /** 刚从服务器载入：以它为基准，不要马上又存回去 */
  const markLoaded = useCallback(() => {
    lastSaved.current = JSON.stringify(payload());
  }, [payload]);

  useEffect(() => {
    if (!enabled) return;
    const unsubscribe = useStore.subscribe((state, prev) => {
      if (state.pendingAction !== prev.pendingAction && !state.pendingAction) {
        schedule();
        return;
      }
      if (SNAPSHOT_FIELDS.some(field => state[field] !== prev[field])) schedule();
    });
    return () => {
      unsubscribe();
      if (timer.current) {
        window.clearTimeout(timer.current);
        void flush();
      }
    };
  }, [enabled, flush, schedule, useStore]);

  return { saving, savedAt, flush, schedule, markLoaded };
}
