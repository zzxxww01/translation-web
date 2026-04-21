/**
 * 文档页面内的质量面板组件
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { useProjectQualityReport, useSectionQualityReport } from '../api';
import { QualityStatsCard } from './QualityStatsCard';
import { IssueList } from './IssueList';

interface DocumentQualityPanelProps {
  projectId: string;
  currentSectionId?: string;
}

function getScoreVariant(score: number): 'success' | 'warning' | 'error' | 'default' {
  if (score >= 90) return 'success';
  if (score >= 70) return 'warning';
  if (score >= 50) return 'error';
  return 'default';
}

export function DocumentQualityPanel({ projectId, currentSectionId }: DocumentQualityPanelProps) {
  const { data: report, isLoading: reportLoading, error: reportError } = useProjectQualityReport(projectId);
  const { data: sectionReport, isLoading: sectionLoading, error: sectionError } = useSectionQualityReport(
    projectId,
    currentSectionId || ''
  );

  const [view, setView] = useState<'current' | 'all'>('current');

  if (reportLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (reportError) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center">
            <p className="text-red-600 mb-2">加载失败</p>
            <p className="text-sm text-gray-600">{reportError instanceof Error ? reportError.message : '未知错误'}</p>
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => window.location.reload()}
            >
              重试
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!report) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-gray-500">
          暂无质量报告数据
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* 视图切换 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">质量报告</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Button
              variant={view === 'current' ? 'default' : 'outline'}
              size="sm"
              className="flex-1"
              onClick={() => setView('current')}
              disabled={!currentSectionId}
            >
              当前章节
            </Button>
            <Button
              variant={view === 'all' ? 'default' : 'outline'}
              size="sm"
              className="flex-1"
              onClick={() => setView('all')}
            >
              全文
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 当前章节视图 */}
      {view === 'current' && currentSectionId && (
        <div className="space-y-4">
          {sectionLoading ? (
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-center">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
                </div>
              </CardContent>
            </Card>
          ) : sectionError ? (
            <Card>
              <CardContent className="p-6">
                <div className="text-center">
                  <p className="text-red-600 mb-2">加载章节数据失败</p>
                  <p className="text-sm text-gray-600">{sectionError instanceof Error ? sectionError.message : '未知错误'}</p>
                </div>
              </CardContent>
            </Card>
          ) : sectionReport ? (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="text-sm">{sectionReport.section_title}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 gap-2">
                    <QualityStatsCard
                      title="总体评分"
                      value={sectionReport.overall_score}
                      variant={getScoreVariant(sectionReport.overall_score)}
                    />
                    <QualityStatsCard
                      title="问题数"
                      value={sectionReport.issues.length}
                    />
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="text-center p-2 bg-gray-50 rounded">
                      <div className="text-lg font-semibold">{sectionReport.readability_score}</div>
                      <div className="text-xs text-gray-500">可读性</div>
                    </div>
                    <div className="text-center p-2 bg-gray-50 rounded">
                      <div className="text-lg font-semibold">{sectionReport.accuracy_score}</div>
                      <div className="text-xs text-gray-500">准确性</div>
                    </div>
                    <div className="text-center p-2 bg-gray-50 rounded">
                      <div className="text-lg font-semibold">{sectionReport.conciseness_score}</div>
                      <div className="text-xs text-gray-500">简洁性</div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {sectionReport.issues.length > 0 && (
                <IssueList
                  issues={sectionReport.issues}
                  onIssueClick={(issue) => {
                    const element = document.getElementById(
                      `${currentSectionId}-p${issue.paragraph_index}`
                    );
                    element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  }}
                />
              )}
            </>
          ) : (
            <Card>
              <CardContent className="p-6 text-center text-gray-500">
                暂无章节质量数据
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* 全文视图 */}
      {view === 'all' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <QualityStatsCard
              title="总体评分"
              value={report.overall_score}
              variant={getScoreVariant(report.overall_score)}
            />
            <QualityStatsCard
              title="问题总数"
              value={report.total_issues}
            />
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm">章节列表</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {report.sections.map(section => (
                <div
                  key={section.section_id}
                  className="p-3 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => {
                    const element = document.getElementById(section.section_id);
                    element?.scrollIntoView({ behavior: 'smooth' });
                    setView('current');
                  }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-medium text-sm">{section.section_title}</span>
                    <span className={cn(
                      'text-lg font-bold',
                      section.overall_score >= 90 ? 'text-green-700' :
                      section.overall_score >= 70 ? 'text-amber-700' :
                      'text-red-700'
                    )}>
                      {section.overall_score}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500">
                    {section.issues.length} 个问题
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}

      {/* 查看完整报告链接 */}
      <Card>
        <CardContent className="p-4">
          <a
            href={`/document/${projectId}/quality-report`}
            className="text-sm text-primary hover:underline flex items-center justify-center gap-1"
          >
            查看完整质量报告 →
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
