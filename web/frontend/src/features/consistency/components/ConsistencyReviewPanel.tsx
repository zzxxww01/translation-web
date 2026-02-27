/**
 * 一致性审查面板组件
 * 显示审查结果和建议修正列表
 */

import { useState, useCallback } from 'react';
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  ChevronDown,
  ChevronRight,
  Zap,
  Eye,
  RefreshCw,
} from 'lucide-react';
import { Button } from '../../../components/ui';
import { cn } from '../../../shared/utils';

interface ConsistencyIssue {
  section_id: string;
  paragraph_index: number;
  issue_type: string;
  description: string;
  auto_fixable: boolean;
  fix_suggestion: string | null;
}

interface TermStats {
  [term: string]: {
    total_count: number;
    translations: { [key: string]: number };
    is_consistent: boolean;
    preferred?: string;
  };
}

interface Suggestion {
  issue_type: string;
  section_id: string;
  paragraph_index: number;
  description: string;
  action: string;
  auto_fixable: boolean;
  priority: number;
}

interface ConsistencyReviewResult {
  is_consistent: boolean;
  style_score: number;
  issue_count: number;
  auto_fixable_count: number;
  manual_review_count: number;
  term_stats: TermStats;
  suggestions: Suggestion[];
  issues: ConsistencyIssue[];
}

interface ConsistencyReviewPanelProps {
  result: ConsistencyReviewResult | null;
  isLoading: boolean;
  onRunReview: () => Promise<void>;
  onNavigateToParagraph?: (sectionId: string, paragraphIndex: number) => void;
}

const ISSUE_TYPE_LABELS: Record<string, string> = {
  terminology: '术语一致性',
  style: '风格一致性',
  reference: '交叉引用',
  data: '数据一致性',
  punctuation: '标点符号',
  proper_noun: '专有名词',
};

const ISSUE_TYPE_ICONS: Record<string, React.ReactNode> = {
  terminology: <AlertTriangle className="h-4 w-4" />,
  style: <AlertTriangle className="h-4 w-4" />,
  reference: <AlertTriangle className="h-4 w-4" />,
  data: <XCircle className="h-4 w-4" />,
  punctuation: <AlertTriangle className="h-4 w-4" />,
  proper_noun: <AlertTriangle className="h-4 w-4" />,
};

