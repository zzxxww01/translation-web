import { useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { glossaryApi } from '@/features/confirmation/api/glossaryApi';
import type { TermReviewDecision } from '@/features/confirmation/types';
import { TerminologyReviewPage } from '@/features/document/components/TerminologyReviewPage';
import { findAgent, normalizeCatalog } from '@/features/skills/agents';
import { LoginPanel } from '@/features/skills/components/LoginPanel';
import { RunPanel } from '@/features/skills/components/RunPanel';
import { isUnauthorized, useCatalog, useSkillsAuth } from '@/features/skills/hooks';
import type { RunMeta } from '@/features/skills/types';
import '@/features/skills/styles.css';
import { articleKeys } from '../hooks';
import { CLAUDE_SKILL } from '../lib/claude';

export type DrawerState =
  | { kind: 'terms'; projectId: string; jobId: string }
  | { kind: 'claude'; run: RunMeta }
  | null;

export function TrackDrawer({ state, mainId, onClose }: { state: DrawerState; mainId: string; onClose: () => void }) {
  return (
    <Sheet open={state !== null} onOpenChange={open => !open && onClose()}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-3xl">
        <SheetHeader className="border-b border-border-subtle px-5 py-3 text-left">
          <SheetTitle className="text-base">{state?.kind === 'terms' ? '网页版：确认术语' : 'Claude'}</SheetTitle>
          <SheetDescription className="text-xs">
            {state?.kind === 'terms' ? '确认后网页版接着翻；不确认的话到时间会自动采用建议。' : '和 Claude 页里是同一个任务。'}
          </SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-auto">
          {state?.kind === 'terms' && <TermsPanel projectId={state.projectId} jobId={state.jobId} mainId={mainId} onDone={onClose} />}
          {state?.kind === 'claude' && <ClaudePanel run={state.run} onDone={onClose} />}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function TermsPanel({ projectId, jobId, mainId, onDone }: { projectId: string; jobId: string; mainId: string; onDone: () => void }) {
  const queryClient = useQueryClient();
  const job = useQuery({
    queryKey: ['articles', 'term-job', projectId, jobId],
    // 剩余秒数按拿到数据的时刻算
    queryFn: async () => ({ job: await glossaryApi.getTermReviewJob(projectId, jobId), receivedAt: Date.now() }),
  });
  if (job.isPending) return <p className="p-6 text-sm text-text-muted">读取术语表…</p>;
  const data = job.data?.job;
  if (job.error || !data?.result) return <p className="p-6 text-sm text-text-muted">术语表读不到了，可能已经自动采用。</p>;
  if (data.confirmation_status && data.confirmation_status !== 'waiting') {
    return <p className="p-6 text-sm text-text-muted">术语已经确认过了，网页版在接着翻。</p>;
  }
  const review = data.result;
  const deadline = data.confirmation_deadline ? Date.parse(data.confirmation_deadline) : NaN;
  const remaining = Number.isFinite(deadline) ? Math.max(1, Math.round((deadline - job.data!.receivedAt) / 1000)) : 600;

  const submit = async (decisions: TermReviewDecision[]) => {
    try {
      await glossaryApi.submitTermReview(projectId, review.artifact_id, decisions);
      toast.success('术语已确认，网页版接着翻');
      await queryClient.invalidateQueries({ queryKey: articleKeys.workbench(mainId) });
      onDone();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '提交失败');
    }
  };

  return (
    <div className="p-4">
      <TerminologyReviewPage key={review.artifact_id} review={review} autoContinueSeconds={remaining} onSubmit={submit} onCancel={onDone} />
    </div>
  );
}

function ClaudePanel({ run, onDone }: { run: RunMeta; onDone: () => void }) {
  const auth = useSkillsAuth();
  const catalog = useCatalog(Boolean(auth.data));
  if (auth.isPending) return <p className="p-6 text-sm text-text-muted">连接 Claude…</p>;
  if (auth.error) {
    return isUnauthorized(auth.error) ? <LoginPanel /> : <p className="p-6 text-sm text-text-muted">Claude 服务连不上：{auth.error.message}</p>;
  }
  return (
    <div className="h-full">
      <RunPanel
        key={run.id}
        run={run}
        agent={findAgent(normalizeCatalog(catalog.data), run.skill || CLAUDE_SKILL)}
        maxUploadMb={auth.data.max_upload_mb}
        onDeleted={onDone}
      />
    </div>
  );
}
