# Plan 2: 前端质量报告界面

## 概述
实现质量报告的前端界面，包括独立的质量报告页面和文档页面内的集成视图。

## 前置条件
- Plan 1（后端质量报告服务和 API）已完成
- 后端 API 端点可用：
  - `GET /api/projects/{project_id}/quality-report`
  - `GET /api/projects/{project_id}/sections/{section_id}/quality-report`

## 实现步骤

### 第 1 步：创建质量报告数据类型定义
**文件**: `web/frontend/src/features/quality-report/types.ts`

创建 TypeScript 类型定义：
```typescript
export interface QualityIssue {
  id: string;
  type: 'accuracy' | 'readability' | 'terminology' | 'consistency' | 'style';
  severity: 'critical' | 'major' | 'minor';
  paragraph_index: number;
  source_text: string;
  translation_text: string;
  description: string;
  suggestion?: string;
  status: 'pending' | 'auto_fixed' | 'manual_fixed' | 'dismissed';
  fixed_text?: string;
}

export interface SectionQualityReport {
  section_id: string;
  section_title: string;
  overall_score: number;
  readability_score: number;
  accuracy_score: number;
  conciseness_score: number;
  is_excellent: boolean;
  issues: QualityIssue[];
  revision_count: number;
  final_assessment?: {
    passed: boolean;
    overall_score: number;
    failed_criteria: string[];
  };
}

export interface ProjectQualityReport {
  project_id: string;
  project_title: string;
  overall_score: number;
  total_issues: number;
  issues_by_status: Record<string, number>;
  issues_by_severity: Record<string, number>;
  sections: SectionQualityReport[];
  generated_at: string;
}
```

### 第 2 步：创建质量报告 API 客户端
**文件**: `web/frontend/src/features/quality-report/api.ts`

使用 React Query 创建数据获取 hooks：
```typescript
import { useQuery } from '@tanstack/react-query';
import { ProjectQualityReport, SectionQualityReport } from './types';

export function useProjectQualityReport(projectId: string) {
  return useQuery({
    queryKey: ['quality-report', projectId],
    queryFn: async () => {
      const response = await fetch(`/api/projects/${projectId}/quality-report`);
      if (!response.ok) throw new Error('Failed to fetch quality report');
      return response.json() as Promise<ProjectQualityReport>;
    },
    enabled: !!projectId,
  });
}

export function useSectionQualityReport(projectId: string, sectionId: string) {
  return useQuery({
    queryKey: ['quality-report', projectId, sectionId],
    queryFn: async () => {
      const response = await fetch(
        `/api/projects/${projectId}/sections/${sectionId}/quality-report`
      );
      if (!response.ok) throw new Error('Failed to fetch section quality report');
      return response.json() as Promise<SectionQualityReport>;
    },
    enabled: !!projectId && !!sectionId,
  });
}
```

### 第 3 步：创建质量报告统计卡片组件
**文件**: `web/frontend/src/features/quality-report/components/QualityStatsCard.tsx`

创建显示统计信息的卡片组件：
```typescript
interface QualityStatsCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  variant?: 'default' | 'success' | 'warning' | 'error';
}

export function QualityStatsCard({ title, value, subtitle, variant = 'default' }: QualityStatsCardProps) {
  // 实现统计卡片 UI
  // 根据 variant 显示不同颜色
  // 显示 title、value 和可选的 subtitle
}
```

### 第 4 步：创建问题列表组件
**文件**: `web/frontend/src/features/quality-report/components/IssueList.tsx`

创建可筛选、可排序的问题列表：
```typescript
interface IssueListProps {
  issues: QualityIssue[];
  onIssueClick?: (issue: QualityIssue) => void;
}

export function IssueList({ issues, onIssueClick }: IssueListProps) {
  const [filters, setFilters] = useState({
    type: 'all',
    severity: 'all',
    status: 'all',
  });
  
  const [sortBy, setSortBy] = useState<'severity' | 'type' | 'paragraph'>('severity');
  
  // 实现筛选和排序逻辑
  // 渲染问题列表，每个问题显示：
  // - 类型标签（颜色编码）
  // - 严重程度标签
  // - 状态标签（待审核/已自动修复/已手动修复/已忽略）
  // - 段落索引
  // - 问题描述
  // - 原文片段
  // - 译文片段
  // - 修复建议（如果有）
  // - 修复后文本（如果已修复）
}
```

### 第 5 步：创建章节质量卡片组件
**文件**: `web/frontend/src/features/quality-report/components/SectionQualityCard.tsx`

