import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ArrowUp, Check, Copy, Globe, History, Info, Loader2, MessageSquarePlus, Pencil, RotateCcw, Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { ModelSelector } from '@/components/ModelSelector';
import { Button } from '@/components/ui/Button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { renderMarkdown } from '@/features/skills/markdown';
import '@/features/skills/styles.css';
import { cn } from '@/lib/utils';
import { copyToClipboard } from '@/shared/utils';
import { confirmAction } from '@/shared/ui/confirm';
import { PageActions } from '@/components/layout/HeaderSlot';
import { chatApi, type ChatMessage, type ChatSession, type ChatSessionSummary } from './api';
import { useChatStore } from './chatStore';

const EXAMPLES = [
  '今天科技圈有什么新闻？',
  '帮我把这段话改得更口语一点：',
  'CoWoS 产能为什么会卡住 AI 芯片出货？',
];

const errorText = (e: unknown) => (e instanceof Error ? e.message : '没有拿到回复');

function shortTime(seconds?: number) {
  if (!seconds) return '';
  const date = new Date(seconds * 1000);
  const pad = (n: number) => String(n).padStart(2, '0');
  return date.toDateString() === new Date().toDateString()
    ? `${pad(date.getHours())}:${pad(date.getMinutes())}`
    : `${date.getMonth() + 1}-${pad(date.getDate())}`;
}

/**
 * Chatbot 页：普通的 AI 对话，可以联网搜索。会话存在服务器上（左边是会话列表，手机上收在顶栏「对话」里）；
 * 模型、联网开关和「新对话」在全站顶栏右侧。回复按 Markdown 显示，联网时下面列出引用的网页。
 */
