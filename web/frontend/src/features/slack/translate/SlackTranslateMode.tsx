import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, CheckCircle2, Circle, Copy, Download, ImageOff, Loader2, RotateCcw, Send, X } from 'lucide-react';
import { toast } from 'sonner';
import { ModelSelector } from '@/components/ModelSelector';
import { ResizablePanes } from '@/components/layout/ResizablePanes';
import { Button } from '@/components/ui/Button';
import { copyToClipboard } from '@/shared/utils';
import { createPostStore, type PostStoreHook } from '@/shared/stores/postStore';
import { WorkColumn } from '@/features/post';
import { DiscardEditDialog, PendingChip, SaveState } from '@/features/post/components/WorkspaceChrome';
import { draftKeys, draftsApi, useDraftSync, type DraftDoc, type DraftImage } from '@/features/post/drafts';
import { usePostWorkspace } from '@/features/post/usePostWorkspace';
import { MessageItem } from '../inbox/MessageItem';
import { useSlackReplies } from '../inbox/hooks';

// 每篇帖子一份工作区 store，放模块里：切走再回来（组件重新挂载）内容和进行中的请求都还在
const stores = new Map<string, PostStoreHook>();
function storeFor(key: string) {
  let store = stores.get(key);
  if (!store) {
    store = createPostStore();
    stores.set(key, store);
  }
  return store;
}

/**
 * Slack 翻译模式：① 原文 + 配图 | ② 译文 / 优化 / 标题（和帖子翻译页同一套）| ③ 原 thread。
 * 三栏都能收起、能拖宽。第一次打开自动跑「提取 → 翻译 → 标题」，之后所有修改自动存进翻译稿（翻译记录）。
 */
