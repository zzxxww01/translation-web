import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/Button';
import { translationRuleCandidatesApi } from '../api';

export function TranslationRuleCandidates({ onApproved }: { onApproved: () => void }) {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ['translation-rule-candidates'], queryFn: translationRuleCandidatesApi.list });
  const decision = useMutation({
    mutationFn: ({ id, action }: { id: string; action: 'approve' | 'reject' }) =>
      translationRuleCandidatesApi.decide(id, action),
    onSuccess: async (row) => {
      await client.invalidateQueries({ queryKey: ['translation-rule-candidates'] });
      if (row.status === 'approved') onApproved();
    },
    onError: () => { toast.error('规则确认失败，请重试'); },
  });
  const pending = query.data?.candidates.filter(row => row.status === 'pending') ?? [];
  return (
    <section className="space-y-3 rounded-md border p-4" aria-label="待确认的翻译建议">
      <h2 className="font-semibold">待确认的翻译建议</h2>
      <p className="text-sm text-muted-foreground">模型建议不会自动影响其他文章。确认适用于所有项目后，再加入全局规则。</p>
      {query.isPending && <p className="text-sm">正在加载建议…</p>}
      {query.isError && <Button variant="outline" onClick={() => void query.refetch()}>加载失败，重试</Button>}
      {!query.isPending && !query.isError && pending.length === 0 && <p className="text-sm text-muted-foreground">暂无待确认建议</p>}
      {pending.map(row => (
        <div key={row.id} className="space-y-2 border-t pt-3">
          <p className="text-sm leading-6">{row.rule}</p>
          <details className="text-xs text-muted-foreground">
            <summary>查看来源与修改依据（{row.source_kind}）</summary>
            <pre className="mt-2 whitespace-pre-wrap break-words">{JSON.stringify(row.evidence, null, 2)}</pre>
          </details>
          <div className="flex gap-2">
            <Button size="sm" disabled={decision.isPending} onClick={() => decision.mutate({ id: row.id, action: 'approve' })}>确认并加入全局规则</Button>
            <Button size="sm" variant="outline" disabled={decision.isPending} onClick={() => decision.mutate({ id: row.id, action: 'reject' })}>不采纳</Button>
          </div>
        </div>
      ))}
    </section>
  );
}