创建显示单个章节质量信息的卡片：
```typescript
interface SectionQualityCardProps {
  section: SectionQualityReport;
  onViewDetails?: () => void;
}

export function SectionQualityCard({ section, onViewDetails }: SectionQualityCardProps) {
  // 显示章节标题
  // 显示总体评分（带颜色指示器）
  // 显示各维度评分（可读性、准确性、简洁性）
  // 显示问题数量统计
  // 显示修订次数
  // 显示最终评估结果（如果有）
  // 提供"查看详情"按钮
}
```

### 第 6 步：创建独立质量报告页面
**文件**: `web/frontend/src/features/quality-report/QualityReportPage.tsx`

创建完整的质量报告页面：
```typescript
export function QualityReportPage() {
  const { projectId } = useParams();
  const { data: report, isLoading, error } = useProjectQualityReport(projectId!);
  
  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!report) return <EmptyState message="未找到质量报告" />;
  
  return (
    <div className="quality-report-page">
      {/* 页面标题和元信息 */}
      <header>
        <h1>质量报告</h1>
        <p>项目：{report.project_title}</p>
        <p>生成时间：{formatDate(report.generated_at)}</p>
      </header>
      
      {/* 全文统计概览 */}
      <section className="overview">
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
      </section>
      
      {/* 问题分布图表 */}
      <section className="charts">
        <div className="chart">
          <h3>按类型分布</h3>
          {/* 饼图或柱状图 */}
        </div>
        <div className="chart">
          <h3>按严重程度分布</h3>
          {/* 饼图或柱状图 */}
        </div>
      </section>
      
      {/* 章节质量列表 */}
      <section className="sections">
        <h2>章节质量</h2>
        {report.sections.map(section => (
          <SectionQualityCard
            key={section.section_id}
            section={section}
            onViewDetails={() => {
              // 导航到文档页面并高亮该章节
              navigate(`/projects/${projectId}/document#${section.section_id}`);
            }}
          />
        ))}
      </section>
      
      {/* 全部问题列表 */}
      <section className="all-issues">
        <h2>所有问题</h2>
        <IssueList
          issues={report.sections.flatMap(s => s.issues)}
          onIssueClick={(issue) => {
            // 导航到文档页面并定位到该段落
            const section = report.sections.find(s => 
              s.issues.some(i => i.id === issue.id)
            );
            if (section) {
              navigate(
                `/projects/${projectId}/document#${section.section_id}-p${issue.paragraph_index}`
              );
            }
          }}
        />
      </section>
    </div>
  );
}
```

### 第 7 步：创建文档页面内的质量面板组件
**文件**: `web/frontend/src/features/quality-report/components/DocumentQualityPanel.tsx`

创建嵌入文档页面的质量面板：
```typescript
interface DocumentQualityPanelProps {
  projectId: string;
  currentSectionId?: string;
}

