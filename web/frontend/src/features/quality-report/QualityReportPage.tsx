/**
 * 质量报告页面
 */

import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useProjectQualityReport } from './api';
import { QualityStatsCard } from './components/QualityStatsCard';
import { IssueList } from './components/IssueList';
import { SectionQualityCard } from './components/SectionQualityCard';

function getScoreVariant(score: number): 'success' | 'warning' | 'error' | 'default' {
  if (score >= 90) return 'success';
  if (score >= 70) return 'warning';
  if (score >= 50) return 'error';
  return 'default';
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function QualityReportPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { data: report, isLoading, error } = useProjectQualityReport(projectId!);

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-gray-600">加载质量报告中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="p-8 text-center">
            <p className="text-red-600 mb-4">加载质量报告失败</p>
            <p className="text-sm text-gray-600 mb-4">
              {error instanceof Error ? error.message : '未知错误'}
            </p>
            <Button onClick={() => window.location.reload()}>重试</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Card className="max-w-md">
          <CardContent className="p-8 text-center">
            <p className="text-gray-600 mb-4">未找到质量报告</p>
            <Button onClick={() => navigate('/document')}>返回文档列表</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const allIssues = report.sections.flatMap(s => s.issues);

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* 页面标题和元信息 */}
      <header className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">质量报告</h1>
            <p className="text-gray-600">项目：{report.project_title}</p>
            <p className="text-sm text-gray-500">生成时间：{formatDate(report.generated_at)}</p>
          </div>
          <Button
            variant="outline"
            onClick={() => navigate(`/document/${projectId}/confirmation`)}
          >
            返回文档
          </Button>
        </div>
      </header>

      {/* 全文统计概览 */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">统计概览</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <QualityStatsCard
            title="总体评分"
            value={report.overall_score}
            variant={getScoreVariant(report.overall_score)}
          />
          <QualityStatsCard
            title="问题总数"
            value={report.total_issues}
          />
          <QualityStatsCard
            title="待审核"
            value={report.issues_by_status.pending || 0}
            variant="warning"
          />
          <QualityStatsCard
            title="已修复"
            value={(report.issues_by_status.auto_fixed || 0) + (report.issues_by_status.manual_fixed || 0)}
            variant="success"
          />
        </div>
      </section>

      {/* 问题分布 */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">问题分布</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">按严重程度</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">严重</span>
                  <span className="text-lg font-semibold text-red-700">
                    {report.issues_by_severity.critical || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">重要</span>
                  <span className="text-lg font-semibold text-amber-700">
                    {report.issues_by_severity.major || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">轻微</span>
                  <span className="text-lg font-semibold text-gray-700">
                    {report.issues_by_severity.minor || 0}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">按状态</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">待审核</span>
                  <span className="text-lg font-semibold text-amber-700">
                    {report.issues_by_status.pending || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">已自动修复</span>
                  <span className="text-lg font-semibold text-green-700">
                    {report.issues_by_status.auto_fixed || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">已手动修复</span>
                  <span className="text-lg font-semibold text-green-700">
                    {report.issues_by_status.manual_fixed || 0}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">已忽略</span>
                  <span className="text-lg font-semibold text-gray-700">
                    {report.issues_by_status.dismissed || 0}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* 章节质量列表 */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">章节质量</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {report.sections.map(section => (
            <SectionQualityCard
              key={section.section_id}
              section={section}
              onViewDetails={() => {
                navigate(`/document/${projectId}/confirmation#${section.section_id}`);
              }}
            />
          ))}
        </div>
      </section>

      {/* 全部问题列表 */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">所有问题</h2>
        <IssueList
          issues={allIssues}
          onIssueClick={(issue) => {
            const section = report.sections.find(s =>
              s.issues.some(i => i.id === issue.id)
            );
            if (section) {
              navigate(
                `/document/${projectId}/confirmation#${section.section_id}-p${issue.paragraph_index}`
              );
            }
          }}
        />
      </section>
    </div>
  );
}
