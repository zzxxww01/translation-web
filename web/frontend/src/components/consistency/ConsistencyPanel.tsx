import React, { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button-extended';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, CheckCircle, Info } from 'lucide-react';

interface ConsistencyIssue {
  section_id: string;
  paragraph_index: number;
  issue_type: string;
  description: string;
  auto_fixable: boolean;
  fix_suggestion?: string | null;
}

interface ConsistencyPanelProps {
  projectId: string;
}

type IssueFilter = 'all' | 'auto' | 'manual';
const ISSUE_FILTER_OPTIONS: Array<{ value: IssueFilter; label: string }> = [
  { value: 'all', label: '全部' },
  { value: 'auto', label: '可自动修复' },
  { value: 'manual', label: '需人工审核' },
];

export const ConsistencyPanel: React.FC<ConsistencyPanelProps> = ({ projectId }) => {
  const [isReviewing, setIsReviewing] = useState(false);
  const [report, setReport] = useState<{
    is_consistent: boolean;
    style_score: number;
    issue_count: number;
    auto_fixable_count: number;
    manual_review_count: number;
    issues: ConsistencyIssue[];
  } | null>(null);
  const [filter, setFilter] = useState<IssueFilter>('all');

  const startReview = async () => {
    setIsReviewing(true);
    try {
      const response = await fetch(`/api/projects/${projectId}/consistency-review`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error(`Review failed: ${response.status}`);
      }
      const data = await response.json();
      setReport(data);
    } catch (error) {
      console.error('Consistency review failed:', error);
    } finally {
      setIsReviewing(false);
    }
  };

  const filteredIssues = report?.issues.filter((issue) => {
    if (filter === 'all') return true;
    if (filter === 'auto') return issue.auto_fixable;
    return !issue.auto_fixable;
  }) || [];

  const getIssueIcon = (issue: ConsistencyIssue) => {
    return issue.auto_fixable
      ? <CheckCircle className="w-4 h-4 text-green-600" />
      : <AlertCircle className="w-4 h-4 text-amber-600" />;
  };

  const getIssueColor = (issue: ConsistencyIssue) => {
    return issue.auto_fixable
      ? 'bg-green-50 text-green-800 border-green-200'
      : 'bg-amber-50 text-amber-800 border-amber-200';
  };

  return (
    <div className="space-y-6">
      {/* 头部 */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">一致性审查</h2>
          <p className="text-sm text-gray-500 mt-1">
            检查术语翻译和风格的一致性
          </p>
        </div>
        <Button
          onClick={startReview}
          disabled={isReviewing}
          size="lg"
        >
          {isReviewing ? '审查中...' : '开始审查'}
        </Button>
      </div>

      {/* 统计卡片 */}
      {report && (
        <div className="grid grid-cols-4 gap-4">
          <Card className="p-4">
            <div className="text-sm text-gray-500">总问题数</div>
            <div className="text-3xl font-bold text-gray-900 mt-1">
              {report.issue_count}
            </div>
          </Card>
          <Card className="p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFilter('auto')}>
            <div className="text-sm text-gray-500">可自动修复</div>
            <div className="text-3xl font-bold text-green-600 mt-1">
              {report.auto_fixable_count}
            </div>
          </Card>
          <Card className="p-4 cursor-pointer hover:shadow-md transition-shadow" onClick={() => setFilter('manual')}>
            <div className="text-sm text-gray-500">需人工审核</div>
            <div className="text-3xl font-bold text-amber-600 mt-1">
              {report.manual_review_count}
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-sm text-gray-500">风格评分</div>
            <div className="text-3xl font-bold text-blue-600 mt-1">
              {Math.round(report.style_score)}
            </div>
          </Card>
        </div>
      )}

      {/* 筛选器 */}
      {report && (
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600">筛选：</span>
          {ISSUE_FILTER_OPTIONS.map(({ value, label }) => (
            <Button
              key={value}
              variant={filter === value ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter(value)}
            >
              {label}
            </Button>
          ))}
        </div>
      )}

      {/* 问题列表 */}
      <div className="space-y-4">
        {filteredIssues.map((issue, index) => (
          <Card key={index} className={`p-6 border-l-4 ${getIssueColor(issue)}`}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  {getIssueIcon(issue)}
                  <h3 className="text-lg font-semibold text-gray-900">
                    {issue.description}
                  </h3>
                  <Badge variant={issue.auto_fixable ? 'secondary' : 'outline'}>
                    {issue.issue_type}
                  </Badge>
                </div>

                <div className="mt-3 space-y-2 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">位置：</span>
                    <span className="text-gray-600 ml-2">
                      {issue.section_id}:{issue.paragraph_index}
                    </span>
                  </div>

                  {issue.fix_suggestion && (
                    <div>
                      <span className="font-medium text-gray-700">建议值：</span>
                      <span className="text-green-600 ml-2 font-medium">
                        {issue.fix_suggestion}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </Card>
        ))}

        {report && filteredIssues.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500" />
            <p>未发现{filter !== 'all' ? `${filter === 'auto' ? '可自动修复' : '需人工审核'}` : ''}问题</p>
          </div>
        )}

        {!report && !isReviewing && (
          <div className="text-center py-12 text-gray-500">
            <Info className="w-12 h-12 mx-auto mb-3" />
            <p>点击"开始审查"检查翻译一致性</p>
          </div>
        )}
      </div>
    </div>
  );
};
