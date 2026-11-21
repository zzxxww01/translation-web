import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, ChevronLeft, ChevronRight, Copy, ExternalLink, Loader2, Pencil, RefreshCw, Send, Sparkles, Wand2 } from 'lucide-react';
import { toast } from 'sonner';
import { apiClient } from '@/shared/api/client';
import { REQUEST_TIMEOUTS } from '@/shared/constants';
import { cn } from '@/lib/utils';
import { copyToClipboard } from '@/shared/utils';
import type { ComposeResult, ProcessResult } from '@/shared/types';
import { slackApi } from '../api';
import { slackInboxApi } from '../inbox/api';
import type { DmReplyGroup, DmReplyState, DmReplyVariant } from '../inbox/types';

const LABELS: Record<string, string> = { A: '简洁', B: '标准', C: '正式' };

// 一键调整：三版一起改措辞，意思不变（后端 /slack/refine，每版一次、并行）
const ADJUSTMENTS: { label: string; instruction: string }[] = [
  { label: '更短', instruction: '更简短，删掉可有可无的话，意思和承诺不变' },
  { label: '更随意', instruction: '更随意口语，像同事之间聊天' },
  { label: '更正式', instruction: '更正式、更有礼貌的职场语气' },
  { label: '更礼貌', instruction: '更礼貌、更委婉，但不增加承诺或道歉' },
  { label: '加一句感谢', instruction: '在合适的位置自然地加一句简短的感谢' },
];

function variants(raw: { version: string; english: string; chinese?: string }[]): DmReplyVariant[] {
  return raw.filter(r => r.english?.trim()).map(r => ({ version: r.version, english: r.english.trim(), chinese: (r.chinese || '').trim() }));
}

async function refineVersion(version: string, chinese: string) {
  return apiClient.post<DmReplyVariant>('/slack/refine-version', undefined, {
    params: { version, chinese, style: LABELS[version] || '标准' },
    timeout: REQUEST_TIMEOUTS.SHORT_FORM_LLM,
    retry: false,
  });
}

/**
 * 私信右栏的回复面板（2026-11-22 起不用 agent，直接调接口）：
 * 对方要什么 + A/B/C 三版回复；可以改某一版的中文意思、一键调整措辞、写「我想说」；每次结果记一组，可翻回去。
 * 对方有未读新消息时打开就自动生成一次。momo 从不发送，复制后自己去 Slack 发。
 */