export function SlackTranslateMode({ channelId, threadTs, channelName, onExit }: {
  channelId: string;
  threadTs: string;
  channelName: string;
  onExit: () => void;
}) {
  const key = `${channelId}:${threadTs}`;
  const store = storeFor(key);
  const ws = usePostWorkspace(store);
  const queryClient = useQueryClient();
  const replies = useSlackReplies(channelId, threadTs);
  const draftQuery = useQuery({
    queryKey: draftKeys.slack(channelId, threadTs),
    queryFn: () => draftsApi.slack(channelId, threadTs),
    select: data => data.draft,
    staleTime: Infinity,
  });
  const [doc, setDoc] = useState<DraftDoc | null>(null);
  const [images, setImages] = useState<DraftImage[]>([]);
  const [status, setStatus] = useState<'draft' | 'done'>('draft');
  const [sentAt, setSentAt] = useState<number | null>(null);
  const [sentBusy, setSentBusy] = useState(false);
  const [running, setRunning] = useState(false);
  const [instruction, setInstruction] = useState('');
  const [picking, setPicking] = useState(false);
  const draftId = store(state => state.draftId);
  const sync = useDraftSync(store, { enabled: !!doc, extra: () => ({ images, status, seen: true }) });

  const load = (next: DraftDoc) => {
    setDoc(next);
    setImages(next.images);
    setStatus(next.status);
    setSentAt(next.sent_at ?? null);
    store.getState().loadSnapshot(next.state, next.id, next.rev);
    sync.markLoaded();
    queryClient.setQueryData(draftKeys.slack(channelId, threadTs), { draft: next });
  };

  const run = async (text?: string) => {
    if (running) return;
    setRunning(true);
    try {
      await sync.flush();
      load(await draftsApi.runSlack(channelId, threadTs, text));
      setInstruction('');
      void queryClient.invalidateQueries({ queryKey: ['slack-inbox', 'activity'] });
      void queryClient.invalidateQueries({ queryKey: ['post-drafts'] });
    } catch (error) {
      toast.error(error instanceof Error ? `没翻出来：${error.message}` : '没翻出来');
    } finally {
      setRunning(false);
    }
  };

  // 第一次进来：没有稿子就自动跑一遍；有稿子就载入（自动翻好的顺手标成「看过了」）
  const started = useRef(false);
  const ready = !draftQuery.isLoading && !draftQuery.isError;
  const existing = draftQuery.data;
  useEffect(() => {
    if (!ready || started.current) return;
    const timer = window.setTimeout(() => {
      if (started.current) return;
      started.current = true;
      if (!existing) {
        void run();
        return;
      }
      const current = store.getState();
      if (current.draftId === existing.id && (current.draftRev ?? 0) >= existing.rev) {
        setDoc(existing);
        setImages(existing.images);
        setStatus(existing.status);
        setSentAt(existing.sent_at ?? null);
      } else {
        load(existing);
      }
      if (existing.auto && !existing.seen) window.setTimeout(() => void sync.flush(), 0);
    }, 0);
    return () => window.clearTimeout(timer);
    // 只在稿子查询有结果时跑一次；run / load / sync 每次渲染都是新函数，不能放进依赖
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, existing]);

  const toggleImage = (id: string, name: string) => {
    setImages(prev => (prev.some(i => i.id === id) ? prev.filter(i => i.id !== id) : [...prev, { id, name }]));
    sync.schedule();
  };
  const moveImage = (index: number, dir: -1 | 1) => {
    setImages(prev => {
      const next = [...prev];
      const j = index + dir;
      if (j < 0 || j >= next.length) return prev;
      [next[index], next[j]] = [next[j], next[index]];
      return next;
    });
    sync.schedule();
  };

  const toggleDone = () => {
    setStatus(s => (s === 'done' ? 'draft' : 'done'));
    sync.schedule();
    toast.success(status === 'done' ? '已改回草稿' : '已标记完成');
  };

  /** 已发送和「标记完成」分开：发出去之后点；先把正在改的存好，后端记下的译文才是发出去的那版 */
  const setSent = async (sent: boolean) => {
    if (!draftId || sentBusy) return;
    setSentBusy(true);
    try {
      if (sent) await sync.flush();
      const result = await draftsApi.setSent(draftId, sent);
      setSentAt(result.sent_at);
      void queryClient.invalidateQueries({ queryKey: ['post-drafts'] });
      void queryClient.invalidateQueries({ queryKey: ['slack-inbox', 'activity'] });
      toast.success(sent ? '已标记为已发送' : '已撤销「已发送」');
    } catch (error) {
      toast.error(`没保存上：${error instanceof Error ? error.message : '请重试'}`);
    } finally {
      setSentBusy(false);
    }
  };

  const downloadZip = async () => {
    await sync.flush();
    if (draftId) window.location.href = draftsApi.imagesZipUrl(draftId);
  };

  const copyWithTitle = async () => {
    const title = ws.selectedTitle || ws.generatedTitles[0] || '';
    const text = title ? `${title}\n\n${ws.currentContent}` : ws.currentContent;
    if (await copyToClipboard(text)) {
      // 复制了不等于发了，不自动标；顺手给个按钮
      toast.success(title ? '标题和译文已复制' : '译文已复制', sentAt || !draftId ? undefined : {
        action: { label: '标记已发送', onClick: () => void setSent(true) }, duration: 8000,
      });
    }
  };

  const extraction = doc?.extraction;
  const usedTs = new Set(extraction?.message_ts ?? []);
  const messages = replies.data?.messages ?? [];
  const title = doc?.slack?.title || (messages[0]?.text ?? '').split('\n')[0] || 'Slack 帖子';
  const hasNew = !!extraction?.latest_ts && messages.length > 0
    && parseFloat(messages[messages.length - 1].ts) > parseFloat(extraction.latest_ts);

  // 改了原文、还没按新原文翻：提示「按这段原文重新翻译」
  const sourceChanged = !!ws.currentVersion && ws.originalText.trim() !== ws.currentVersion.sourceText.trim();

  const sourcePane = (
    <div className="flex min-h-full flex-col gap-5 px-4 py-4">
      {running && !doc && (
        <div className="rounded-xl bg-primary-50/60 px-4 py-8 text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-primary-500" />
          <p className="mt-3 text-sm font-medium text-text-primary">正在从 Slack 原帖里找出要发的帖子</p>
          <p className="mt-1 text-xs text-text-muted">找原文和配图 → 翻译 → 起标题，大约 15 秒</p>
        </div>
      )}

      {extraction && !extraction.has_post && (
        <div className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-medium">这个 thread 里没找到要发的帖子</p>
          <p className="mt-1 text-[13px] leading-relaxed">{extraction.note}</p>
        </div>
      )}

      {/* 1. 要翻译的英文：AI 从原帖里挑出来的，可以直接改 */}
      <section>
        <h3 className="mb-2 text-sm font-semibold text-text-primary">要翻译的英文</h3>
        <textarea
          id="postSourceInput"
          value={ws.originalText}
          onChange={e => ws.setOriginalText(e.target.value)}
          aria-label="帖子原文"
          placeholder={running ? '正在提取…' : '在这里粘贴或修改英文原文'}
          className="min-h-[220px] w-full resize-y rounded-lg border border-border-subtle bg-white px-3.5 py-3 text-[14px] leading-relaxed text-text-primary outline-none transition-colors focus:border-primary-200 focus:ring-2 focus:ring-primary-50"
        />
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {(sourceChanged || (!ws.versions.length && ws.originalText.trim())) && (
            <Button size="sm" className="h-8" onClick={() => void ws.handleTranslate()} disabled={ws.isLoading || running}>
              {ws.pendingAction === 'translate' ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              {ws.versions.length ? '按改过的原文重新翻译' : '翻译'}
            </Button>
          )}
          <button
            type="button"
            onClick={() => setPicking(v => !v)}
            className="text-xs text-text-muted underline-offset-2 hover:text-primary-700 hover:underline"
          >
            挑错了？让 AI 重新挑
          </button>
          <span className="ml-auto text-[11px] tabular-nums text-text-muted">{ws.originalText.length.toLocaleString()} 字符</span>
        </div>
        {picking && (
          <div className="mt-2 space-y-2 rounded-lg bg-bg-tertiary/70 p-3">
            {extraction?.candidates.map((c, i) => (
              <button
                key={i}
                type="button"
                onClick={() => {
                  store.getState().setOriginalText(c.source_text);
                  const byId = new Map(messages.flatMap(m => m.files).map(f => [f.id, f.name]));
                  setImages(c.image_ids.map(id => ({ id, name: byId.get(id) ?? id })));
                  setPicking(false);
                  toast.info('原文已换成这一版，点「按改过的原文重新翻译」出新译文');
                }}
                className="block w-full rounded-md bg-white px-3 py-2 text-left text-xs shadow-sm hover:ring-1 hover:ring-primary-200"
              >
                <span className="font-medium text-text-primary">换成：{c.label || `备选 ${i + 1}`}</span>
                <span className="mt-0.5 line-clamp-2 block text-text-muted">{c.source_text}</span>
              </button>
            ))}
            <div className="flex items-center gap-2">
              <input
                value={instruction}
                onChange={e => setInstruction(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') void run(instruction); }}
                placeholder="告诉 AI 怎么挑：用第一版 / 把地图那段也加上"
                aria-label="重新挑选的要求"
                disabled={running}
                className="h-8 min-w-0 flex-1 rounded-md border border-border-subtle bg-white px-2.5 text-sm outline-none focus:border-primary-200"
              />
              <Button variant="outline" size="sm" className="h-8 shrink-0" onClick={() => void run(instruction)} disabled={running}>
                {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />} 重新挑
              </Button>
            </div>
          </div>
        )}
        {hasNew && (
          <p className="mt-2 text-xs text-amber-800">
            原帖后来又有更新，可能有新版本。
            <button type="button" onClick={() => void run()} disabled={running} className="ml-1 font-medium text-primary-700 hover:underline">重新挑</button>
          </p>
        )}
      </section>

      {/* 2. 配图：按发帖顺序；在右边原帖里点图片增减 */}
      <section>
        <div className="mb-2 flex items-baseline gap-2">
          <h3 className="text-sm font-semibold text-text-primary">配图</h3>
          <span className="text-xs text-text-muted">{images.length ? `${images.length} 张，按发帖顺序` : '没有配图'}</span>
          {images.length > 0 && (
            <button type="button" onClick={() => void downloadZip()} className="ml-auto inline-flex items-center gap-1 text-xs text-primary-700 hover:underline">
              <Download className="h-3.5 w-3.5" /> 全部下载
            </button>
          )}
        </div>
        {images.length === 0 ? (
          <div className="flex items-center gap-2 rounded-lg border border-dashed border-border px-3 py-4 text-xs text-text-muted">
            <ImageOff className="h-4 w-4" /> 在右边的 Slack 原帖里点图片，就能加进配图
          </div>
        ) : (
          <>
            <div className="grid grid-cols-3 gap-2">
              {images.map((img, i) => (
                <div key={img.id} className="group relative overflow-hidden rounded-lg bg-bg-tertiary">
                  <img src={`/api/slack-inbox/files/${img.id}`} alt={img.name} loading="lazy" className="aspect-square w-full object-cover" />
                  <span className="absolute left-1.5 top-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-black/60 text-[11px] font-medium text-white">{i + 1}</span>
                  <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-gradient-to-t from-black/60 to-transparent px-1.5 pb-1.5 pt-4 opacity-0 transition-opacity group-hover:opacity-100">
                    <div className="flex gap-1">
                      <button type="button" onClick={() => moveImage(i, -1)} disabled={i === 0} className="rounded bg-white/90 px-1.5 text-[11px] disabled:opacity-40" aria-label="往前挪">←</button>
                      <button type="button" onClick={() => moveImage(i, 1)} disabled={i === images.length - 1} className="rounded bg-white/90 px-1.5 text-[11px] disabled:opacity-40" aria-label="往后挪">→</button>
                    </div>
                    <div className="flex gap-1">
                      <a href={`/api/slack-inbox/files/${img.id}?download=true`} className="rounded bg-white/90 p-1" title="下载这张" aria-label="下载这张"><Download className="h-3 w-3" /></a>
                      <button type="button" onClick={() => toggleImage(img.id, img.name)} className="rounded bg-white/90 p-1" title="不要这张" aria-label="不要这张"><X className="h-3 w-3" /></button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );

  const threadPane = (
    <div className="pb-6 pt-2">
      {replies.isLoading && <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}
      {messages.map(m => (
        <MessageItem
          key={m.ts}
          message={m}
          marked={usedTs.has(m.ts)}
          context={messages[0]?.text}
          picker={{ selected: images.map(i => i.id), onToggle: toggleImage }}
        />
      ))}
    </div>
  );

  return (
    <div className="flex h-full min-h-0 flex-col bg-background">
      {/* 翻译模式自己的细工具条：返回、标题、状态和模型（顶栏留给全站导航） */}
      <div className="flex h-10 shrink-0 items-center gap-2 border-b border-border-subtle bg-white/70 px-3">
        <Button variant="ghost" size="sm" className="h-7 shrink-0 px-2 text-text-secondary" onClick={onExit}>
          <ArrowLeft className="h-4 w-4" /> 返回 Slack
        </Button>
        <span className="h-4 w-px shrink-0 bg-border" />
        <div className="min-w-0 flex-1 truncate text-sm text-text-primary" title={title}>
          <span className="text-text-muted">#{doc?.slack?.channel_name || channelName} · </span>{title}
        </div>
        <span className="shrink-0 whitespace-nowrap"><SaveState saving={sync.saving} savedAt={sync.savedAt} hasDraft={!!draftId} /></span>
        <PendingChip ws={ws} />
        {draftId && (
          <Button variant={status === 'done' ? 'secondary' : 'ghost'} size="sm" className="h-7 shrink-0" onClick={toggleDone}>
            {status === 'done' ? <CheckCircle2 className="h-4 w-4 text-success" /> : <Circle className="h-4 w-4" />}
            {status === 'done' ? '已完成' : '标记完成'}
          </Button>
        )}
        {draftId && (
          <Button variant={sentAt ? 'secondary' : 'ghost'} size="sm" className="h-7 shrink-0" disabled={sentBusy}
            onClick={() => void setSent(!sentAt)} title={sentAt ? `发送于 ${new Date(sentAt * 1000).toLocaleString('zh-CN')}，点一下撤销` : '在 Slack 等地方发出去之后点一下'}>
            <Send className={sentAt ? 'h-4 w-4 text-primary-600' : 'h-4 w-4'} />
            {sentAt ? '已发送' : '标记已发送'}
          </Button>
        )}
        <div className="w-40 shrink-0" title="翻译和优化用的模型">
          <ModelSelector value={ws.selectedModel} onChange={ws.setSelectedModel} className="h-7 text-xs" disabled={ws.isLoading} />
        </div>
      </div>
      <ResizablePanes
        storageKey="slack-translate-panes-v1"
        mobileDefault="work"
        panes={[
          { id: 'source', title: '原文和配图', width: 420, minWidth: 300, content: sourcePane },
          {
            id: 'work',
            title: '译文',
            minWidth: 380,
            content: (
              <WorkColumn
                ws={ws}
                extraActions={
                  <Button type="button" variant="outline" size="sm" className="h-10 sm:h-9" onClick={() => void copyWithTitle()} disabled={!ws.currentContent}>
                    <Copy className="h-4 w-4" /> 连标题复制
                  </Button>
                }
              />
            ),
          },
          { id: 'thread', title: 'Slack 原帖', width: 400, minWidth: 280, content: threadPane },
        ]}
      />
      <DiscardEditDialog ws={ws} />
    </div>
  );
}