export function DocumentQualityPanel({ projectId, currentSectionId }: DocumentQualityPanelProps) {
  const { data: report } = useProjectQualityReport(projectId);
  const { data: sectionReport } = useSectionQualityReport(
    projectId,
    currentSectionId || ''
  );
  
  const [view, setView] = useState<'current' | 'all'>('current');
  
  return (
    <div className="document-quality-panel">
      {/* 视图切换 */}
      <div className="view-toggle">
        <button
          onClick={() => setView('current')}
          className={view === 'current' ? 'active' : ''}
        >
          当前章节
        </button>
        <button
          onClick={() => setView('all')}
          className={view === 'all' ? 'active' : ''}
        >
          全文
        </button>
      </div>
      
      {/* 当前章节视图 */}
      {view === 'current' && sectionReport && (
        <div className="current-section-view">
          <h3>{sectionReport.section_title}</h3>
          
          {/* 章节评分 */}
          <div className="section-scores">
            <QualityStatsCard
              title="总体评分"
              value={sectionReport.overall_score}
              variant={getScoreVariant(sectionReport.overall_score)}
            />
            <QualityStatsCard
              title="可读性"
              value={sectionReport.readability_score}
            />
            <QualityStatsCard
              title="准确性"
              value={sectionReport.accuracy_score}
            />
            <QualityStatsCard
              title="简洁性"
              value={sectionReport.conciseness_score}
            />
          </div>
          
          {/* 章节问题列表 */}
          <IssueList
            issues={sectionReport.issues}
            onIssueClick={(issue) => {
              // 滚动到对应段落
              const element = document.getElementById(
                `${currentSectionId}-p${issue.paragraph_index}`
              );
              element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }}
          />
        </div>
      )}
      
      {/* 全文视图 */}
      {view === 'all' && report && (
        <div className="all-sections-view">
          <div className="overview-stats">
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
          
          {/* 章节列表 */}
          {report.sections.map(section => (
            <SectionQualityCard
              key={section.section_id}
              section={section}
              onViewDetails={() => {
                // 滚动到该章节
                const element = document.getElementById(section.section_id);
                element?.scrollIntoView({ behavior: 'smooth' });
                // 切换到当前章节视图
                setView('current');
              }}
            />
          ))}
        </div>
      )}
      
      {/* 查看完整报告链接 */}
      <div className="full-report-link">
        <a href={`/projects/${projectId}/quality-report`}>
          查看完整质量报告 →
        </a>
      </div>
    </div>
  );
}
```

### 第 8 步：集成到文档页面
**文件**: `web/frontend/src/features/document/DocumentPage.tsx`

修改现有文档页面，添加质量面板：
```typescript
// 在 DocumentPage 组件中添加质量面板
export function DocumentPage() {
  const { projectId } = useParams();
  const [currentSectionId, setCurrentSectionId] = useState<string>();
  
  // ... 现有代码 ...
  
  return (
    <div className="document-page">
      <div className="document-content">
        {/* 现有文档内容 */}
      </div>
      
      {/* 添加质量面板 */}
      <aside className="quality-panel-sidebar">
        <DocumentQualityPanel
          projectId={projectId!}
          currentSectionId={currentSectionId}
        />
      </aside>
    </div>
  );
}
```

### 第 9 步：添加路由配置
**文件**: `web/frontend/src/router.tsx`

添加质量报告页面路由：
```typescript
const QualityReportPage = lazy(() => 
  import('./features/quality-report/QualityReportPage').then(m => ({ 
    default: m.QualityReportPage 
  }))
);

// 在路由配置中添加
{
  path: '/projects/:projectId/quality-report',
  element: <QualityReportPage />,
}
```

### 第 10 步：添加导航入口
**文件**: `web/frontend/src/features/project/ProjectNavigation.tsx`

在项目导航中添加质量报告入口：
```typescript
// 在项目导航菜单中添加
<NavLink to={`/projects/${projectId}/quality-report`}>
  <Icon name="chart-bar" />
  质量报告
</NavLink>
```

### 第 11 步：样式实现
**文件**: `web/frontend/src/features/quality-report/styles.css`

实现质量报告相关组件的样式：
- 统计卡片样式（不同 variant 的颜色）
- 问题列表样式（类型/严重程度/状态标签颜色）
- 章节质量卡片样式
- 质量面板侧边栏样式
- 响应式布局

### 第 12 步：添加图表可视化（可选）
**文件**: `web/frontend/src/features/quality-report/components/QualityCharts.tsx`

使用图表库（如 recharts）添加数据可视化：
- 问题类型分布饼图
- 问题严重程度分布柱状图
- 章节评分趋势图

## 测试验证

### 单元测试
- 测试数据获取 hooks
- 测试筛选和排序逻辑
- 测试组件渲染

### 集成测试
- 测试质量报告页面完整流程
- 测试文档页面质量面板交互
- 测试导航和路由跳转

### 手动测试场景
1. 访问质量报告页面，验证数据正确显示
2. 筛选和排序问题列表
3. 点击问题跳转到文档对应位置
4. 在文档页面查看当前章节质量
5. 切换全文/当前章节视图
6. 验证响应式布局

## 边界情况处理
- 无质量报告数据时显示空状态
- API 请求失败时显示错误信息
- 加载状态显示
- 章节无问题时显示"无问题"状态
- 处理 URL 中的章节/段落锚点定位

## 依赖关系
- 依赖 Plan 1 的后端 API
- 需要现有的 React Query 和 Zustand 配置
- 需要现有的 UI 组件库（按钮、卡片等）

## 预估工作量
- 类型定义和 API 客户端：1 小时
- 基础组件（统计卡片、问题列表）：3 小时
- 质量报告页面：4 小时
- 文档页面集成：2 小时
- 路由和导航：1 小时
- 样式实现：2 小时
- 测试和调试：3 小时
- 总计：约 16 小时

## 后续优化
- 添加问题的手动修复功能
- 添加问题的忽略/恢复功能
- 添加导出质量报告功能（PDF/Excel）
- 添加质量趋势分析（多次翻译对比）
- 添加实时协作功能（多人审核）
