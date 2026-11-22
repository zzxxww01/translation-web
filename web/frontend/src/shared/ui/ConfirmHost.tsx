import { useEffect } from 'react';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { buttonVariants } from '@/components/ui/button-variants';
import { useConfirmStore } from './confirm';

/** 挂在 App 根部一次；confirmAction() 打开的确认框都画在这里 */
export function ConfirmHost() {
  const request = useConfirmStore(state => state.request);
  useEffect(() => {
    useConfirmStore.setState({ hosted: true });
    return () => useConfirmStore.setState({ hosted: false });
  }, []);

  const answer = (ok: boolean) => {
    request?.resolve(ok);
    useConfirmStore.setState({ request: null });
  };

  return (
    <AlertDialog open={Boolean(request)} onOpenChange={open => { if (!open) answer(false); }}>
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <AlertDialogTitle className="text-base">{request?.title}</AlertDialogTitle>
          {request?.description && (
            <AlertDialogDescription className="whitespace-pre-line leading-relaxed text-text-secondary">
              {request.description}
            </AlertDialogDescription>
          )}
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={() => answer(false)}>{request?.cancelLabel ?? '取消'}</AlertDialogCancel>
          <AlertDialogAction
            className={request?.destructive ? buttonVariants({ variant: 'destructive' }) : undefined}
            onClick={() => answer(true)}
          >
            {request?.confirmLabel ?? '确定'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
