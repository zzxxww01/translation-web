import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, CheckCircle2, Circle, Copy, Download, ImageOff, Loader2, RotateCcw, Sparkles, X } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import { ModelSelector } from '@/components/ModelSelector';
import { ResizablePanes } from '@/components/layout/ResizablePanes';
import { Button } from '@/components/ui/Button';
import { copyToClipboard } from '@/shared/utils';
import { createPostStore, type PostStoreHook } from '@/shared/stores/postStore';
import { WorkColumn } from '@/features/post';
import { SourceInput } from '@/features/post/components/SourceInput';
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
  const [running, setRunning] = useState(false);
  const [instruction, setInstruction] = useState('');
  const draftId = store(state => state.draftId);
  const sync = useDraftSync(store, { enabled: !!doc, extra: () => ({ images, status, seen: true }) });

  const load = (next: DraftDoc) => {
    setDoc(next);
    setImages(next.images);
    setStatus(next.status);
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

  const downloadZip = async () => {
    await sync.flush();
    if (draftId) window.location.href = draftsApi.imagesZipUrl(draftId);
  };

  const copyWithTitle = async () => {
    const title = ws.selectedTitle || ws.generatedTitles[0] || '';
    const text = title ? `${title}\n\n${ws.currentContent}` : ws.currentContent;
    if (await copyToClipboard(text)) toast.success(title ? '标题和译文已复制' : '译文已复制');
  };

  const extraction = doc?.extraction;
  const usedTs = new Set(extraction?.message_ts ?? []);
  const messages = replies.data?.messages ?? [];
  const title = doc?.slack?.title || (messages[0]?.text ?? '').split('\n')[0] || 'Slack 帖子';
  const hasNew = !!extraction?.latest_ts && messages.length > 0
    && parseFloat(messages[messages.length - 1].ts) > parseFloat(extraction.latest_ts);

  const sourcePane = (
    <div className="flex min-h-full flex-col gap-4 p-4">
      {running && !doc && (
        <div className="rounded-xl border border-primary-100 bg-primary-50/60 px-4 py-6 text-center">
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-primary-500" />
          <p className="mt-2 text-sm font-medium text-text-primary">正在从 thread 里找出要发的帖子</p>
          <p className="mt-1 text-xs text-text-muted">提取原文和配图 → 翻译 → 起标题，大约 15 秒</p>
        </div>
      )}
      {extraction && (
        <div className={cn(
          'rounded-xl border px-3.5 py-2.5 text-[13px] leading-relaxed',
          extraction.has_post ? 'border-primary-100 bg-gradient-to-br from-primary-50/70 to-white' : 'border-amber-200 bg-amber-50'
        )}>
          <div className="mb-0.5 flex items-center gap-1 text-xs font-semibold text-primary-700">
            <Sparkles className="h-3.5 w-3.5" /> {extraction.has_post ? 'AI 选的内容' : '这个 thread 里没有要发的帖子'}
          </div>
          <p className="text-text-primary">{extraction.note || '—'}</p>
          {extraction.has_post && usedTs.size > 0 && (
            <p className="mt-1 text-xs text-text-muted">来源：右边标了竖线的 {usedTs.size} 条消息</p>
          )}
          {extraction.candidates.length > 0 && (
            <div className="mt-2 space-y-1.5">
              <div className="text-xs text-text-muted">也可能是：</div>
              {extraction.candidates.map((c, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => {
                    store.getState().setOriginalText(c.source_text);
                    const byId = new Map(messages.flatMap(m => m.files).map(f => [f.id, f.name]));
                    setImages(c.image_ids.map(id => ({ id, name: byId.get(id) ?? id })));
                    toast.info('原文已换成这个版本，点「重新翻译」出新译文');
                  }}
                  className="block w-full rounded-lg border border-border-subtle bg-white px-2.5 py-1.5 text-left text-xs hover:border-primary-200"
                >
                  <span className="font-medium text-text-primary">{c.label || `备选 ${i + 1}`}</span>
                  <span className="mt-0.5 line-clamp-2 block text-text-muted">{c.source_text}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      {hasNew && (
        <div className="flex items-center gap-2 rounded-lg border border-warning/30 bg-warning-light px-3 py-2 text-xs">
          <span className="flex-1">thread 有更新，可能有新版本</span>
          <button type="button" onClick={() => void run()} disabled={running} className="font-medium text-primary-700 hover:underline">重新提取</button>
        </div>
      )}

      <div className="flex min-h-[260px] flex-1 flex-col">
        <SourceInput
          hideTitle
          value={ws.originalText}
          onChange={ws.setOriginalText}
          onTranslate={() => void ws.handleTranslate()}
          onClear={() => ws.setOriginalText('')}
          isLoading={ws.isLoading || running}
          isTranslating={ws.pendingAction === 'translate'}
          canClear={!!ws.originalText.trim()}
          className="min-h-[220px] flex-1 resize-none"
        />
      </div>

      <div className="flex items-center gap-2">
        <input
          value={instruction}
          onChange={e => setInstruction(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') void run(instruction); }}
          placeholder="选错了？告诉 AI：用第一版 / 把地图那段加上……"
          aria-label="重新提取的要求"
          disabled={running}
          className="h-9 min-w-0 flex-1 rounded-lg border border-border-subtle bg-white px-3 text-sm outline-none focus:border-primary-200 focus:ring-2 focus:ring-primary-50"
        />
        <Button variant="outline" size="sm" className="h-9 shrink-0" onClick={() => void run(instruction)} disabled={running}>
          {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />} 重新提取
        </Button>
      </div>

      <div className="rounded-xl border border-border-subtle bg-white p-3">
        <div className="mb-2 flex items-center gap-2">
          <span className="text-sm font-semibold text-text-primary">配图</span>
          <span className="text-xs text-text-muted">{images.length ? `${images.length} 张，按发帖顺序` : '在右边原 thread 里点图片添加'}</span>
          {images.length > 0 && (
            <button type="button" onClick={() => void downloadZip()} className="ml-auto inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-primary-700 hover:bg-primary-50">
              <Download className="h-3.5 w-3.5" /> 打包下载
            </button>
          )}
        </div>
        {images.length === 0 ? (
          <div className="flex items-center gap-2 rounded-lg bg-bg-tertiary/60 px-3 py-4 text-xs text-text-muted">
            <ImageOff className="h-4 w-4" /> 没有配图
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {images.map((img, i) => (
              <div key={img.id} className="group relative overflow-hidden rounded-lg border border-border-subtle bg-bg-tertiary">
                <img src={`/api/slack-inbox/files/${img.id}`} alt={img.name} loading="lazy" className="aspect-square w-full object-cover" />
                <span className="absolute left-1 top-1 flex h-5 w-5 items-center justify-center rounded-full bg-primary-500 text-[11px] font-semibold text-white shadow">{i + 1}</span>
                <div className="absolute inset-x-0 bottom-0 flex justify-between gap-1 bg-gradient-to-t from-black/50 p-1 opacity-0 transition-opacity group-hover:opacity-100">
                  <div className="flex gap-1">
                    <button type="button" onClick={() => moveImage(i, -1)} disabled={i === 0} className="rounded bg-white/90 px-1 text-[11px] disabled:opacity-40" aria-label="往前">←</button>
                    <button type="button" onClick={() => moveImage(i, 1)} disabled={i === images.length - 1} className="rounded bg-white/90 px-1 text-[11px] disabled:opacity-40" aria-label="往后">→</button>
                  </div>
                  <div className="flex gap-1">
                    <a href={`/api/slack-inbox/files/${img.id}?download=true`} className="rounded bg-white/90 p-0.5" title="下载这张" aria-label="下载这张"><Download className="h-3 w-3" /></a>
                    <button type="button" onClick={() => toggleImage(img.id, img.name)} className="rounded bg-white/90 p-0.5" title="不配这张" aria-label="不配这张"><X className="h-3 w-3" /></button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  const threadPane = (
    <div className="pb-6 pt-2">
      {replies.isLoading && <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-text-muted" /></div>}
      <p className="px-5 pb-2 text-xs text-text-muted">标了竖线的是用来提取原文的消息；点图片可以加入或去掉配图。</p>
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
      <div className="flex shrink-0 flex-wrap items-center gap-3 border-b border-border-subtle bg-white/80 px-4 py-2.5">
        <Button variant="ghost" size="sm" className="h-8 px-2" onClick={onExit}>
          <ArrowLeft className="h-4 w-4" /> 退出翻译
        </Button>
        <div className="min-w-0 flex-1">
          <div className="truncate text-[15px] font-semibold text-text-primary" title={title}>{title}</div>
          <div className="text-xs text-text-muted">#{doc?.slack?.channel_name || channelName} · 帖子翻译</div>
        </div>
        <SaveState saving={sync.saving} savedAt={sync.savedAt} hasDraft={!!draftId} />
        <PendingChip ws={ws} />
        {draftId && (
          <Button variant={status === 'done' ? 'secondary' : 'outline'} size="sm" className="h-8" onClick={toggleDone}>
            {status === 'done' ? <CheckCircle2 className="h-4 w-4 text-success" /> : <Circle className="h-4 w-4" />}
            {status === 'done' ? '已完成' : '标记完成'}
          </Button>
        )}
        <div className="w-48" title="翻译和优化用的模型">
          <ModelSelector value={ws.selectedModel} onChange={ws.setSelectedModel} className="h-8 text-sm" disabled={ws.isLoading} />
        </div>
      </div>
      <ResizablePanes
        storageKey="slack-translate-panes-v1"
        mobileDefault="work"
        panes={[
          { id: 'source', title: '① 原文 + 配图', width: 420, minWidth: 300, content: sourcePane },
          {
            id: 'work',
            title: '② 译文 · 优化 · 标题',
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
          { id: 'thread', title: '③ 原 thread', width: 400, minWidth: 280, content: threadPane },
        ]}
      />
      <DiscardEditDialog ws={ws} />
    </div>
  );
}