export function ChatFeature() {
  const { currentId, model, webSearch, draft, messages: legacy, setCurrentId, setModel, setWebSearch, setDraft, clearLegacy } = useChatStore();
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [session, setSession] = useState<ChatSession | null>(null);
  // 正在等回复的会话（还没建好的新对话记作 'new'），以及先显示出来的那句问题
  const [pendingFor, setPendingFor] = useState<string | null>(null);
  const [pendingQuestion, setPendingQuestion] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [listOpen, setListOpen] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const currentRef = useRef(currentId);
  const loadedRef = useRef<string | null>(null);
  useEffect(() => { currentRef.current = currentId; }, [currentId]);
  useEffect(() => { loadedRef.current = session?.id ?? null; }, [session]);

  const pending = pendingFor !== null && pendingFor === (currentId ?? 'new');
  // 一次只等一个回复：别的对话在等时，这里也先不发
  const busy = pendingFor !== null;
  const messages = session && session.id === currentId ? session.messages : [];

  const refreshList = useCallback(async () => {
    try {
      setSessions((await chatApi.list()).sessions);
    } catch {
      // 列表刷新失败不打扰，下次操作再刷
    }
  }, []);

  // 打开页面：旧版存在浏览器里的对话导入成一个会话，然后读会话列表
  useEffect(() => {
    void (async () => {
      if (legacy.length) {
        try {
          const imported = await chatApi.create(legacy.map(({ role, content }) => ({ role, content })));
          clearLegacy();
          setCurrentId(imported.id);
        } catch {
          // 导入失败下次打开再试
        }
      }
      await refreshList();
    })();
    // 只在打开页面时跑一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 切换会话：读这个会话的消息；已经被删掉就回到新对话
  useEffect(() => {
    // 刚建好的新对话已经在手上了，不再读（免得读回来的旧内容盖掉随后到的回复）
    if (!currentId || loadedRef.current === currentId) return;
    let cancelled = false;
    chatApi.get(currentId).then(doc => { if (!cancelled) setSession(doc); }).catch(() => {
      if (!cancelled) setCurrentId(null);
    });
    return () => { cancelled = true; };
  }, [currentId, setCurrentId]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages.length, pending, currentId]);

  const options = () => ({ model: model || undefined, web_search: webSearch });

  /** 发请求等回复；回来时用户已经切到别的会话，就只刷新列表 */
  const run = async (id: string, request: () => Promise<ChatSession>) => {
    setPendingFor(id);
    setError(null);
    try {
      const doc = await request();
      if (currentRef.current === id) setSession(doc);
    } catch (e) {
      if (currentRef.current === id) {
        setError(errorText(e));
        // 问题已经存在服务器上了：重新读一遍显示出来，点「重试」再答
        chatApi.get(id).then(doc => { if (currentRef.current === id) setSession(doc); }).catch(() => undefined);
      }
    } finally {
      setPendingFor(null);
      setPendingQuestion(null);
      void refreshList();
      inputRef.current?.focus();
    }
  };

  const send = async (text = draft) => {
    const content = text.trim();
    if (!content || busy) return;
    setDraft('');
    setError(null);
    setPendingQuestion(content);
    let id = currentId;
    if (!id) {
      setPendingFor('new');
      try {
        const created = await chatApi.create();
        id = created.id;
        currentRef.current = id;
        loadedRef.current = id;
        setSession(created);
        setCurrentId(id);
      } catch (e) {
        setPendingFor(null);
        setPendingQuestion(null);
        setDraft(content);
        setError(errorText(e));
        return;
      }
    }
    const target = id;
    await run(target, () => chatApi.send(target, content, options()));
  };

  // 重新回答最后一条，或出错后重试：后端去掉最后一个问题后面的回复，再答一次
  const reply = (dropLast: boolean) => {
    if (!currentId || busy) return;
    if (dropLast && session) setSession({ ...session, messages: session.messages.slice(0, -1) });
    const id = currentId;
    void run(id, () => chatApi.reply(id, options()));
  };

  const startNew = () => {
    setCurrentId(null);
    setError(null);
    setListOpen(false);
    inputRef.current?.focus();
  };

  const open = (id: string) => {
    if (id !== currentId) setError(null);
    setCurrentId(id);
    setListOpen(false);
  };

  const rename = async (id: string, title: string) => {
    try {
      const doc = await chatApi.rename(id, title);
      if (session?.id === id) setSession(doc);
      await refreshList();
    } catch (e) {
      toast.error(`改名没成功：${errorText(e)}`);
    }
  };

  const remove = async (item: ChatSessionSummary) => {
    const ok = await confirmAction({ title: `删除对话「${item.title}」？`, description: '删除后找不回来。', confirmLabel: '删除', destructive: true });
    if (!ok) return;
    try {
      await chatApi.remove(item.id);
      if (item.id === currentId) setCurrentId(null);
      await refreshList();
    } catch (e) {
      toast.error(`删除没成功：${errorText(e)}`);
    }
  };

  const list = (
    <SessionList sessions={sessions} currentId={currentId} busyId={pendingFor} onOpen={open} onRename={rename} onRemove={remove} />
  );
  const shown: ChatMessage[] = pendingQuestion && pending
    ? [...messages, { id: 'pending', role: 'user', content: pendingQuestion }]
    : messages;
  const last = shown[shown.length - 1];

  return (
    <section className="flex h-full min-h-0">
      <h1 className="sr-only">Chatbot</h1>
      <PageActions>
        <Sheet open={listOpen} onOpenChange={setListOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="sm" className="h-9 md:hidden" aria-label="对话列表"><History /></Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 p-0">
            <SheetHeader className="px-4 pt-4"><SheetTitle className="text-base">对话</SheetTitle></SheetHeader>
            <div className="min-h-0 flex-1 overflow-y-auto p-2">{list}</div>
          </SheetContent>
        </Sheet>
        <div className="w-36 sm:w-48 lg:w-40 xl:w-48" title="对话用的模型">
          <ModelSelector value={model} onChange={value => setModel(value)} className="h-9 text-sm" disabled={pending} />
        </div>
        <Button variant={webSearch ? 'secondary' : 'ghost'} size="sm" className="h-9" aria-pressed={webSearch}
          onClick={() => setWebSearch(!webSearch)}
          title={webSearch ? '联网搜索已开：需要最新信息时模型会自己去搜' : '联网搜索已关：只用模型自己知道的'}>
          <Globe /><span className="hidden sm:inline lg:hidden xl:inline">联网</span>
        </Button>
        <Button variant="ghost" size="sm" className="h-9" onClick={startNew} disabled={!currentId && !draft}>
          <MessageSquarePlus /><span className="hidden sm:inline lg:hidden xl:inline">新对话</span>
        </Button>
      </PageActions>

      <aside className="hidden w-60 shrink-0 flex-col border-r border-border-subtle md:flex" aria-label="对话列表">
        <div className="min-h-0 flex-1 overflow-y-auto p-2">{list}</div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <div ref={listRef} className="min-h-0 flex-1 overflow-y-auto px-3 py-6 sm:px-6" aria-live="polite">
          {shown.length === 0 && !pending ? (
            <div className="mx-auto flex h-full max-w-md flex-col items-center justify-center text-center">
              <p className="text-2xl text-text-primary [font-family:var(--font-display)]">有什么想问的？</p>
              <p className="mt-1 text-sm text-text-muted">
                什么都可以问，回答默认用中文{webSearch ? '；需要最新信息时会联网搜索' : ''}。
              </p>
              <div className="mt-5 flex flex-wrap justify-center gap-2">
                {EXAMPLES.map(example => (
                  <button key={example} type="button"
                    onClick={() => { if (example.endsWith('：')) { setDraft(example); inputRef.current?.focus(); } else void send(example); }}
                    className="rounded-full border border-border-subtle bg-bg-tertiary/50 px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-primary-200 hover:bg-paper-hover hover:text-text-primary">
                    {example}
                  </button>
                ))}
              </div>
              {error && <p className="mt-4 text-sm text-error">没发出去：{error}</p>}
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-5">
              {shown.map(message => (
                <Bubble key={message.id} message={message}
                  onRegenerate={!busy && message === last && message.role === 'assistant' ? () => reply(true) : undefined} />
              ))}
              {pending && (
                <div className="flex items-center gap-2 text-sm text-text-muted">
                  <Loader2 className="h-4 w-4 animate-spin" />{webSearch ? '正在想，需要时会联网搜索…' : '正在想…'}
                </div>
              )}
              {error && !pending && (
                <div className="flex flex-wrap items-center gap-3 rounded-lg bg-error-light/60 px-3 py-2 text-sm text-error">
                  <span className="min-w-0 flex-1">没拿到回复：{error}</span>
                  {last?.role === 'user' && <Button variant="outline" size="sm" onClick={() => reply(false)}><RotateCcw />重试</Button>}
                </div>
              )}
            </div>
          )}
        </div>

        <footer className="shrink-0 px-3 pb-4 pt-2 sm:px-6">
          <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-border bg-white p-2 shadow-paper focus-within:border-primary-400 focus-within:ring-[3px] focus-within:ring-primary-500/12">
            <textarea
              ref={inputRef}
              value={draft}
              onChange={event => setDraft(event.target.value)}
              onKeyDown={event => {
                // Enter 发送，Shift+Enter 换行；输入法选字时的 Enter 不算
                if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                  event.preventDefault();
                  void send();
                }
              }}
              rows={1}
              maxLength={20000}
              placeholder="输入消息，Enter 发送，Shift+Enter 换行"
              aria-label="输入消息"
              className="max-h-48 min-h-9 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm leading-6 text-text-primary outline-none [field-sizing:content] placeholder:text-text-disabled"
            />
            <Button size="icon" className="h-9 w-9 shrink-0 rounded-lg" onClick={() => void send()} disabled={!draft.trim() || busy} aria-label="发送">
              {busy ? <Loader2 className="animate-spin" /> : <ArrowUp />}
            </Button>
          </div>
        </footer>
      </div>
    </section>
  );
}

function SessionList({ sessions, currentId, busyId, onOpen, onRename, onRemove }: {
  sessions: ChatSessionSummary[];
  currentId: string | null;
  busyId: string | null;
  onOpen: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onRemove: (item: ChatSessionSummary) => void;
}) {
  const [editing, setEditing] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  if (!sessions.length) return <p className="px-2 py-3 text-xs text-text-muted">还没有对话，发一条消息就会出现在这里。</p>;
  const save = (id: string) => {
    const next = title.trim();
    setEditing(null);
    if (next && next !== sessions.find(s => s.id === id)?.title) onRename(id, next);
  };
  return (
    <ul className="space-y-0.5">
      {sessions.map(item => (
        <li key={item.id}>
          {editing === item.id ? (
            <input autoFocus value={title} maxLength={40} aria-label="对话标题"
              onChange={event => setTitle(event.target.value)}
              onBlur={() => save(item.id)}
              onKeyDown={event => {
                if (event.key === 'Enter' && !event.nativeEvent.isComposing) save(item.id);
                if (event.key === 'Escape') setEditing(null);
              }}
              className="h-9 w-full rounded-md border border-primary-300 bg-white px-2 text-sm outline-none" />
          ) : (
            <div className={cn('group flex items-center rounded-md text-sm',
              item.id === currentId ? 'bg-primary-50 text-primary-700' : 'text-text-secondary hover:bg-bg-hover hover:text-text-primary')}>
              <button type="button" onClick={() => onOpen(item.id)} className="flex min-w-0 flex-1 items-center gap-2 px-2.5 py-2 text-left">
                <span className="min-w-0 flex-1 truncate">{item.title}</span>
                {busyId === item.id
                  ? <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-text-muted" />
                  : <span className="shrink-0 text-[11px] text-text-muted group-hover:hidden">{shortTime(item.updated_at)}</span>}
              </button>
              <div className="hidden shrink-0 pr-1 group-hover:flex">
                <button type="button" title="改名" aria-label={`改名：${item.title}`} onClick={() => { setTitle(item.title); setEditing(item.id); }}
                  className="rounded p-1 text-text-muted hover:bg-ink-wash hover:text-text-primary"><Pencil className="h-3.5 w-3.5" /></button>
                <button type="button" title="删除" aria-label={`删除：${item.title}`} onClick={() => onRemove(item)}
                  className="rounded p-1 text-text-muted hover:bg-ink-wash hover:text-error"><Trash2 className="h-3.5 w-3.5" /></button>
              </div>
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}

function hostOf(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

function Bubble({ message, onRegenerate }: { message: ChatMessage; onRegenerate?: () => void }) {
  const [copied, setCopied] = useState(false);
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-primary-50 px-4 py-2.5 text-sm leading-relaxed text-text-primary">
          {message.content}
        </div>
      </div>
    );
  }
  const copy = async () => {
    if (await copyToClipboard(message.content)) {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } else {
      toast.error('复制失败，请手动选中复制');
    }
  };
  return (
    <div className="group">
      <div className="skill-md text-[15px] text-text-primary" dangerouslySetInnerHTML={{ __html: renderMarkdown(message.content) }} />
      {!!message.sources?.length && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5 text-xs">
          <span className="text-text-muted">来源</span>
          {message.sources.map((source, index) => (
            <a key={source.url} href={source.url} target="_blank" rel="noreferrer noopener" title={source.title}
              className="max-w-[16rem] truncate rounded-full border border-border-subtle px-2 py-0.5 text-text-secondary hover:border-primary-200 hover:text-text-primary">
              {index + 1}. {source.title && source.title !== source.url ? source.title : hostOf(source.url)}
            </a>
          ))}
        </div>
      )}
      {message.note && (
        <p className="mt-2 flex items-center gap-1 text-xs text-text-muted"><Info className="h-3.5 w-3.5" />{message.note}</p>
      )}
      <div className={cn('mt-1.5 flex gap-1 text-text-muted transition-opacity sm:opacity-0 sm:group-hover:opacity-100', onRegenerate && 'sm:opacity-100')}>
        <button type="button" onClick={() => void copy()} className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-xs hover:bg-ink-wash hover:text-text-primary">
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}{copied ? '已复制' : '复制'}
        </button>
        {onRegenerate && (
          <button type="button" onClick={onRegenerate} className="inline-flex h-7 items-center gap-1 rounded-md px-2 text-xs hover:bg-ink-wash hover:text-text-primary">
            <RotateCcw className="h-3.5 w-3.5" />重新回答
          </button>
        )}
      </div>
    </div>
  );
}
