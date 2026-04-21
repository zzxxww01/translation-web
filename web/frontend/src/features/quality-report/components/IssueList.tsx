/**
 * 问题列表组件
 */

import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import type { BadgeProps } from '@/components/ui/badge';
import type { QualityIssue, IssueType, IssueSeverity, IssueStatus, SortBy } from '../types';

interface IssueListProps {
  issues: QualityIssue[];
  onIssueClick?: (issue: QualityIssue) => void;
}

const issueTypeLabels: Record<IssueType, string> = {
  accuracy: '准确性',
  readability: '可读性',
  terminology: '术语',
  consistency: '一致性',
  style: '风格',
};

const issueTypeColors = {
  accuracy: 'error',
  readability: 'warning',
  terminology: 'info',
  consistency: 'warning',
  style: 'default',
} as const satisfies Record<IssueType, NonNullable<BadgeProps['variant']>>;

const severityLabels: Record<IssueSeverity, string> = {
  critical: '严重',
  major: '重要',
  minor: '轻微',
};

const severityColors = {
  critical: 'error',
  major: 'warning',
  minor: 'default',
} as const satisfies Record<IssueSeverity, NonNullable<BadgeProps['variant']>>;

const statusLabels: Record<IssueStatus, string> = {
  pending: '待审核',
  auto_fixed: '已自动修复',
  manual_fixed: '已手动修复',
  dismissed: '已忽略',
};

const statusColors = {
  pending: 'warning',
  auto_fixed: 'success',
  manual_fixed: 'success',
  dismissed: 'default',
} as const satisfies Record<IssueStatus, NonNullable<BadgeProps['variant']>>;

const severityOrder: Record<IssueSeverity, number> = {
  critical: 0,
  major: 1,
  minor: 2,
};

const issueTypeBadgeVariant: Record<IssueType, NonNullable<BadgeProps['variant']>> = issueTypeColors;
const severityBadgeVariant: Record<IssueSeverity, NonNullable<BadgeProps['variant']>> = severityColors;
const statusBadgeVariant: Record<IssueStatus, NonNullable<BadgeProps['variant']>> = statusColors;

export function IssueList({ issues, onIssueClick }: IssueListProps) {
  const [filters, setFilters] = useState<{
    type: IssueType | 'all';
    severity: IssueSeverity | 'all';
    status: IssueStatus | 'all';
  }>({
    type: 'all',
    severity: 'all',
    status: 'all',
  });

  const [sortBy, setSortBy] = useState<SortBy>('severity');

  const filteredAndSortedIssues = useMemo(() => {
    let filtered = issues;

    if (filters.type !== 'all') {
      filtered = filtered.filter(issue => issue.type === filters.type);
    }
    if (filters.severity !== 'all') {
      filtered = filtered.filter(issue => issue.severity === filters.severity);
    }
    if (filters.status !== 'all') {
      filtered = filtered.filter(issue => issue.status === filters.status);
    }

    const sorted = [...filtered].sort((a, b) => {
      if (sortBy === 'severity') {
        return severityOrder[a.severity] - severityOrder[b.severity];
      } else if (sortBy === 'type') {
        return a.type.localeCompare(b.type);
      } else {
        return a.paragraph_index - b.paragraph_index;
      }
    });

    return sorted;
  }, [issues, filters, sortBy]);

  return (
    <div className="space-y-4">
      {/* 筛选和排序控制 */}
      <div className="flex flex-wrap gap-3">
        <Select value={filters.type} onValueChange={(value) => setFilters({ ...filters, type: value as IssueType | 'all' })}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部类型</SelectItem>
            {Object.entries(issueTypeLabels).map(([key, label]) => (
              <SelectItem key={key} value={key}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={filters.severity} onValueChange={(value) => setFilters({ ...filters, severity: value as IssueSeverity | 'all' })}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="严重程度" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部程度</SelectItem>
            {Object.entries(severityLabels).map(([key, label]) => (
              <SelectItem key={key} value={key}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={filters.status} onValueChange={(value) => setFilters({ ...filters, status: value as IssueStatus | 'all' })}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            {Object.entries(statusLabels).map(([key, label]) => (
              <SelectItem key={key} value={key}>{label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortBy)}>
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="排序" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="severity">按严重程度</SelectItem>
            <SelectItem value="type">按类型</SelectItem>
            <SelectItem value="paragraph">按段落</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* 问题列表 */}
      <div className="space-y-3">
        {filteredAndSortedIssues.length === 0 ? (
          <Card>
            <CardContent className="p-8 text-center text-gray-500">
              没有找到匹配的问题
            </CardContent>
          </Card>
        ) : (
          filteredAndSortedIssues.map((issue) => (
            <Card
              key={issue.id}
              className={cn(
                'transition-all hover:shadow-md',
                onIssueClick && 'cursor-pointer'
              )}
              onClick={() => onIssueClick?.(issue)}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex flex-wrap gap-2">
                    <Badge variant={issueTypeBadgeVariant[issue.type]}>
                      {issueTypeLabels[issue.type]}
                    </Badge>
                    <Badge variant={severityBadgeVariant[issue.severity]}>
                      {severityLabels[issue.severity]}
                    </Badge>
                    <Badge variant={statusBadgeVariant[issue.status]}>
                      {statusLabels[issue.status]}
                    </Badge>
                    <Badge variant="outline">段落 {issue.paragraph_index + 1}</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">问题描述</p>
                  <p className="text-sm text-gray-600">{issue.description}</p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">原文</p>
                    <p className="text-sm text-gray-700 bg-gray-50 p-2 rounded border">
                      {issue.source_text}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">译文</p>
                    <p className="text-sm text-gray-700 bg-gray-50 p-2 rounded border">
                      {issue.translation_text}
                    </p>
                  </div>
                </div>

                {issue.suggestion && (
                  <div>
                    <p className="text-xs font-medium text-blue-600 mb-1">修复建议</p>
                    <p className="text-sm text-blue-700 bg-blue-50 p-2 rounded border border-blue-200">
                      {issue.suggestion}
                    </p>
                  </div>
                )}

                {issue.fixed_text && (
                  <div>
                    <p className="text-xs font-medium text-green-600 mb-1">修复后文本</p>
                    <p className="text-sm text-green-700 bg-green-50 p-2 rounded border border-green-200">
                      {issue.fixed_text}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
