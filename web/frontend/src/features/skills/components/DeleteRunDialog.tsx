import { useState, type MouseEvent, type ReactNode } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';

/** 删除对话的确认框。服务器上是假删除（目录挪进存档），所以文案不说「无法恢复」。 */
export function DeleteRunDialog({ onConfirm, children }: {
  onConfirm: () => Promise<void>;
  /** 触发按钮，会被包进 AlertDialogTrigger asChild */
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const confirm = async (event: MouseEvent) => {
    // 成功才关；失败留着框并提示
    event.preventDefault();
    setBusy(true);
    try {
      await onConfirm();
      setOpen(false);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '删除失败');
    } finally {
      setBusy(false);
    }
  };
  return (
    <AlertDialog open={open} onOpenChange={next => { if (!busy) setOpen(next); }}>
      <AlertDialogTrigger asChild>{children}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>删除这个对话？</AlertDialogTitle>
          <AlertDialogDescription>从列表里删掉。服务器上会保留存档，需要时可以找回。</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={busy}>取消</AlertDialogCancel>
          <AlertDialogAction disabled={busy} onClick={event => void confirm(event)}>{busy ? '删除中…' : '删除'}</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
