import { useEffect, useRef, useState } from 'react';
import { ArrowUp, Check, Copy, Loader2, MessageSquarePlus, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import { ModelSelector } from '@/components/ModelSelector';
import { Button } from '@/components/ui/Button';
import { renderMarkdown } from '@/features/skills/markdown';
import '@/features/skills/styles.css';
import { cn } from '@/lib/utils';
import { copyToClipboard } from '@/shared/utils';
import { PageActions } from '@/components/layout/HeaderSlot';
import { chatApi } from './api';
import { useChatStore, type ChatMessage } from './chatStore';

const EXAMPLES = [
  '用三句话解释 HBM 和 GDDR 的区别',
  '帮我把这段话改得更口语一点：',
  'CoWoS 产能为什么会卡住 AI 芯片出货？',
];

const newId = () => (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`);

/**
 * Chatbot 页：普通的 AI 对话。走后端 API（默认 GPT-6.2 Sol），整段对话每次一起发，回复按 Markdown 显示。
 * 模型选择和「新对话」在全站顶栏右侧，和其他页面一样。
 */
export function ChatFeature() {
  const { messages, model, draft, add, removeFrom, setModel, setDraft, clear } = useChatStore();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages.length, pending]);

  const ask = async (history: ChatMessage[]) => {
    setPending(true);
    setError(null);
    try {
      const { reply } = await chatApi.send({
        messages: history.map(({ role, content }) => ({ role, content })),
        model: model || undefined,
      });
      add({ id: newId(), role: 'assistant', content: reply });
    } catch (e) {
      setError(e instanceof Error ? e.message : '没有拿到回复');
    } finally {
      setPending(false);
      inputRef.current?.focus();
    }
  };

  const send = (text = draft) => {
    const content = text.trim();
    if (!content || pending) return;
    const message: ChatMessage = { id: newId(), role: 'user', content };
    add(message);
    setDraft('');
    void ask([...messages, message]);
  };

  // 出错后重试：最后一条一定是用户消息，原样再问一次
  const retry = () => void ask(messages);

  // 重新生成最后一条回复
  const regenerate = (id: string) => {
    const index = messages.findIndex(message => message.id === id);
    if (index < 0) return;
    const history = messages.slice(0, index);
    removeFrom(id);
    void ask(history);
  };

  return (
    <section className="flex h-full min-h-0 flex-col">
      <h1 className="sr-only">Chatbot</h1>
      <PageActions>
        <div className="w-40 sm:w-48" title="对话用的模型">
          <ModelSelector value={model} onChange={value => setModel(value)} className="h-9 text-sm" disabled={pending} />
        </div>
        <Button variant="ghost" size="sm" className="h-9" onClick={() => { clear(); setError(null); inputRef.current?.focus(); }}
          disabled={pending || (!messages.length && !draft)}>
          <MessageSquarePlus /><span className="hidden sm:inline">新对话</span>
        </Button>
      </PageActions>

      <div ref={listRef} className="min-h-0 flex-1 overflow-y-auto px-3 py-6 sm:px-6" aria-live="polite">
        {messages.length === 0 && !pending ? (
          <div className="mx-auto flex h-full max-w-md flex-col items-center justify-center text-center">
            <p className="text-2xl text-text-primary [font-family:var(--font-display)]">有什么想问的？</p>
            <p className="mt-1 text-sm text-text-muted">什么都可以问，回答默认用中文。</p>
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {EXAMPLES.map(example => (
                <button key={example} type="button"
                  onClick={() => { if (example.endsWith('：')) { setDraft(example); inputRef.current?.focus(); } else send(example); }}
                  className="rounded-full border border-border-subtle bg-bg-tertiary/50 px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-primary-200 hover:bg-paper-hover hover:text-text-primary">
                  {example}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-5">
            {messages.map((message, index) => (
              <Bubble key={message.id} message={message}
                onRegenerate={!pending && index === messages.length - 1 && message.role === 'assistant' ? () => regenerate(message.id) : undefined} />
            ))}
            {pending && (
              <div className="flex items-center gap-2 text-sm text-text-muted">
                <Loader2 className="h-4 w-4 animate-spin" />正在想…
              </div>
            )}
            {error && !pending && (
              <div className="flex flex-wrap items-center gap-3 rounded-lg bg-error-light/60 px-3 py-2 text-sm text-error">
                <span className="min-w-0 flex-1">没拿到回复：{error}</span>
                <Button variant="outline" size="sm" onClick={retry}><RotateCcw />重试</Button>
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
                send();
              }
            }}
            rows={1}
            maxLength={20000}
            placeholder="输入消息，Enter 发送，Shift+Enter 换行"
            aria-label="输入消息"
            className="max-h-48 min-h-9 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm leading-6 text-text-primary outline-none [field-sizing:content] placeholder:text-text-disabled"
          />
          <Button size="icon" className="h-9 w-9 shrink-0 rounded-lg" onClick={() => send()} disabled={!draft.trim() || pending} aria-label="发送">
            {pending ? <Loader2 className="animate-spin" /> : <ArrowUp />}
          </Button>
        </div>
      </footer>
    </section>
  );
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
