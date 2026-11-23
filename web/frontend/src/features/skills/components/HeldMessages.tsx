import { useState } from 'react';
import { Clock, Paperclip, Pencil, Send, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { skillsApi } from '../api';
import type { HeldMessage } from '../types';

/**
 * 对话末尾的待发消息：这一轮正常结束后合成一条一起发；之前可以改、删、立刻发。
 * paused：上一轮没正常结束（停止、出错、服务重启），不会自动发，等你点发送或发新消息时一起带上。
 */
export function HeldMessages({ runId, items, paused }: { runId: string; items: HeldMessage[]; paused: boolean }) {
  if (!items.length) return null;
  const label = paused
    ? '没发出去（上一轮没正常结束）'
    : items.length > 1
      ? '这一轮结束后一起发'
      : '这一轮结束后发';
  return (
    <div className="space-y-2">
      {items.map(item => (
        <HeldBubble key={item.id} runId={runId} item={item} label={label} paused={paused} />
      ))}
    </div>
  );
}

function HeldBubble({ runId, item, label, paused }: { runId: string; item: HeldMessage; label: string; paused: boolean }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.text);
  const [busy, setBusy] = useState(false);

  const act = async (action: () => Promise<unknown>, failText: string) => {
    setBusy(true);
    try {
      await action();
      return true;
    } catch (error) {
      toast.error(error instanceof Error ? error.message : failText);
      return false;
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (await act(() => skillsApi.editHeld(runId, item.id, draft), '没改成')) setEditing(false);
  };
  const cancel = () => {
    setEditing(false);
    setDraft(item.text);
  };
  const canSave = !busy && Boolean(draft.trim() || item.files.length);

  return (
    <div className="flex justify-end">
      {/* 编辑时撑满到和对话气泡一样宽，输入框是一整条，不跟着字数缩成小方块 */}
      <div className={cn(
        'max-w-[85%] rounded-xl rounded-tr-sm border border-dashed bg-white px-3.5 py-2 text-sm text-text-primary',
        paused ? 'border-warning/60' : 'border-primary-200',
        editing && 'w-full'
      )}>
        <div className="mb-1 flex items-center gap-1.5 text-xs text-text-muted">
          <Clock className="h-3 w-3" /> {label}
        </div>
        {editing ? (
          <textarea
            value={draft}
            onChange={event => setDraft(event.target.value)}
            onKeyDown={event => {
              if (event.key === 'Enter' && (event.metaKey || event.ctrlKey) && canSave) {
                event.preventDefault();
                void save();
              } else if (event.key === 'Escape') {
                event.preventDefault();
                cancel();
              }
            }}
            rows={Math.min(10, Math.max(3, draft.split('\n').length + 1))}
            autoFocus
            onFocus={event => event.currentTarget.setSelectionRange(draft.length, draft.length)}
            className="block w-full resize-y rounded-md border border-border bg-white px-3 py-2 text-sm leading-relaxed outline-none focus:border-primary-300 focus:ring-2 focus:ring-primary-100"
          />
        ) : (
          item.text && <p className="whitespace-pre-wrap break-words">{item.text}</p>
        )}
        {item.files.length > 0 && (
          <ul className="mt-1 space-y-0.5 text-xs text-text-secondary">
            {item.files.map(file => (
              <li key={file} className="flex items-center gap-1.5">
                <Paperclip className="h-3 w-3" /> {file}
              </li>
            ))}
          </ul>
        )}
        <div className="mt-1.5 flex items-center justify-end gap-1">
          {editing ? (
            <>
              <span className="mr-auto hidden text-xs text-text-muted sm:inline">Ctrl/⌘ + Enter 保存，Esc 取消</span>
              <Button variant="ghost" size="sm" disabled={busy} onClick={cancel}>
                取消
              </Button>
              <Button size="sm" disabled={!canSave} onClick={() => void save()}>
                保存
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm" disabled={busy} onClick={() => setEditing(true)} title="编辑">
                <Pencil /> 编辑
              </Button>
              <Button variant="ghost" size="sm" disabled={busy} onClick={() => void act(() => skillsApi.deleteHeld(runId, item.id), '没删掉')} title="删除">
                <Trash2 /> 删除
              </Button>
              <Button variant="outline" size="sm" disabled={busy} onClick={() => void act(() => skillsApi.sendHeld(runId, item.id), '没发出去')} title={paused ? '发出去' : '不等了，马上发给它'}>
                <Send /> {paused ? '发送' : '立即发送'}
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
