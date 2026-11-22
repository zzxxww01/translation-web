import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowUp, ChevronDown, LayoutList } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { AUTO_REPLY_MINUTES, startRun } from '../api';
import { skillKeys } from '../hooks';
import { HARNESSES, loadHarness, saveHarness, type Harness } from '../harness';
import { loadModel, saveModel } from '../models';
import type { Agent, RunMeta } from '../types';
import { AgentAvatar } from './AgentIcon';
import { droppedFiles, isSendKey, pastedFiles, SEND_HINT } from '../input';
import { AttachmentPicker } from './AttachmentChips';
import { ModelPicker } from './ModelPicker';

interface NewRunFormProps {
  /** 第一个是通用 Agent，其余是专职 Agent（见 normalizeCatalog） */
  catalog: Agent[];
  maxUploadMb: number;
  /** 从 Agent 详情页点「和它对话」进来时预选的 Agent */
  initialAgent?: string;
  onStarted: (run: RunMeta) => void;
  /** 打开 Agent 列表 */
  onBrowse: () => void;
}

/** 新对话：输入框上方下拉选 Agent（默认通用），交代要做什么。模型和自动继续是次要选项，放在输入框下面。 */
export function NewRunForm({ catalog, maxUploadMb, initialAgent = '', onStarted, onBrowse }: NewRunFormProps) {
  const queryClient = useQueryClient();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [agentName, setAgentName] = useState(initialAgent);
  const [pickerOpen, setPickerOpen] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);
  // 点别处收起 Agent 列表
  useEffect(() => {
    if (!pickerOpen) return;
    const close = (event: MouseEvent) => {
      if (!pickerRef.current?.contains(event.target as Node)) setPickerOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [pickerOpen]);
  const agent = catalog.find(item => item.name === agentName) ?? catalog[0];
  const [harness, setHarness] = useState<Harness>(() => loadHarness(agent.name, agent.harness));
  const [model, setModel] = useState(() => loadModel(agent.name, harness));
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [autoReply, setAutoReply] = useState(true);
  const [progress, setProgress] = useState<number | null>(null);

  const busy = progress !== null;
  const tooLarge = files.find(file => file.size > maxUploadMb * 1024 * 1024);
  const canStart = Boolean(message.trim() || files.length > 0) && !tooLarge && !busy;

  const pickAgent = (next: Agent) => {
    setAgentName(next.name);
    setPickerOpen(false);
    const nextHarness = loadHarness(next.name, next.harness);
    setHarness(nextHarness);
    setModel(loadModel(next.name, nextHarness));
    textareaRef.current?.focus();
  };

  const pickHarness = (next: Harness) => {
    setHarness(next);
    saveHarness(agent.name, next);
    setModel(loadModel(agent.name, next));
  };

  const pickModel = (next: string) => {
    setModel(next);
    saveModel(agent.name, harness, next);
  };

  const start = async () => {
    if (!canStart) return;
    setProgress(files.length ? 0 : 100);
    try {
      const run = await startRun(
        { skill: agent.name, message, files, harness, ...(model.trim() ? { model: model.trim() } : {}), autoReplyMinutes: autoReply ? AUTO_REPLY_MINUTES : 0 },
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
      <h1 className="text-2xl text-text-primary [font-family:var(--font-display)]">要做什么？</h1>
      <p className="mt-1.5 text-sm text-text-muted">交代给 Agent，它在服务器上干活，关掉页面也不会停。</p>

      <div
        className="mt-6 rounded-xl border border-border bg-white shadow-sm transition-colors focus-within:border-primary-300"
        onDragOver={event => event.preventDefault()}
        onDrop={event => {
          const dropped = droppedFiles(event);
          if (dropped.length && !busy) setFiles(current => [...current, ...dropped]);
        }}
      >
        <div className="flex items-center gap-2 px-3 pt-3 text-xs text-text-muted">
          <span className="pl-1">交给 </span>
          <div ref={pickerRef} className="relative">
            <button
              type="button"
              aria-label="选 Agent"
              aria-expanded={pickerOpen}
              disabled={busy}
              onClick={() => setPickerOpen(open => !open)}
              className="inline-flex items-center gap-1.5 rounded-md border border-border-subtle bg-bg-secondary px-2 py-1 text-text-secondary transition-colors hover:border-primary-200 hover:text-text-primary"
            >
              <AgentAvatar icon={agent.icon} size="sm" className="h-5 w-5 rounded" />
              <span className="font-medium">{agent.title}</span>
              <ChevronDown className="h-3.5 w-3.5" />
            </button>
            {/* 列表一直在 DOM 里，收起时隐藏：键盘和读屏都能找到 */}
            <div
              hidden={!pickerOpen}
              className="absolute left-0 top-full z-20 mt-1 w-80 max-w-[85vw] rounded-lg border border-border-subtle bg-white p-1 shadow-lg"
            >
              <div role="radiogroup" aria-label="选 Agent" className="max-h-80 overflow-y-auto">
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
                        'flex w-full items-start gap-2.5 rounded-md px-2 py-2 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-50',
                        selected ? 'bg-primary-50' : 'enabled:hover:bg-bg-hover'
                      )}
                    >
                      <span className="sr-only">{item.title}</span>
                      <AgentAvatar icon={item.icon} size="sm" />
                      <span className="min-w-0" aria-hidden>
                        <span className="block text-sm text-text-primary">{item.title}</span>
                        <span className="line-clamp-1 block text-xs text-text-muted">
                          {item.available ? item.description : '服务器上还没装这个 Agent'}
                        </span>
                      </span>
                    </button>
                  );
                })}
              </div>
              <button
                type="button"
                onClick={onBrowse}
                className="mt-1 flex w-full items-center gap-2 border-t border-border-subtle px-2 pb-1 pt-2 text-left text-xs text-text-secondary hover:text-text-primary"
              >
                <LayoutList className="h-3.5 w-3.5" /> 查看全部 Agent 和它们的 skill
              </button>
            </div>
          </div>
          <span className="hidden min-w-0 truncate sm:inline">{agent.description}</span>
        </div>
        <Textarea
          ref={textareaRef}
          rows={4}
          value={message}
          onChange={event => setMessage(event.target.value)}
          onKeyDown={event => {
            if (!isSendKey(event)) return;
            event.preventDefault();
            void start();
          }}
          onPaste={event => {
            const pasted = pastedFiles(event);
            if (pasted.length && !busy) setFiles(current => [...current, ...pasted]);
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
            <Button size="sm" onClick={() => void start()} disabled={!canStart} title={SEND_HINT || '开始'}>
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
      <div className="mt-3">
        <ModelPicker key={`${agent.name}:${harness}`} harness={harness} value={model} onChange={pickModel} disabled={busy} />
      </div>
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
