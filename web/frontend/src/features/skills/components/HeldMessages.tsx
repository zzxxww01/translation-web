import { useState } from 'react';
import { Clock, Paperclip, Pencil, Send, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { skillsApi } from '../api';
import type { HeldMessage } from '../types';

/** 对话末尾的待发消息：这一轮结束后按顺序自动发；之前可以改、删、立刻发 */
export function HeldMessages({ runId, items }: { runId: string; items: HeldMessage[] }) {
  if (!items.length) return null;
  return (
    <div className="space-y-2">
      {items.map((item, index) => (
        <HeldBubble key={item.id} runId={runId} item={item} first={index === 0} />
      ))}
    </div>
  );
}

function HeldBubble({ runId, item, first }: { runId: string; item: HeldMessage; first: boolean }) {
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

  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-xl rounded-tr-sm border border-dashed border-primary-200 bg-white px-3.5 py-2 text-sm text-text-primary">
        <div className="mb-1 flex items-center gap-1.5 text-xs text-text-muted">
          <Clock className="h-3 w-3" /> {first ? '这一轮结束后发' : '排在后面'}
        </div>
        {editing ? (
          <textarea
            value={draft}
            onChange={event => setDraft(event.target.value)}
            rows={Math.min(8, Math.max(2, draft.split('\n').length))}
            autoFocus
            className="w-full min-w-[16rem] resize-y rounded-md border border-border bg-white px-2 py-1.5 text-sm outline-none focus:border-primary-300"
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
        <div className="mt-1.5 flex justify-end gap-1">
          {editing ? (
            <>
              <Button variant="ghost" size="sm" disabled={busy} onClick={() => { setEditing(false); setDraft(item.text); }}>
                取消
              </Button>
              <Button size="sm" disabled={busy || (!draft.trim() && !item.files.length)} onClick={() => void save()}>
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
              <Button variant="outline" size="sm" disabled={busy} onClick={() => void act(() => skillsApi.sendHeld(runId, item.id), '没发出去')} title="不等了，马上发给它">
                <Send /> 立即发送
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
