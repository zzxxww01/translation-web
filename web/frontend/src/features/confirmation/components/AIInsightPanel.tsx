/**
 * AI透明度面板组件
 * 显示AI翻译的详细信息和质量评分
 */

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '../../../shared/utils';
import type { AIInsight } from '../types';

interface AIInsightPanelProps {
  insight: AIInsight;
  className?: string;
}

export function AIInsightPanel({ insight, className }: AIInsightPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={cn('mt-3 rounded-md bg-muted/50 p-3', className)}>
      {/* 头部 */}
      <div className="mb-2 flex items-center justify-between">
        <span
          className={cn(
            'rounded px-2 py-0.5 text-xs font-medium',
            insight.is_excellent
              ? 'bg-success/20 text-success'
              : 'bg-info/20 text-info'
          )}
        >
          ✓ 质量评分: {insight.overall_score.toFixed(1)}/10
        </span>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary transition-colors"
        >
          {isExpanded ? '收起' : '查看详情'}
          {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {/* 简洁摘要 */}
      <div className="space-y-1.5 text-sm">
        {insight.applied_terms.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-text-secondary">术语:</span>
            <span className="font-medium text-text-primary">
              {insight.applied_terms.join('、')}
            </span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <span className="text-text-secondary">风格:</span>
          <span className="font-medium text-text-primary">{insight.style}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-text-secondary">步骤:</span>
          <span className="flex gap-1 text-xs">
            {insight.steps.understand ? '✓' : '○'}理解
            {insight.steps.translate ? '✓' : '○'}翻译
            {insight.steps.reflect ? '✓' : '○'}反思
            {insight.steps.refine ? '✓' : '○'}润色
          </span>
        </div>
      </div>

      {/* 详细信息（可折叠） */}
      {isExpanded && (
        <div className="mt-3 space-y-3 border-t border-border pt-3 text-sm">
          {/* 章节理解 */}
          {insight.understanding && (
            <div>
              <h4 className="mb-1 font-medium text-text-primary">章节理解</h4>
              <p className="text-text-secondary">{insight.understanding}</p>
            </div>
          )}

          {/* 评分详情 */}
          {insight.scores && (
            <div>
              <h4 className="mb-1 font-medium text-text-primary">评分详情</h4>
              <ul className="space-y-0.5 text-text-secondary">
                <li>可读性: {insight.scores.readability.toFixed(1)}/10</li>
                <li>准确性: {insight.scores.accuracy.toFixed(1)}/10</li>
              </ul>
            </div>
          )}

          {/* 发现的问题 */}
          {insight.issues && insight.issues.length > 0 && (
            <div>
              <h4 className="mb-1 font-medium text-text-primary">发现的问题</h4>
              <ul className="space-y-0.5 text-text-secondary">
                {insight.issues.map((issue, i) => (
                  <li key={i}>• {issue.description}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 模型信息 */}
          {insight.model && (
            <div>
              <h4 className="mb-1 font-medium text-text-primary">模型信息</h4>
              <p className="text-text-secondary text-xs">
                {insight.model}
                {insight.created_at && (
                  <span>
                    {' · '}
                    {new Date(insight.created_at).toLocaleString()}
                  </span>
                )}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
