/**
 * 章节质量卡片组件
 */

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import type { SectionQualityReport } from '../types';

interface SectionQualityCardProps {
  section: SectionQualityReport;
  onViewDetails?: () => void;
}

function getScoreColor(score: number): string {
  if (score >= 90) return 'text-green-700';
  if (score >= 70) return 'text-amber-700';
  if (score >= 50) return 'text-red-700';
  return 'text-gray-700';
}

export function SectionQualityCard({ section, onViewDetails }: SectionQualityCardProps) {
  const scoreColor = getScoreColor(section.overall_score);

  const issueCount = section.issue_count ?? section.issues.length;
  const pendingIssues = section.issues.filter(i => i.status === 'pending').length;
  const criticalIssues = section.issues.filter(i => i.severity === 'critical').length;

  return (
    <Card className="hover:shadow-md transition-all">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <CardTitle className="text-lg mb-2">{section.section_title}</CardTitle>
            <div className="flex flex-wrap gap-2">
              {section.is_excellent && (
                <Badge variant="success">优秀</Badge>
              )}
              {criticalIssues > 0 && (
                <Badge variant="error">{criticalIssues} 个严重问题</Badge>
              )}
              {pendingIssues > 0 && (
                <Badge variant="warning">{pendingIssues} 个待审核</Badge>
              )}
              <Badge variant="outline">修订 {section.revision_count} 次</Badge>
            </div>
          </div>
          <div className="text-right">
            <div className={cn('text-3xl font-bold', scoreColor)}>
              {section.overall_score}
            </div>
            <div className="text-xs text-gray-500">总体评分</div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 各维度评分 */}
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-xl font-semibold text-gray-700">
              {section.readability_score}
            </div>
            <div className="text-xs text-gray-500">可读性</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-xl font-semibold text-gray-700">
              {section.accuracy_score}
            </div>
            <div className="text-xs text-gray-500">准确性</div>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <div className="text-xl font-semibold text-gray-700">
              {section.conciseness_score}
            </div>
            <div className="text-xs text-gray-500">简洁性</div>
          </div>
        </div>

        {/* 问题统计 */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">
            共 {issueCount} 个问题
          </span>
          {section.final_assessment && (
            <Badge variant={section.final_assessment.passed ? 'success' : 'error'}>
              {section.final_assessment.passed ? '已通过' : '未通过'}
            </Badge>
          )}
        </div>

        {/* 未通过的评估标准 */}
        {section.final_assessment && !section.final_assessment.passed && section.final_assessment.failed_criteria.length > 0 && (
          <div className="text-sm">
            <p className="text-red-600 font-medium mb-1">未通过标准：</p>
            <ul className="list-disc list-inside text-red-600 space-y-1">
              {section.final_assessment.failed_criteria.map((criteria, idx) => (
                <li key={idx}>{criteria}</li>
              ))}
            </ul>
          </div>
        )}

        {/* 查看详情按钮 */}
        {onViewDetails && (
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={onViewDetails}
          >
            查看详情
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
