import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowUp } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { AUTO_REPLY_MINUTES, startRun } from '../api';
import { skillKeys } from '../hooks';
import { HARNESSES, loadHarness, saveHarness, type Harness } from '../harness';
import type { Agent, RunMeta } from '../types';
import { AgentAvatar } from './AgentIcon';
import { AttachmentPicker } from './AttachmentChips';

interface NewRunFormProps {
  /** 第一个是通用 Agent，其余是专职 Agent（见 normalizeCatalog） */
  catalog: Agent[];
  maxUploadMb: number;
  onStarted: (run: RunMeta) => void;
}

/** 新对话：先选 Agent（卡片），再交代要做什么。模型和自动继续是次要选项，放在输入框下面。 */
export function NewRunForm({ catalog, maxUploadMb, onStarted }: NewRunFormProps) {
  const queryClient = useQueryClient();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [agentName, setAgentName] = useState('');
  const agent = catalog.find(item => item.name === agentName) ?? catalog[0];
  const [harness, setHarness] = useState<Harness>(() => loadHarness(agent.name, agent.harness));
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [autoReply, setAutoReply] = useState(true);
  const [progress, setProgress] = useState<number | null>(null);

  const busy = progress !== null;
  const tooLarge = files.find(file => file.size > maxUploadMb * 1024 * 1024);
  const canStart = Boolean(message.trim() || files.length > 0) && !tooLarge && !busy;

  const pickAgent = (next: Agent) => {
    setAgentName(next.name);
    setHarness(loadHarness(next.name, next.harness));
    textareaRef.current?.focus();
  };

  const pickHarness = (next: Harness) => {
    setHarness(next);
    saveHarness(agent.name, next);
  };

  const start = async () => {
    if (!canStart) return;
    setProgress(files.length ? 0 : 100);
    try {
      const run = await startRun(
        { skill: agent.name, message, files, harness, autoReplyMinutes: autoReply ? AUTO_REPLY_MINUTES : 0 },
        setProgress
      );
      await queryClient.invalidateQueries({ queryKey: skillKeys.runs });
      onStarted(run);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '没能开始');
      setProgress(null);
    }
  };

  const fillExample = (text: string) => {
    setMessage(text);
    // 示例多半以冒号结尾，等着贴链接：光标放到最后
    requestAnimationFrame(() => {
      const el = textareaRef.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(text.length, text.length);
    });
  };

  return (
    <div className="mx-auto w-full max-w-3xl px-5 py-8 sm:px-8 sm:py-12">
      <h1 className="text-2xl text-text-primary [font-family:var(--font-display)]">找哪个 Agent 帮忙？</h1>
      <p className="mt-1.5 text-sm text-text-muted">选一个 Agent，告诉它要做什么。它在服务器上干活，关掉页面也不会停。</p>

      <div className="mt-6 grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="选 Agent">
        {catalog.map(item => {
          const selected = item.name === agent.name;
          return (
            <button
              key={item.name || 'general'}
              type="button"
              role="radio"
              aria-checked={selected}
              disabled={!item.available || busy}
              onClick={() => pickAgent(item)}
              className={cn(
                'flex items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50',
                selected ? 'border-primary-400 bg-white shadow-sm ring-1 ring-primary-200' : 'border-border-subtle bg-white/60 hover:border-primary-200 hover:bg-white'
              )}
            >
              <AgentAvatar icon={item.icon} />
              <span className="min-w-0">
                <span className="block text-sm font-medium text-text-primary">{item.title}</span>
                <span className="mt-0.5 block text-xs leading-relaxed text-text-muted">
                  {item.available ? item.description : '服务器上还没装这个 Agent'}
                </span>
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-5 rounded-xl border border-border bg-white shadow-sm transition-colors focus-within:border-primary-300">
        <div className="flex items-center gap-2 px-4 pt-3 text-xs text-text-muted">
          <AgentAvatar icon={agent.icon} size="sm" className="h-5 w-5 rounded" />
          交给 <span className="font-medium text-text-secondary">{agent.title}</span>
        </div>
        <Textarea
          ref={textareaRef}
          rows={4}
          value={message}
          onChange={event => setMessage(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) void start();
          }}
          placeholder={agent.hint}
          aria-label="要做什么"
          className="min-h-[6.5rem] resize-none rounded-none border-0 bg-transparent focus:border-0 focus:bg-transparent focus:shadow-none"
        />
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 pb-3">
          <AttachmentPicker files={files} onChange={setFiles} disabled={busy} compact />
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 text-xs text-text-muted">
              模型
              <div className="inline-flex rounded-md bg-bg-tertiary p-0.5" role="radiogroup" aria-label="模型">
                {HARNESSES.map(item => (
                  <button
                    key={item.id}
                    type="button"
                    role="radio"
                    aria-checked={harness === item.id}
                    title={item.note}
                    disabled={busy}
                    onClick={() => pickHarness(item.id)}
                    className={cn(
                      'rounded px-2 py-0.5 transition-colors',
                      harness === item.id ? 'bg-white text-text-primary shadow-sm' : 'text-text-muted hover:text-text-primary'
                    )}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
            <Button size="sm" onClick={() => void start()} disabled={!canStart} title="Ctrl/⌘ + Enter">
              <ArrowUp /> {progress === null ? '开始' : progress < 100 ? `上传 ${progress}%` : '开始中…'}
            </Button>
          </div>
        </div>
      </div>
      {tooLarge && (
        <p className="mt-2 text-sm text-error">
          {tooLarge.name} 超过 {maxUploadMb} MB 上限，大文件请改用链接
        </p>
      )}
      <label className="mt-3 flex items-center gap-1.5 text-xs text-text-muted">
        <input
          type="checkbox"
          checked={autoReply}
          disabled={busy}
          onChange={event => setAutoReply(event.target.checked)}
          className="accent-[var(--color-primary-500)]"
        />
        需要你确认时（比如术语表），{AUTO_REPLY_MINUTES} 分钟没回就按它的建议继续
      </label>

      {agent.examples.length > 0 && (
        <div className="mt-6">
          <p className="text-xs text-text-muted">可以这样说：</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {agent.examples.map(example => (
              <button
                key={example}
                type="button"
                onClick={() => fillExample(example)}
                disabled={busy}
                className="max-w-full truncate rounded-full border border-border-subtle bg-white px-3 py-1 text-sm text-text-secondary transition-colors hover:border-primary-200 hover:text-text-primary"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
