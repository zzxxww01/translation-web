/**
 * 质量报告页面
 */

import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, CheckCircle2, CircleAlert, CircleDashed } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/Button';
import { useProjectQualityReport } from './api';

function getQualityLevel(score: number) {
  if (score >= 90) {
    return {
      label: '整体质量优秀',
      description: '译文整体表现稳定，只需关注少量章节。',
      tone: 'text-emerald-700',
      bg: 'bg-emerald-50 border-emerald-200',
      icon: CheckCircle2,
    };
  }
  if (score >= 75) {
    return {
      label: '整体质量良好',
      description: '译文可以继续使用，建议优先复核问题较多的章节。',
      tone: 'text-amber-700',
      bg: 'bg-amber-50 border-amber-200',
      icon: CircleAlert,
    };
  }
  return {
    label: '需要重点复核',
    description: '译文仍有较多风险，建议先处理低分章节。',
    tone: 'text-rose-700',
    bg: 'bg-rose-50 border-rose-200',
    icon: CircleAlert,
  };
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

function getSectionStatus(score: number, issueCount: number) {
  if (score >= 90 && issueCount === 0) {
    return { label: '通过', variant: 'success' as const, icon: CheckCircle2 };
  }
  if (score >= 75) {
    return { label: '建议复核', variant: 'warning' as const, icon: CircleDashed };
  }
  return { label: '重点复核', variant: 'error' as const, icon: CircleAlert };
}

function issueTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    terminology: '术语',
    accuracy: '准确性',
    readability: '可读性',
    consistency: '一致性',
    style: '风格',
    tone: '语气',
    conciseness: '简洁性',
    structure: '结构',
  };
  return labels[type] || type;
}

function severityLabel(severity: string): string {
  const labels: Record<string, string> = {
    critical: '严重',
    major: '重要',
    minor: '轻微',
  };
  return labels[severity] || severity;
}

function severityVariant(severity: string) {
  if (severity === 'critical') return 'error' as const;
  if (severity === 'major') return 'warning' as const;
  return 'outline' as const;
}

