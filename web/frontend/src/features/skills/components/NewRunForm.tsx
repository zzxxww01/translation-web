import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowUp, X } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';
import { AUTO_REPLY_MINUTES, startRun } from '../api';
import { skillKeys } from '../hooks';
import type { Agent, RunMeta } from '../types';
import { AgentIcon } from './AgentIcon';
import { AttachmentPicker } from './AttachmentChips';
import { HARNESSES, loadHarness, saveHarness, type Harness } from '../harness';

interface NewRunFormProps {
  /** 第一个是 Claude 聊天，其余是专职 agent（见 normalizeCatalog） */
  catalog: Agent[];
  maxUploadMb: number;
  onStarted: (run: RunMeta) => void;
}

/** 新任务：居中一个大输入框，下面一排 agent 按钮。不点按钮就是和 Claude 聊。 */
export function NewRunForm({ catalog, maxUploadMb, onStarted }: NewRunFormProps) {
  const queryClient = useQueryClient();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [skill, setSkill] = useState('');
  const [harness, setHarness] = useState<Harness>(loadHarness);
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [autoReply, setAutoReply] = useState(true);
  const [progress, setProgress] = useState<number | null>(null);

  const chat = catalog[0];
  const agent = catalog.find(item => item.name === skill) ?? chat;
  const specialists = catalog.filter(item => item.name);
  const busy = progress !== null;
  const tooLarge = files.find(file => file.size > maxUploadMb * 1024 * 1024);
  const canStart = Boolean(message.trim() || files.length > 0) && !tooLarge && !busy;

  const start = async () => {
    if (!canStart) return;
    setProgress(files.length ? 0 : 100);
    try {
      const run = await startRun({ skill, message, files, harness, autoReplyMinutes: autoReply ? AUTO_REPLY_MINUTES : 0 }, setProgress);
      await queryClient.invalidateQueries({ queryKey: skillKeys.runs });
      onStarted(run);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '启动失败');
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
    <div className="mx-auto flex min-h-full w-full max-w-2xl flex-col justify-center px-5 py-10 sm:px-8">
      <h1 className="mb-4 text-center text-2xl text-text-primary">今天要做什么？</h1>
      <div className="mb-4 flex justify-center">
        <div className="inline-flex rounded-lg bg-bg-tertiary p-0.5 text-sm" role="radiogroup" aria-label="用哪个 harness">
          {HARNESSES.map(item => (
            <button
              key={item.id}
              type="button"
              role="radio"
              aria-checked={harness === item.id}
              disabled={busy}
              onClick={() => {
                setHarness(item.id);
                saveHarness(item.id);
              }}
              className={cn(
                'rounded-md px-3 py-1 transition-colors',
                harness === item.id ? 'bg-white text-text-primary shadow-sm' : 'text-text-muted hover:text-text-primary'
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-border bg-white shadow-sm transition-colors focus-within:border-primary-300">
        {agent.name && (
          <div className="px-4 pt-3">
            <span className="inline-flex items-center gap-1.5 rounded-md bg-primary-50 py-1 pl-2 pr-1 text-xs font-medium text-primary-700">
              <AgentIcon icon={agent.icon} className="h-3.5 w-3.5" />
              {agent.title}
              <button
                type="button"
                onClick={() => setSkill('')}
                disabled={busy}
                aria-label={`不用${agent.title}，改为和 Claude 聊`}
                className="rounded p-0.5 hover:bg-primary-100"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          </div>
        )}
        <Textarea
          ref={textareaRef}
          rows={4}
          value={message}
          onChange={event => setMessage(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) start();
          }}
          placeholder={agent.hint || chat.hint}
          aria-label="要做什么"
          className="min-h-[6.5rem] resize-none rounded-none border-0 bg-transparent focus:border-0 focus:bg-transparent focus:shadow-none"
        />
        <div className="flex flex-wrap items-end justify-between gap-2 px-3 pb-3">
          <AttachmentPicker files={files} onChange={setFiles} disabled={busy} compact />
          <Button size="sm" onClick={start} disabled={!canStart} title="Ctrl/⌘ + Enter">
            <ArrowUp /> {progress === null ? '开始' : progress < 100 ? `上传 ${progress}%` : '启动中…'}
          </Button>
        </div>
      </div>
      <label className="mt-2 flex items-center justify-center gap-1.5 text-xs text-text-muted">
        <input
          type="checkbox"
          checked={autoReply}
          disabled={busy}
          onChange={event => setAutoReply(event.target.checked)}
          className="accent-[var(--color-primary-500)]"
        />
        需要你确认时（比如术语表），{AUTO_REPLY_MINUTES} 分钟没回复就按它的建议自动继续
      </label>
      {tooLarge && (
        <p className="mt-2 text-sm text-error">
          {tooLarge.name} 超过 {maxUploadMb} MB 上限，大文件请改用链接
        </p>
      )}

      {specialists.length > 0 && (
        <div className="mt-4 flex flex-wrap justify-center gap-2" role="group" aria-label="专职 agent">
          {specialists.map(item => {
            const selected = item.name === skill;
            return (
              <button
                key={item.name}
                type="button"
                aria-pressed={selected}
                disabled={!item.available || busy}
                title={item.available ? item.description : '服务器上没有安装这个 skill'}
                onClick={() => setSkill(selected ? '' : item.name)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-50',
                  selected
                    ? 'border-primary-400 bg-primary-50 text-primary-700'
                    : 'border-border-subtle bg-white text-text-secondary hover:border-primary-200 hover:text-text-primary'
                )}
              >
                <AgentIcon icon={item.icon} />
                {item.title}
              </button>
            );
          })}
        </div>
      )}

      <div className="mt-7 text-center">
        {agent.description && <p className="text-sm leading-relaxed text-text-muted">{agent.description}</p>}
        {agent.examples.length > 0 && (
          <div className="mt-3 flex flex-col items-center gap-2">
            {agent.examples.map(example => (
              <button
                key={example}
                type="button"
                onClick={() => fillExample(example)}
                disabled={busy}
                className="max-w-full truncate rounded-lg border border-border-subtle bg-white px-3 py-1.5 text-sm text-text-secondary transition-colors hover:border-primary-200 hover:text-text-primary"
              >
                {example}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