export function ConsistencyReviewPanel({
  result,
  isLoading,
  onRunReview,
  onNavigateToParagraph,
}: ConsistencyReviewPanelProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['suggestions']));

  const toggleSection = useCallback((section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  }, []);

  const getScoreColor = (score: number) => {
    if (score >= 90) return 'text-success';
    if (score >= 70) return 'text-warning';
    return 'text-error';
  };

  const getScoreBg = (score: number) => {
    if (score >= 90) return 'bg-success/10';
    if (score >= 70) return 'bg-warning/10';
    return 'bg-error/10';
  };

  // 按类型分组问题
  const issuesByType = result?.issues.reduce((acc, issue) => {
    if (!acc[issue.issue_type]) {
      acc[issue.issue_type] = [];
    }
    acc[issue.issue_type].push(issue);
    return acc;
  }, {} as Record<string, ConsistencyIssue[]>) || {};

  return (
    <div className="h-full flex flex-col">
      {/* 头部 */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-text-primary">一致性审查</h3>
          <Button
            variant="primary"
            size="sm"
            onClick={onRunReview}
            isLoading={isLoading}
            leftIcon={<RefreshCw className="h-4 w-4" />}
          >
            {isLoading ? '审查中...' : '开始审查'}
          </Button>
        </div>
        <p className="text-sm text-text-muted">
          检查术语一致性、风格统一性和数据准确性
        </p>
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!result && !isLoading && (
          <div className="text-center py-12">
            <div className="w-16 h-16 rounded-full bg-bg-hover mx-auto mb-4 flex items-center justify-center">
              <CheckCircle className="h-8 w-8 text-text-muted" />
            </div>
            <p className="text-text-muted">点击"开始审查"运行一致性检查</p>
          </div>
        )}

        {isLoading && (
          <div className="text-center py-12">
            <div className="w-16 h-16 rounded-full bg-primary/10 mx-auto mb-4 flex items-center justify-center animate-pulse">
              <RefreshCw className="h-8 w-8 text-primary animate-spin" />
            </div>
            <p className="text-text-muted">正在分析翻译一致性...</p>
          </div>
        )}

        {result && !isLoading && (
          <>
            {/* 总览卡片 */}
            <div className={cn(
              'rounded-xl p-4',
              result.is_consistent ? 'bg-success/10' : 'bg-warning/10'
            )}>
              <div className="flex items-center gap-3 mb-3">
                {result.is_consistent ? (
                  <CheckCircle className="h-6 w-6 text-success" />
                ) : (
                  <AlertTriangle className="h-6 w-6 text-warning" />
                )}
                <span className="font-medium text-text-primary">
                  {result.is_consistent ? '翻译一致性良好' : '发现一致性问题'}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-4 text-center">
                <div className={cn('rounded-lg p-3', getScoreBg(result.style_score))}>
                  <div className={cn('text-2xl font-bold', getScoreColor(result.style_score))}>
                    {result.style_score.toFixed(0)}
                  </div>
                  <div className="text-xs text-text-muted">风格评分</div>
                </div>
                <div className="rounded-lg p-3 bg-bg-hover">
                  <div className="text-2xl font-bold text-text-primary">
                    {result.issue_count}
                  </div>
                  <div className="text-xs text-text-muted">问题总数</div>
                </div>
                <div className="rounded-lg p-3 bg-bg-hover">
                  <div className="text-2xl font-bold text-primary">
                    {result.auto_fixable_count}
                  </div>
                  <div className="text-xs text-text-muted">可自动修复</div>
                </div>
              </div>
            </div>

            {/* 建议修正 */}
            {result.suggestions.length > 0 && (
              <div className="rounded-xl border border-border overflow-hidden">
                <button
                  onClick={() => toggleSection('suggestions')}
                  className="w-full flex items-center justify-between p-4 hover:bg-bg-hover transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Zap className="h-5 w-5 text-primary" />
                    <span className="font-medium text-text-primary">建议修正</span>
                    <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary text-xs">
                      {result.suggestions.length}
                    </span>
                  </div>
                  {expandedSections.has('suggestions') ? (
                    <ChevronDown className="h-5 w-5 text-text-muted" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-text-muted" />
                  )}
                </button>

                {expandedSections.has('suggestions') && (
                  <div className="border-t border-border divide-y divide-border">
                    {result.suggestions.map((suggestion, idx) => (
                      <div
                        key={idx}
                        className="p-4 hover:bg-bg-hover transition-colors cursor-pointer"
                        onClick={() => onNavigateToParagraph?.(suggestion.section_id, suggestion.paragraph_index)}
                      >
                        <div className="flex items-start gap-3">
                          <div className={cn(
                            'mt-0.5 p-1.5 rounded-lg',
                            suggestion.auto_fixable ? 'bg-primary/10 text-primary' : 'bg-warning/10 text-warning'
                          )}>
                            {suggestion.auto_fixable ? (
                              <Zap className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-sm text-text-primary mb-1">
                              {suggestion.description}
                            </div>
                            <div className="text-xs text-text-muted">
                              {suggestion.action}
                            </div>
                          </div>
                          <span className="text-xs text-text-muted whitespace-nowrap">
                            {ISSUE_TYPE_LABELS[suggestion.issue_type] || suggestion.issue_type}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 术语统计 */}
            {Object.keys(result.term_stats).length > 0 && (
              <div className="rounded-xl border border-border overflow-hidden">
                <button
                  onClick={() => toggleSection('terms')}
                  className="w-full flex items-center justify-between p-4 hover:bg-bg-hover transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-text-primary">术语使用统计</span>
                    <span className="px-2 py-0.5 rounded-full bg-bg-hover text-text-muted text-xs">
                      {Object.keys(result.term_stats).length}
                    </span>
                  </div>
                  {expandedSections.has('terms') ? (
                    <ChevronDown className="h-5 w-5 text-text-muted" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-text-muted" />
                  )}
                </button>

                {expandedSections.has('terms') && (
                  <div className="border-t border-border divide-y divide-border">
                    {Object.entries(result.term_stats).slice(0, 10).map(([term, stats]) => (
                      <div key={term} className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-text-primary">{term}</span>
                          <span className={cn(
                            'px-2 py-0.5 rounded-full text-xs',
                            stats.is_consistent ? 'bg-success/10 text-success' : 'bg-warning/10 text-warning'
                          )}>
                            {stats.is_consistent ? '一致' : '不一致'}
                          </span>
                        </div>
                        <div className="text-sm text-text-muted">
                          出现 {stats.total_count} 次
                          {Object.entries(stats.translations).map(([trans, count]) => (
                            <span key={trans} className="ml-2">
                              "{trans}" ({count}次)
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* 问题详情 */}
            {Object.keys(issuesByType).length > 0 && (
              <div className="rounded-xl border border-border overflow-hidden">
                <button
                  onClick={() => toggleSection('issues')}
                  className="w-full flex items-center justify-between p-4 hover:bg-bg-hover transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-text-primary">问题详情</span>
                    <span className="px-2 py-0.5 rounded-full bg-error/10 text-error text-xs">
                      {result.issue_count}
                    </span>
                  </div>
                  {expandedSections.has('issues') ? (
                    <ChevronDown className="h-5 w-5 text-text-muted" />
                  ) : (
                    <ChevronRight className="h-5 w-5 text-text-muted" />
                  )}
                </button>

                {expandedSections.has('issues') && (
                  <div className="border-t border-border">
                    {Object.entries(issuesByType).map(([type, issues]) => (
                      <div key={type} className="border-b border-border last:border-b-0">
                        <div className="px-4 py-2 bg-bg-tertiary flex items-center gap-2">
                          {ISSUE_TYPE_ICONS[type]}
                          <span className="text-sm font-medium text-text-primary">
                            {ISSUE_TYPE_LABELS[type] || type}
                          </span>
                          <span className="text-xs text-text-muted">
                            ({issues.length})
                          </span>
                        </div>
                        <div className="divide-y divide-border">
                          {issues.slice(0, 5).map((issue, idx) => (
                            <div
                              key={idx}
                              className="p-4 hover:bg-bg-hover transition-colors cursor-pointer"
                              onClick={() => onNavigateToParagraph?.(issue.section_id, issue.paragraph_index)}
                            >
                              <div className="flex items-start gap-3">
                                <div className={cn(
                                  'mt-0.5 p-1 rounded',
                                  issue.auto_fixable ? 'bg-primary/10 text-primary' : 'bg-text-muted/10 text-text-muted'
                                )}>
                                  {issue.auto_fixable ? '修' : '查'}
                                </div>
                                <div className="flex-1">
                                  <div className="text-sm text-text-primary">
                                    {issue.description}
                                  </div>
                                  {issue.fix_suggestion && (
                                    <div className="text-xs text-text-muted mt-1">
                                      {issue.fix_suggestion}
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                          {issues.length > 5 && (
                            <div className="p-4 text-center text-sm text-text-muted">
                              还有 {issues.length - 5} 个问题...
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
