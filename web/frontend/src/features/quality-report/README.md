# 质量报告功能 - 前端实现

## 概述

质量报告功能为翻译项目提供全面的质量分析和问题追踪界面，包括独立的质量报告页面和文档页面内的集成视图。

## 文件结构

```
web/frontend/src/features/quality-report/
├── api.ts                              # API 客户端和 React Query hooks
├── types.ts                            # TypeScript 类型定义
├── index.ts                            # 功能入口导出
├── QualityReportPage.tsx               # 独立质量报告页面
├── ConfirmationWithQuality.tsx         # 带质量面板的确认工作流包装器
├── INTEGRATION.ts                      # 集成说明
└── components/
    ├── index.ts                        # 组件导出
    ├── QualityStatsCard.tsx            # 统计卡片组件
    ├── IssueList.tsx                   # 问题列表组件（支持筛选、排序）
    ├── SectionQualityCard.tsx          # 章节质量卡片组件
    └── DocumentQualityPanel.tsx        # 文档页面质量面板组件
```

## 核心功能

### 1. 类型定义 (types.ts)

定义了质量报告相关的所有 TypeScript 类型：
- `QualityIssue`: 质量问题
- `SectionQualityReport`: 章节质量报告
- `ProjectQualityReport`: 项目质量报告

### 2. API 客户端 (api.ts)

使用 React Query 提供数据获取 hooks：
- `useProjectQualityReport(projectId)`: 获取项目质量报告
- `useSectionQualityReport(projectId, sectionId)`: 获取章节质量报告

### 3. 核心组件

#### QualityStatsCard
统计卡片组件，显示单个指标：
- 支持 4 种变体：default、success、warning、error
- 显示标题、数值和可选的副标题

#### IssueList
问题列表组件，功能包括：
- 按类型、严重程度、状态筛选
- 按严重程度、类型、段落排序
- 显示问题详情（描述、原文、译文、建议、修复后文本）
- 点击问题触发回调（用于跳转到对应位置）

#### SectionQualityCard
章节质量卡片组件，显示：
- 章节标题和总体评分
- 各维度评分（可读性、准确性、简洁性）
- 问题统计和修订次数
- 最终评估结果

#### DocumentQualityPanel
文档页面质量面板，支持：
- 当前章节/全文视图切换
- 显示章节评分和问题列表
- 点击问题滚动到对应段落
- 点击章节卡片滚动到对应章节

### 4. 页面组件

#### QualityReportPage
独立的质量报告页面，包含：
- 页面标题和元信息
- 全文统计概览（总体评分、问题总数、待审核、已修复）
- 问题分布图表（按严重程度、按状态）
- 章节质量列表
- 全部问题列表（支持筛选和排序）
- 点击问题/章节跳转到文档对应位置

#### ConfirmationWithQuality
带质量面板的确认工作流包装器：
- 在确认工作流右侧添加可折叠的质量面板
- 提供切换按钮显示/隐藏质量面板
- 保持原有确认工作流功能不变

## 路由配置

已在 `router.tsx` 中添加质量报告页面路由：

```typescript
{
  path: 'document/:projectId/quality-report',
  element: (
    <LazyPage>
      <QualityReportPage />
    </LazyPage>
  ),
}
```

访问路径：`/document/{projectId}/quality-report`

## 集成方式

### 方式 1: 使用 ConfirmationWithQuality 包装器（推荐）

在确认工作流中集成质量面板，修改 `router.tsx`：

```typescript
import { ConfirmationWithQuality } from './features/quality-report/ConfirmationWithQuality';

function ConfirmationRoute() {
  const { projectId = '' } = useParams<{ projectId: string }>();
  return (
    <LazyPage>
      <ConfirmationWithQuality projectId={projectId} />
    </LazyPage>
  );
}
```

### 方式 2: 添加导航按钮

在确认工作流或文档页面添加质量报告入口：

```typescript
import { BarChart3 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

<Button
  variant="outline"
  onClick={() => navigate(`/document/${projectId}/quality-report`)}
>
  <BarChart3 className="h-4 w-4" />
  质量报告
</Button>
```

### 方式 3: 在文档列表添加链接

在项目列表或文档侧边栏添加质量报告链接：

```typescript
<a href={`/document/${projectId}/quality-report`}>
  查看质量报告
</a>
```

## API 端点要求

前端期望后端提供以下 API 端点：

### 获取项目质量报告
```
GET /api/projects/{project_id}/quality-report
```

响应格式：
```typescript
{
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

### 获取章节质量报告
```
GET /api/projects/{project_id}/sections/{section_id}/quality-report
```

响应格式：
```typescript
{
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
```

## 样式和主题

所有组件使用现有的 UI 组件库和 Tailwind CSS：
- 使用 `Card`、`Button`、`Badge`、`Select` 等基础组件
- 遵循现有的颜色系统和间距规范
- 支持响应式布局

## 状态管理

- 使用 React Query 管理服务器状态（数据获取、缓存）
- 使用 React 本地状态管理 UI 状态（筛选、排序、视图切换）
- 缓存时间设置为 2 分钟

## 交互功能

1. **问题筛选和排序**
   - 按类型筛选：准确性、可读性、术语、一致性、风格
   - 按严重程度筛选：严重、重要、轻微
   - 按状态筛选：待审核、已自动修复、已手动修复、已忽略
   - 排序方式：按严重程度、按类型、按段落

2. **导航和跳转**
   - 点击问题跳转到文档对应段落
   - 点击章节卡片跳转到文档对应章节
   - 使用 URL hash 定位到具体位置

3. **视图切换**
   - 文档质量面板支持当前章节/全文视图切换
   - 质量面板可折叠/展开

## 边界情况处理

- 加载状态：显示加载动画
- 错误状态：显示错误信息和重试按钮
- 空状态：显示"暂无数据"提示
- 无问题状态：显示"没有找到匹配的问题"

## 后续优化建议

1. 添加问题的手动修复功能
2. 添加问题的忽略/恢复功能
3. 添加导出质量报告功能（PDF/Excel）
4. 添加质量趋势分析（多次翻译对比）
5. 添加图表可视化（使用 recharts 或类似库）
6. 添加实时协作功能（多人审核）

## 测试建议

### 单元测试
- 测试筛选和排序逻辑
- 测试组件渲染
- 测试 API hooks

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

## 依赖项

- React 18+
- React Router 6+
- @tanstack/react-query 5+
- Tailwind CSS
- Lucide React (图标)
- 现有的 UI 组件库

## 开发者注意事项

1. 所有组件都使用 TypeScript 严格模式
2. 遵循现有的代码风格和命名规范
3. 使用 `@/` 别名导入共享模块
4. 组件都有适当的 props 类型定义
5. 使用 `cn()` 工具函数合并 className
