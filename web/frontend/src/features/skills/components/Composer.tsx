import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';
import { Send, Square } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { sendMessage, skillsApi } from '../api';
import type { Agent, RunStatus } from '../types';
import { droppedFiles, isSendKey, pastedFiles, SEND_HINT } from '../input';
import { AttachmentPicker } from './AttachmentChips';

interface ComposerProps {
  runId: string;
  agent: Agent;
  status: RunStatus | null;
  hasPendingQuestion: boolean;
  /** 停住没发出去的挂起消息条数：这时发新消息会把它们放在前面一起发 */
  pausedHeld?: number;
  maxUploadMb: number;
  /** 输入框上方的一行提示（比如「在等你确认」），不另占一整条横幅 */
  notice?: ReactNode;
}

const MAX_HEIGHT = 200;

/**
 * 对话底部的输入框。agent 在干活时发的话先挂起，这一轮结束后自动发；
 * 挂起的消息在对话末尾可以改、删，要马上发就点它上面的「立即发送」。
 */
export function Composer({ runId, agent, status, hasPendingQuestion, pausedHeld = 0, maxUploadMb, notice }: ComposerProps) {
  const [message, setMessage] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [progress, setProgress] = useState<number | null>(null);
  const [stopping, setStopping] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const active = status === 'running' || status === 'waiting';
  const queued = status === 'queued';
  // 有提问挂着时输入的话是回答，直接发
  const holdable = (active || queued) && !hasPendingQuestion;
  const tooLarge = files.find(file => file.size > maxUploadMb * 1024 * 1024);
  const canSend = (message.trim() || files.length > 0) && !tooLarge && progress === null;

  // 输入框随内容长高，最多 MAX_HEIGHT，再多就滚动
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  }, [message]);

  const send = async (mode: 'queue' | 'now') => {
    if (!canSend) return;
    setProgress(files.length ? 0 : 100);
    try {
      await sendMessage(runId, { message, files, mode }, setProgress);
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
    : holdable
      ? `${agent.title}在干活，发的话等这一轮结束再发；输入 /status 看状态`
      : pausedHeld > 0
        ? `发新消息时，上面没发出去的 ${pausedHeld} 条会放在前面一起发`
        : status === 'error'
          ? '发一条消息（比如「继续」）从断点接着做'
          : `回复${agent.title}，或者交代下一步`;
  const sending = progress === null ? null : progress < 100 ? `上传 ${progress}%` : '发送中…';

  return (
    <div className="shrink-0 border-t border-border-subtle bg-white px-3 py-2 sm:px-4">
      <div
        className="mx-auto max-w-4xl"
        onDragOver={event => event.preventDefault()}
        onDrop={event => {
          const dropped = droppedFiles(event);
          if (dropped.length && progress === null) setFiles(current => [...current, ...dropped]);
        }}
      >
        {notice && <div className="mb-1.5 text-xs">{notice}</div>}
        <div className="rounded-xl border border-border bg-white transition-colors focus-within:border-primary-300">
          <textarea
            ref={textareaRef}
            rows={1}
            value={message}
            onChange={event => setMessage(event.target.value)}
            onKeyDown={event => {
              if (!isSendKey(event)) return;
              event.preventDefault();
              void send(holdable ? 'queue' : 'now');
            }}
            onPaste={event => {
              const pasted = pastedFiles(event);
              if (pasted.length && progress === null) setFiles(current => [...current, ...pasted]);
            }}
            placeholder={placeholder}
            aria-label="回复"
            className="block w-full resize-none bg-transparent px-3 pt-2.5 text-sm leading-relaxed text-text-primary outline-none placeholder:text-text-muted"
            style={{ maxHeight: MAX_HEIGHT }}
          />
          <div className="flex flex-wrap items-center justify-between gap-2 px-1.5 pb-1.5">
            <AttachmentPicker files={files} onChange={setFiles} disabled={progress !== null} compact />
            <div className="ml-auto flex items-center gap-1.5">
              {tooLarge && <span className="text-xs text-error">{tooLarge.name} 超过 {maxUploadMb} MB</span>}
              {SEND_HINT && !holdable && <span className="hidden text-xs text-text-muted md:inline">{SEND_HINT}</span>}
              {(active || queued) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={stop}
                  disabled={stopping}
                  title={queued ? '不排了，消息留在记录里' : '让它停下来，之后发消息可以接着做'}
                >
                  <Square /> {stopping ? '停止中…' : queued ? '取消排队' : '停止'}
                </Button>
              )}
              <Button
                size="sm"
                onClick={() => void send(holdable ? 'queue' : 'now')}
                disabled={!canSend}
                title={holdable ? '这一轮结束后自动发；要马上发，点待发消息上的「立即发送」' : SEND_HINT || '发送'}
              >
                <Send /> {sending ?? '发送'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
