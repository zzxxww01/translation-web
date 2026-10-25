import { useState } from 'react';
import { Send, Square } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { Textarea } from '@/components/ui/textarea';
import { sendMessage, skillsApi } from '../api';
import type { Agent, RunStatus } from '../types';
import { AttachmentPicker } from './AttachmentChips';

interface ComposerProps {
  runId: string;
  agent: Agent;
  status: RunStatus | null;
  hasPendingQuestion: boolean;
  maxUploadMb: number;
}

export function Composer({ runId, agent, status, hasPendingQuestion, maxUploadMb }: ComposerProps) {
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [stopping, setStopping] = useState(false);
  const active = status === 'running' || status === 'waiting';
  const tooLarge = files.find(file => file.size > maxUploadMb * 1024 * 1024);
  const canSend = (message.trim() || files.length > 0) && !tooLarge && progress === null;

  const send = async () => {
    if (!canSend) return;
    setProgress(files.length ? 0 : 100);
    try {
      await sendMessage(runId, { message, files }, setProgress);
      setMessage('');
      setFiles([]);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '发送失败');
    } finally {
      setProgress(null);
    }
  };

  const stop = async () => {
    setStopping(true);
    try {
      await skillsApi.interrupt(runId);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '停止失败');
    } finally {
      setStopping(false);
    }
  };

  const placeholder = hasPendingQuestion
    ? '也可以直接在这里写字回答上面的问题'
    : active
      ? `${agent.title}在干活，也可以随时补充说明`
      : status === 'error'
        ? '发一条消息（比如「继续」）从断点接着做'
        : `回复${agent.title}，或者交代下一步`;

  return (
    <div className="border-t border-border-subtle bg-white px-4 py-3">
      <div className="mx-auto max-w-3xl">
        <Textarea
          rows={2}
          value={message}
          onChange={event => setMessage(event.target.value)}
          onKeyDown={event => {
            if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) void send();
          }}
          placeholder={placeholder}
          aria-label="回复"
          className="min-h-[3.5rem] resize-y"
        />
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
          <AttachmentPicker files={files} onChange={setFiles} disabled={progress !== null} compact />
          <div className="flex items-center gap-2">
            {tooLarge && <span className="text-xs text-error">{tooLarge.name} 超过 {maxUploadMb} MB</span>}
            {active && (
              <Button variant="outline" size="sm" onClick={stop} disabled={stopping} title="让它停下来，之后发消息可以接着做">
                <Square /> {stopping ? '停止中…' : '停止'}
              </Button>
            )}
            <Button size="sm" onClick={() => void send()} disabled={!canSend} title="Ctrl/⌘ + Enter">
              <Send /> {progress === null ? '发送' : progress < 100 ? `上传 ${progress}%` : '发送中…'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
