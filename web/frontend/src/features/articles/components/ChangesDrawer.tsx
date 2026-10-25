import { useQuery } from '@tanstack/react-query';
import { Download } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { articlesApi, downloadText, HUMAN_EDITS_URL } from '../api';
import { articleKeys } from '../hooks';
import { changesMarkdown, savedAtText } from '../lib/changes';
import type { DiffSegment } from '../types';

export interface ChangesTarget {
  projectId: string;
  target: string;
  /** 「译本 1 · 网页版」这类栏名 */
  label: string;
  title: string;
}

/** 这一版里人工改了什么：每段机翻初稿 → 现在，逐字标出删改。 */
export function ChangesDrawer({ state, onClose }: { state: ChangesTarget | null; onClose: () => void }) {
  return (
    <Sheet open={state !== null} onOpenChange={open => !open && onClose()}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 p-0 sm:max-w-2xl">
        <SheetHeader className="border-b border-border-subtle px-5 py-3 text-left">
          <SheetTitle className="text-base">人工改动 · {state?.label}</SheetTitle>
          <SheetDescription className="text-xs">和机翻初稿比，你改了哪些段落。点「保存全文」时会连同定稿一起存到服务器。</SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 overflow-auto">{state && <ChangesList state={state} />}</div>
      </SheetContent>
    </Sheet>
  );
}

function ChangesList({ state }: { state: ChangesTarget }) {
  const query = useQuery({
    queryKey: articleKeys.changes(state.target),
    queryFn: () => articlesApi.changes(state.projectId, state.target),
  });
  if (query.isPending) return <p className="p-6 text-sm text-text-muted">读取改动…</p>;
  if (query.error || !query.data) return <p className="p-6 text-sm text-error">读不到改动：{query.error?.message}</p>;
  const report = query.data;

  return (
    <div className="px-5 py-4">
      <div className="flex flex-wrap items-center gap-2 text-sm text-text-secondary">
        <span>共 {report.total} 段，改了 <b className="text-text-primary">{report.changed}</b> 段</span>
        <span className="text-xs text-text-muted">
          {report.finalized ? `上次保存全文：${savedAtText(report.finalized.saved_at)}` : '还没保存过全文'}
        </span>
        <span className="flex-1" />
        <Button
          size="sm"
          variant="outline"
          disabled={!report.changed}
          onClick={() => downloadText(`${state.target}-人工改动.md`, changesMarkdown(`${state.title}（${state.label}）`, report))}
        >
          <Download /> 下载这篇
        </Button>
        <a href={HUMAN_EDITS_URL} className="text-xs text-primary-700 hover:underline" title="所有保存过全文的文章，一行一段（JSONL）">
          全部文章的改动
        </a>
      </div>

      {!report.changed && <p className="py-10 text-center text-sm text-text-muted">还没有改过。</p>}
      <ol className="mt-4 space-y-5">
        {report.changes.map(change => (
          <li key={change.key} className="border-b border-border-subtle pb-4 last:border-0">
            <p className="text-[11px] text-text-muted">{change.section_title || change.section_id} · {change.paragraph_id}</p>
            <p className="mt-1 text-[13px] leading-relaxed text-text-muted">{change.source}</p>
            {change.before === null && <p className="mt-2 text-xs text-text-muted">原来没有译文，是你写的：</p>}
            <p className="mt-2 text-[15px] leading-[1.8] text-text-primary">
              <Segments segments={change.segments} />
            </p>
          </li>
        ))}
      </ol>
    </div>
  );
}

function Segments({ segments }: { segments: DiffSegment[] }) {
  return (
    <>
      {segments.map((segment, index) => {
        if (segment.op === 'delete') return <del key={index} className="bg-error-light text-error decoration-error/60">{segment.text}</del>;
        if (segment.op === 'insert') return <ins key={index} className="bg-success-light text-success no-underline">{segment.text}</ins>;
        return <span key={index}>{segment.text}</span>;
      })}
    </>
  );
}
