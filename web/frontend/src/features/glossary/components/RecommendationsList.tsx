import { Badge } from '@/components/ui/badge';
import { ButtonExtended as Button } from '@/components/ui/button-extended';
import { Card, CardContent } from '@/components/ui/card';
import type { GlossaryRecommendation } from '@/features/confirmation/types';
import { strategyLabels } from '../types';

interface RecommendationsListProps {
  projectId: string | null | undefined;
  isLoading: boolean;
  filteredRecommendations: GlossaryRecommendation[];
  onPromote: (term: GlossaryRecommendation) => Promise<void>;
}

export function RecommendationsList({
  projectId,
  isLoading,
  filteredRecommendations,
  onPromote,
}: RecommendationsListProps) {
  if (!projectId) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-border bg-white p-10 text-center text-muted-foreground">
        正在加载推荐提升...
      </div>
    );
  }

  if (!filteredRecommendations.length) {
    return (
      <div className="rounded-2xl border border-dashed border-border p-10 text-center text-muted-foreground">
        当前没有可提升的项目术语推荐。
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {filteredRecommendations.map(term => (
        <Card key={term.original}>
          <CardContent className="p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div className="space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-lg font-semibold text-foreground">{term.original}</h3>
                  <Badge variant="outline">{strategyLabels[term.strategy]}</Badge>
                  <Badge variant="secondary">使用 {term.usage_count} 次</Badge>
                </div>
                <div className="text-muted-foreground">译法：{term.translation || '保留原文'}</div>
                {term.note ? (
                  <div className="text-sm text-muted-foreground">词义说明：{term.note}</div>
                ) : null}
                <p className="text-sm text-muted-foreground">{term.recommended_reason}</p>
                <div className="flex flex-wrap gap-2">
                  {(term.tags || []).map(tag => (
                    <Badge key={`${term.original}-${tag}`} variant="secondary">
                      {tag}
                    </Badge>
                  ))}
                </div>
                <div className="text-sm text-muted-foreground">
                  涉及章节：
                  {term.section_titles.length
                    ? term.section_titles.map(item => item.title).join(' / ')
                    : '未记录章节'}
                </div>
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={() => void onPromote(term)}>
                  提升到全局
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