const severityRank: Record<string, number> = {
  critical: 0,
  major: 1,
  minor: 2,
};

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
        <Card className="max-w-lg">
          <CardContent className="p-8 text-center">
            <CircleAlert className="mx-auto mb-4 h-10 w-10 text-amber-600" />
            <h2 className="mb-2 text-xl font-semibold text-gray-900">质量报告暂不可用</h2>
            <p className="mb-5 text-sm leading-6 text-gray-600">
              当前项目没有可读取的完整质量报告，或者报告服务暂时没有响应。已完成的报告会在这里显示为摘要，不需要进入其它页面。
            </p>
            <div className="flex justify-center gap-3">
              <Button variant="outline" onClick={() => navigate(`/document/${projectId}/confirmation`)}>
                返回文档
              </Button>
              <Button onClick={() => window.location.reload()}>重新加载</Button>
            </div>
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

  const level = getQualityLevel(report.overall_score);
  const LevelIcon = level.icon;
  const sortedSections = [...report.sections].sort((a, b) => {
    const issueDiff = (b.issue_count ?? b.issues.length) - (a.issue_count ?? a.issues.length);
    if (issueDiff !== 0) return issueDiff;
    return a.overall_score - b.overall_score;
  });
  const needsReviewCount = report.sections.filter(section => {
    const issueCount = section.issue_count ?? section.issues.length;
    return issueCount > 0 || section.overall_score < 90;
  }).length;
  const sortedIssues = [...report.issues].sort((a, b) => {
    const severityDiff = (severityRank[a.severity] ?? 9) - (severityRank[b.severity] ?? 9);
    if (severityDiff !== 0) return severityDiff;
    return a.paragraph_index - b.paragraph_index;
  });
  const priorityIssues = sortedIssues.filter(issue => issue.severity !== 'minor').slice(0, 20);
  const sectionIssueMap = sortedIssues.reduce<Record<string, typeof sortedIssues>>((acc, issue) => {
    const key = issue.section_id || 'unknown';
    acc[key] = acc[key] || [];
    acc[key].push(issue);
    return acc;
  }, {});
  const topIssueTypes = Object.entries(report.issue_type_counts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 4);

  return (
    <div className="mx-auto max-w-5xl px-4 py-8">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">质量报告</h1>
          <p className="mt-1 text-sm text-gray-600">{report.project_title}</p>
          <p className="mt-2 text-xs text-gray-500">生成时间：{formatDate(report.generated_at)}</p>
        </div>
        <Button
          variant="outline"
          onClick={() => navigate(`/document/${projectId}/confirmation`)}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          返回文档
        </Button>
      </header>

      <Card className={`mb-6 border ${level.bg}`}>
        <CardContent className="flex flex-col gap-4 p-6 md:flex-row md:items-center md:justify-between">
          <div className="flex items-start gap-3">
            <LevelIcon className={`mt-1 h-6 w-6 ${level.tone}`} />
            <div>
              <h2 className={`text-xl font-semibold ${level.tone}`}>{level.label}</h2>
              <p className="mt-1 text-sm text-gray-700">{level.description}</p>
            </div>
          </div>
          <div className={`text-5xl font-bold ${level.tone}`}>{report.overall_score}</div>
        </CardContent>
      </Card>

      <section className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-gray-500">问题总数</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">{report.total_issues}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-gray-500">建议复核章节</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">{needsReviewCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-sm text-gray-500">已自动修复</p>
            <p className="mt-2 text-3xl font-bold text-gray-900">
              {report.issues_by_status.auto_fixed || 0}
            </p>
          </CardContent>
        </Card>
      </section>

      {topIssueTypes.length > 0 && (
        <section className="mb-6">
          <Card>
            <CardContent className="p-5">
              <h2 className="mb-3 text-lg font-semibold text-gray-900">主要问题类型</h2>
              <div className="flex flex-wrap gap-2">
                {topIssueTypes.map(([type, count]) => (
                  <Badge key={type} variant="outline">
                    {issueTypeLabel(type)} {count}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </section>
      )}

      <section className="mb-6">
        <div className="mb-3 flex items-end justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">优先处理的问题</h2>
            <p className="mt-1 text-sm text-gray-500">先看严重和重要问题，每条都标出章节、段落和修改建议。</p>
          </div>
        </div>

        <Card>
          <CardContent className="divide-y divide-gray-100 p-0">
            {priorityIssues.length > 0 ? (
              priorityIssues.map((issue, index) => (
                <div key={`${issue.section_id}-${issue.paragraph_index}-${index}`} className="p-5">
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <Badge variant={severityVariant(issue.severity)}>{severityLabel(issue.severity)}</Badge>
                    <Badge variant="outline">{issueTypeLabel(issue.type)}</Badge>
                    <span className="text-xs text-gray-500">
                      {issue.section_title || issue.section_id} · 段落 {issue.paragraph_index + 1}
                    </span>
                  </div>
                  <p className="text-sm font-medium leading-6 text-gray-900">{issue.description}</p>
                  {issue.source_text && (
                    <p className="mt-2 text-xs leading-5 text-gray-500">涉及文本：{issue.source_text}</p>
                  )}
                  {issue.why_it_matters && (
                    <p className="mt-2 text-xs leading-5 text-gray-600">影响：{issue.why_it_matters}</p>
                  )}
                  {issue.suggestion && (
                    <p className="mt-2 rounded-md bg-amber-50 px-3 py-2 text-sm leading-6 text-amber-900">
                      建议：{issue.suggestion}
                    </p>
                  )}
                </div>
              ))
            ) : (
              <div className="p-5 text-sm text-gray-600">没有严重或重要问题。</div>
            )}
          </CardContent>
        </Card>
      </section>

      <section>
        <div className="mb-3">
          <h2 className="text-lg font-semibold text-gray-900">按章节查看全部问题</h2>
          <p className="mt-1 text-sm text-gray-500">展开章节后可以看到该章的具体问题和建议。</p>
        </div>

        <div className="space-y-3">
          {sortedSections.map(section => {
            const issueCount = section.issue_count ?? section.issues.length;
            const status = getSectionStatus(section.overall_score, issueCount);
            const StatusIcon = status.icon;
            const issues = sectionIssueMap[section.section_id] || [];

            return (
              <details key={section.section_id} className="rounded-lg border border-gray-200 bg-white">
                <summary className="flex cursor-pointer list-none items-center gap-4 px-5 py-4">
                  <StatusIcon className="h-5 w-5 shrink-0 text-gray-500" />
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm font-medium text-gray-900">
                      {section.section_title}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-gray-500">
                      <span>问题 {issueCount}</span>
                      <span>可读性 {section.readability_score}</span>
                      <span>准确性 {section.accuracy_score}</span>
                      <span>简洁性 {section.conciseness_score}</span>
                    </div>
                  </div>
                  <Badge variant={status.variant}>{status.label}</Badge>
                  <div className="w-14 text-right text-lg font-semibold text-gray-900">
                    {section.overall_score}
                  </div>
                </summary>
                <div className="border-t border-gray-100 px-5 py-4">
                  {issues.length > 0 ? (
                    <div className="space-y-4">
                      {issues.map((issue, index) => (
                        <div key={`${issue.paragraph_index}-${index}`} className="rounded-md bg-gray-50 p-4">
                          <div className="mb-2 flex flex-wrap items-center gap-2">
                            <Badge variant={severityVariant(issue.severity)}>{severityLabel(issue.severity)}</Badge>
                            <Badge variant="outline">{issueTypeLabel(issue.type)}</Badge>
                            <span className="text-xs text-gray-500">段落 {issue.paragraph_index + 1}</span>
                          </div>
                          <p className="text-sm font-medium leading-6 text-gray-900">{issue.description}</p>
                          {issue.suggestion && (
                            <p className="mt-2 text-sm leading-6 text-gray-700">建议：{issue.suggestion}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">这一章没有记录具体问题。</p>
                  )}
                </div>
              </details>
            );
          })}
        </div>
      </section>
    </div>
  );
}
