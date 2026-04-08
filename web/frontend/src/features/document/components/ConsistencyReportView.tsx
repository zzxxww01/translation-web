import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, RefreshCw, ScanSearch } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button-extended';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  documentApi,
  type ConsistencyIssue,
  type LatestConsistencyReportResponse,
} from '../api';

interface ConsistencyReportViewProps {
  projectId: string;
  projectTitle: string;
  onLocateIssue: (issue: ConsistencyIssue) => void;
}

function formatTimestamp(value?: string) {
  if (!value) return '未知';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function issueTone(issueType: string) {
  switch (issueType) {
    case 'data':
      return 'bg-rose-50 border-rose-200 text-rose-700';
    case 'proper_noun':
      return 'bg-amber-50 border-amber-200 text-amber-700';
    case 'style':
      return 'bg-sky-50 border-sky-200 text-sky-700';
    default:
      return 'bg-slate-50 border-slate-200 text-slate-700';
  }
}

export function ConsistencyReportView({
  projectId,
  projectTitle,
  onLocateIssue,
}: ConsistencyReportViewProps) {
  const [loading, setLoading] = useState(true);
  const [rerunning, setRerunning] = useState(false);
  const [payload, setPayload] = useState<LatestConsistencyReportResponse | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    try {
      const result = await documentApi.getLatestConsistencyReport(projectId);
      setPayload(result);
    } catch (error) {
      console.error('Failed to load consistency report:', error);
      toast.error('加载一致性报告失败');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const handleRerun = useCallback(async () => {
    setRerunning(true);
    try {
      const report = await documentApi.runConsistencyReview(projectId);
      setPayload(prev => ({
        project_id: projectId,
        report: {
          is_consistent: report.is_consistent,
          issue_count: report.issue_count,
          total_issues: report.issue_count,
          auto_fixable_count: report.auto_fixable_count,
          manual_review_count: report.manual_review_count,
          issues: report.issues,
        },
        run_id: prev?.run_id,
        status: 'manual_review',
        started_at: prev?.started_at,
        finished_at: new Date().toISOString(),
        artifacts_path: prev?.artifacts_path,
        source: 'manual_review',
      }));
      toast.success('一致性审查已更新');
    } catch (error) {
      console.error('Failed to rerun consistency review:', error);
      toast.error('重新审查失败');
    } finally {
      setRerunning(false);
    }
  }, [projectId]);

  if (loading) {
    return (
      <div className="flex min-h-[280px] items-center justify-center">
        <RefreshCw className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  const report = payload?.report;
  if (!report) {
    return (
      <div className="mx-auto max-w-4xl py-8">
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <ScanSearch className="h-12 w-12 text-text-muted" />
            <div>
              <h2 className="text-xl font-semibold">暂无一致性报告</h2>
              <p className="mt-2 text-sm text-text-muted">
                当前项目还没有可展示的一致性审查结果。
              </p>
            </div>
            <Button onClick={handleRerun} disabled={rerunning}>
              {rerunning ? '审查中...' : '立即生成报告'}
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl py-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">一致性报告</h2>
          <p className="mt-1 text-sm text-text-muted">{projectTitle}</p>
          <p className="mt-2 text-xs text-text-muted">
            来源：{payload?.source === 'latest_run_summary' ? '最近一次翻译运行' : '手动重新审查'}
            {' · '}
            运行 ID：{payload?.run_id || '未知'}
            {' · '}
            完成时间：{formatTimestamp(payload?.finished_at)}
          </p>
        </div>
        <Button variant="outline" onClick={handleRerun} disabled={rerunning}>
          {rerunning ? '重新审查中...' : '重新审查'}
        </Button>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-text-muted">总问题数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{report.total_issues}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-text-muted">人工复核</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{report.manual_review_count}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-text-muted">可自动修复</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{report.auto_fixable_count}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-text-muted">整体结果</CardTitle>
          </CardHeader>
          <CardContent className="flex items-center gap-2">
            {report.is_consistent ? (
              <>
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                <span className="font-medium text-emerald-700">一致</span>
              </>
            ) : (
              <>
                <AlertCircle className="h-5 w-5 text-amber-600" />
                <span className="font-medium text-amber-700">需复核</span>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-3">
        {report.issues.map((issue, index) => (
          <Card key={`${issue.section_id}-${issue.paragraph_index}-${index}`} className={issueTone(issue.issue_type)}>
            <CardContent className="flex flex-col gap-3 p-5 md:flex-row md:items-start md:justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{issue.issue_type}</Badge>
                  {issue.auto_fixable && <Badge>可自动修复</Badge>}
                  <span className="text-xs text-text-muted">
                    {issue.section_id}:{issue.paragraph_index}
                  </span>
                </div>
                <p className="text-sm font-medium leading-6">{issue.description}</p>
                {issue.fix_suggestion && (
                  <p className="text-xs text-text-muted">
                    建议：{issue.fix_suggestion}
                  </p>
                )}
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <Button size="sm" onClick={() => onLocateIssue(issue)}>
                  定位到段落
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