export function DmReplyPanel({ channelId, latestTs, hasUnreads, slackLink }: {
  channelId: string;
  latestTs: string | null;
  hasUnreads: boolean;
  slackLink: string;
}) {
  const queryClient = useQueryClient();
  const stateQuery = useQuery({
    queryKey: ['slack-reply-state', channelId],
    queryFn: () => slackInboxApi.replyState(channelId),
    select: data => data.state,
    staleTime: Infinity,
  });
  const ctx = useQuery({
    queryKey: ['slack-reply-context', channelId, latestTs],
    queryFn: () => slackInboxApi.agentContext(channelId),
    staleTime: 30_000,
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [draft, setDraft] = useState('');
  const [editing, setEditing] = useState<{ version: string; chinese: string } | null>(null);

  const state: DmReplyState = stateQuery.data ?? { groups: [], current: -1 };
  const group: DmReplyGroup | undefined = state.groups[state.current];
  const history = useMemo(() => ctx.data?.history ?? [], [ctx.data]);
  const lastMe = history.map(h => h.role).lastIndexOf('me');
  const pendingMessages = history.slice(lastMe + 1).filter(h => h.role === 'them');
  const hasNew = !!group && !!ctx.data?.latest_ts && !!group.based_on_ts
    && parseFloat(ctx.data.latest_ts) > parseFloat(group.based_on_ts) && pendingMessages.length > 0;

  const save = async (next: DmReplyState) => {
    queryClient.setQueryData(['slack-reply-state', channelId], { state: next });
    try {
      await slackInboxApi.saveReplyState(channelId, next);
    } catch {
      toast.error('回复历史没存上，刷新后可能看不到这一组');
    }
  };

  const push = (g: DmReplyGroup) => {
    const groups = [...state.groups, g].slice(-20);
    void save({ groups, current: groups.length - 1 });
  };

  const run = async (label: string, work: () => Promise<DmReplyGroup | null>) => {
    if (busy) return;
    setBusy(label);
    try {
      const g = await work();
      if (g) push(g);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : `${label}失败`);
    } finally {
      setBusy(null);
    }
  };

  const generate = () => run('生成', async () => {
    if (!pendingMessages.length) return null;
    const res = await apiClient.post<ProcessResult>('/slack/process', {
      message: pendingMessages.map(m => m.content).join('\n\n'),
      conversation_history: history.slice(0, lastMe + 1).slice(-20),
    }, { timeout: REQUEST_TIMEOUTS.SHORT_FORM_LLM, retry: false });
    return {
      created_at: Date.now(), kind: 'generate', understanding: res.translation, pending: true,
      replies: variants(res.suggested_replies), based_on_ts: ctx.data?.latest_ts ?? null,
    };
  });

  const compose = () => run('生成', async () => {
    const text = draft.trim();
    if (!text) return null;
    const res = await apiClient.post<ComposeResult>('/slack/compose', {
      content: text, conversation_history: history.slice(-20),
    }, { timeout: REQUEST_TIMEOUTS.SHORT_FORM_LLM, retry: false });
    setDraft('');
    return {
      created_at: Date.now(), kind: 'compose', instruction: text, understanding: group?.understanding,
      pending: pendingMessages.length > 0, replies: variants(res.versions), based_on_ts: ctx.data?.latest_ts ?? null,
    };
  });

  const adjust = (label: string, instruction: string) => run(label, async () => {
    if (!group) return null;
    const refined = await Promise.all(group.replies.map(r => slackApi.refine({
      context_type: 'draft', original_result: r.english, adjustment_instruction: instruction, conversation_history: [],
    })));
    return {
      ...group, created_at: Date.now(), kind: 'adjust', instruction: label,
      replies: group.replies.map((r, i) => ({ ...r, english: refined[i].refined_result.trim() || r.english })),
    };
  });

  const saveMeaning = () => run('改写', async () => {
    if (!group || !editing) return null;
    const updated = await refineVersion(editing.version, editing.chinese);
    setEditing(null);
    return {
      ...group, created_at: Date.now(), kind: 'edit', instruction: `改了 ${editing.version} 的意思`,
      replies: group.replies.map(r => (r.version === editing.version
        ? { version: r.version, english: updated.english, chinese: updated.chinese || editing.chinese }
        : r)),
    };
  });

  // 对方有未读新消息：打开就自动生成一次（这批消息生成过就不再生成）
  const autoDone = useRef(false);
  useEffect(() => {
    if (autoDone.current || !stateQuery.isSuccess || !ctx.data || !hasUnreads || !pendingMessages.length) return;
    const latest = ctx.data.latest_ts;
    const last = state.groups.at(-1);
    if (last?.based_on_ts && latest && parseFloat(last.based_on_ts) >= parseFloat(latest)) return;
    autoDone.current = true;
    window.setTimeout(() => void generate(), 0);
  });

  const copy = async (text: string, openSlack: boolean) => {
    if (await copyToClipboard(text)) {
      toast.success(openSlack ? '已复制，正在打开 Slack' : '已复制');
      if (openSlack) window.open(slackLink, '_blank', 'noopener');
    } else {
      toast.error('复制失败，请手动选中复制');
    }
  };

  if (stateQuery.isLoading || ctx.isLoading) {
    return <div className="flex h-full items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>;
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="min-h-0 flex-1 space-y-3 overflow-auto px-4 py-4">
        {hasNew && (
          <div className="flex items-center gap-2 rounded-lg border border-warning/30 bg-warning-light px-3 py-2 text-xs text-text-primary">
            <span className="flex-1">对方又发了新消息</span>
            <button type="button" onClick={() => void generate()} className="font-medium text-primary-700 hover:underline">重新生成</button>
          </div>
        )}

        {!group && (
          <div className="rounded-xl border border-dashed border-border bg-white/60 px-4 py-6 text-center">
            <Sparkles className="mx-auto h-6 w-6 text-primary-400" />
            {pendingMessages.length > 0 ? (
              <>
                <p className="mt-2 text-sm text-text-primary">对方有 {pendingMessages.length} 条消息等你回</p>
                <button
                  type="button"
                  onClick={() => void generate()}
                  disabled={!!busy}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-primary-500 px-3.5 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-primary-600 disabled:opacity-60"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />} 帮我回复
                </button>
              </>
            ) : (
              <p className="mt-2 text-sm text-text-muted">最后一条是你发的，目前不需要回复。<br />想主动说什么，在下面写中文。</p>
            )}
          </div>
        )}

        {group && (
          <>
            {group.understanding && (
              <section className="rounded-xl border border-primary-100 bg-gradient-to-br from-primary-50/80 to-white px-4 py-3 shadow-sm">
                <div className="mb-1 text-xs font-semibold text-primary-700">对方要什么</div>
                <p className="text-sm leading-relaxed text-text-primary">{group.understanding}</p>
              </section>
            )}
            {group.instruction && group.kind !== 'generate' && (
              <div className="text-xs text-text-muted">
                {group.kind === 'compose' ? `按你的意思：「${group.instruction}」` : group.kind === 'adjust' ? `调整：${group.instruction}` : group.instruction}
              </div>
            )}
            {group.replies.map(r => (
              <section key={r.version} className="rounded-xl border border-border-subtle bg-white px-4 py-3 shadow-sm">
                <div className="mb-1.5 flex items-center gap-2">
                  <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary-100 text-[11px] font-semibold text-primary-700">{r.version}</span>
                  <span className="text-xs font-medium text-text-secondary">{LABELS[r.version] ?? ''}</span>
                  <div className="ml-auto flex items-center gap-1">
                    <button type="button" onClick={() => void copy(r.english, false)}
                      className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-text-secondary hover:bg-bg-hover">
                      <Copy className="h-3.5 w-3.5" /> 复制
                    </button>
                    <button type="button" onClick={() => void copy(r.english, true)}
                      className="inline-flex items-center gap-1 rounded-md bg-primary-50 px-2 py-1 text-xs font-medium text-primary-700 hover:bg-primary-100">
                      <ExternalLink className="h-3.5 w-3.5" /> 复制并打开 Slack
                    </button>
                  </div>
                </div>
                <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-text-primary">{r.english}</p>
                {editing?.version === r.version ? (
                  <div className="mt-2 space-y-2">
                    <textarea
                      value={editing.chinese}
                      onChange={e => setEditing({ version: r.version, chinese: e.target.value })}
                      rows={2}
                      autoFocus
                      className="w-full resize-none rounded-md border border-primary-200 px-2.5 py-1.5 text-sm outline-none focus:ring-2 focus:ring-primary-100"
                    />
                    <div className="flex justify-end gap-2">
                      <button type="button" onClick={() => setEditing(null)} className="rounded-md px-2.5 py-1 text-xs text-text-muted hover:bg-bg-hover">取消</button>
                      <button type="button" onClick={() => void saveMeaning()} disabled={!!busy}
                        className="inline-flex items-center gap-1 rounded-md bg-primary-500 px-2.5 py-1 text-xs font-medium text-white hover:bg-primary-600">
                        {busy === '改写' ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />} 按这个意思重写
                      </button>
                    </div>
                  </div>
                ) : (
                  <button type="button" onClick={() => setEditing({ version: r.version, chinese: r.chinese })}
                    className="group mt-1.5 flex w-full items-start gap-1 text-left text-xs text-text-muted hover:text-text-secondary"
                    title="改中文意思，只重写这一版英文">
                    <span className="flex-1">{r.chinese}</span>
                    <Pencil className="mt-0.5 h-3 w-3 shrink-0 opacity-0 group-hover:opacity-100" />
                  </button>
                )}
              </section>
            ))}
          </>
        )}
      </div>

      <div className="space-y-2 border-t border-border-subtle bg-white/80 px-4 py-3">
        {group && (
          <div className="flex flex-wrap items-center gap-1.5">
            <Wand2 className="h-3.5 w-3.5 text-primary-400" />
            {ADJUSTMENTS.map(a => (
              <button key={a.label} type="button" onClick={() => void adjust(a.label, a.instruction)} disabled={!!busy}
                className="rounded-full border border-border-subtle bg-white px-2.5 py-0.5 text-xs text-text-secondary transition-colors hover:border-primary-200 hover:text-primary-700 disabled:opacity-50">
                {busy === a.label ? <Loader2 className="inline h-3 w-3 animate-spin" /> : a.label}
              </button>
            ))}
            {pendingMessages.length > 0 && (
              <button type="button" onClick={() => void generate()} disabled={!!busy} title="按对方的消息重新生成"
                className="ml-auto rounded-md p-1 text-text-muted hover:bg-bg-hover hover:text-text-primary">
                <RefreshCw className={cn('h-3.5 w-3.5', busy === '生成' && 'animate-spin')} />
              </button>
            )}
          </div>
        )}
        <div className="flex items-end gap-2">
          <textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                void compose();
              }
            }}
            rows={2}
            placeholder="我想说……（写中文意思，比如：可以用，但要注明数据截至 11 月）"
            aria-label="我想说"
            className="min-w-0 flex-1 resize-none rounded-lg border border-border-subtle bg-white px-3 py-2 text-sm outline-none focus:border-primary-200 focus:ring-2 focus:ring-primary-50"
          />
          <button type="button" onClick={() => void compose()} disabled={!draft.trim() || !!busy} title="按这个意思出三版（Ctrl+Enter）"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-500 text-white shadow-sm hover:bg-primary-600 disabled:opacity-50">
            {busy === '生成' && draft ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
        {state.groups.length > 1 && (
          <div className="flex items-center justify-center gap-2 text-xs text-text-muted">
            <button type="button" disabled={state.current <= 0} onClick={() => void save({ ...state, current: state.current - 1 })}
              className="rounded p-0.5 hover:bg-bg-hover disabled:opacity-30" aria-label="上一组"><ChevronLeft className="h-4 w-4" /></button>
            第 {state.current + 1} 组 / 共 {state.groups.length} 组
            <button type="button" disabled={state.current >= state.groups.length - 1} onClick={() => void save({ ...state, current: state.current + 1 })}
              className="rounded p-0.5 hover:bg-bg-hover disabled:opacity-30" aria-label="下一组"><ChevronRight className="h-4 w-4" /></button>
          </div>
        )}
      </div>
    </div>
  );
}
