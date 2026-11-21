import { Check, CloudUpload, Loader2, X } from 'lucide-react';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { ACTION_LABELS, type PostWorkspace } from '../usePostWorkspace';

/** 进行中的请求：已用时 + 取消（各按钮自己的加载态给不了这两样） */
export function PendingChip({ ws }: { ws: PostWorkspace }) {
  if (!ws.pendingAction) return null;
  return (
    <span
      role="status"
      aria-live="polite"
      className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/60 py-0.5 pl-2.5 pr-1 text-xs text-muted-foreground"
    >
      <Loader2 className="h-3 w-3 shrink-0 animate-spin text-primary" />
      <span className="tabular-nums">{ACTION_LABELS[ws.pendingAction]} · {ws.elapsedSeconds}s</span>
      <button
        type="button"
        onClick={ws.cancelActiveAction}
        className="rounded-full p-0.5 text-muted-foreground transition-colors hover:bg-background hover:text-foreground"
        aria-label={`取消${ACTION_LABELS[ws.pendingAction]}`}
        title="取消"
      >
        <X className="h-3 w-3" />
      </button>
    </span>
  );
}

/** 翻译稿保存状态：存档中 / 已存档 */
export function SaveState({ saving, savedAt, hasDraft }: { saving: boolean; savedAt: number | null; hasDraft: boolean }) {
  if (!hasDraft && !saving) return null;
  return (
    <span className="inline-flex items-center gap-1 whitespace-nowrap text-xs text-text-muted" title="内容会自动存进「翻译记录」">
      {saving ? <CloudUpload className="h-3.5 w-3.5 animate-pulse" /> : <Check className="h-3.5 w-3.5 text-success" />}
      {saving ? '存档中' : savedAt ? '已存档' : '已存档'}
    </span>
  );
}

export function DiscardEditDialog({ ws }: { ws: PostWorkspace }) {
  return (
    <AlertDialog open={ws.pendingEditAction !== null} onOpenChange={open => { if (!open) ws.setPendingEditAction(null); }}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>放弃未保存的编辑</AlertDialogTitle>
          <AlertDialogDescription>当前译文有尚未保存的修改。继续后，这些修改将被放弃。</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>返回编辑</AlertDialogCancel>
          <AlertDialogAction onClick={ws.confirmPendingEditAction}>放弃修改</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
