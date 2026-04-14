# 翻译质量报告系统重新设计

**日期**: 2026-04-14  
**状态**: 设计完成，待实现  
**作者**: Claude + 用户协作

## 1. 背景与问题

### 1.1 当前状态

**四步法翻译自动生成的评审数据**（保存在 `artifacts/runs/{run_id}/`）：
- `section-critique/*.json` - 每章节的反思评审（评分、问题诊断）
- `section-revision/*.json` - 每章节的润色结果（质量评估）
- `consistency.json` - 全文一致性报告（术语统计）
- `run-summary.json` - 翻译概览（耗时、段落数）

**前端"一致性报告"API**（`GET /consistency/report/{project_id}`）：
- 数据来源：`projects/{project_id}/consistency_report.json`
- 生成方式：手动调用 `POST /consistency/review`
- 功能：轻量级术语一致性检查
- 问题：与四步法生成的丰富评审数据完全脱节

### 1.2 核心问题

1. **数据孤岛**：四步法生成的详细评审数据前端无法访问
2. **功能鸡肋**：前端只能看到手动触发的轻量级术语检查
3. **信息缺失**：用户看不到翻译质量评分、问题诊断、修复建议
4. **逻辑矛盾**：所有问题已自动修复，查看报告毫无意义

### 1.3 用户需求

经过需求澄清，用户希望：
- **C. 人工审核队列**：显示所有问题（已修复 + 待审核），区分状态
- **D. 质量评分报告**：全文 + 章节级评分，了解翻译质量
- **两者粒度**：既有全文概览，也能下钻到每个章节的详细评分

## 2. 设计目标

### 2.1 核心目标

1. **整合评审数据**：将四步法生成的所有评审数据暴露给前端
2. **可视化质量**：提供直观的质量仪表盘和评分展示
3. **问题追踪**：清晰展示问题状态（已修复 vs 待审核）
4. **上下文集成**：在翻译上下文中查看问题，无缝跳转

### 2.2 非目标

- 不改变四步法的自动修复逻辑
- 不新增评审规则或检查项
- 不实现实时质量检查（仅展示已生成的报告）

## 3. 方案设计

### 3.1 整体架构

采用**混合方案**：独立质量报告页 + 文档页内嵌集成

**优势**：
- 独立页面：全局视角，适合质量审查和问题分析
- 内嵌集成：上下文查看，适合修改译文时参考
- 数据互通：两者可以相互跳转，形成闭环

**工作流**：
```
翻译完成 
  ↓
查看质量报告页（发现问题）
  ↓
点击问题 → 跳转到文档页对应段落
  ↓
在文档页看到问题标记和修复建议
  ↓
修改译文
  ↓
返回质量报告页查看整体进度
```

### 3.2 数据架构

#### 3.2.1 数据来源

```
artifacts/runs/{run_id}/
├── run-summary.json           # 翻译概览
├── consistency.json           # 全文一致性报告
├── section-critique/          # 每章节的反思评审
│   ├── 00-intro.json         # { reflection: { overall_score, issues[] } }
│   └── ...
└── section-revision/          # 每章节的润色结果
    ├── 00-intro.json         # { assessment: { passed, scores, failed_criteria } }
    └── ...
```

#### 3.2.2 API 端点

**新增路由**：`src/api/routers/quality_report.py`

```
GET /api/projects/{project_id}/quality-report
  → 返回最新一次翻译的完整质量报告
  → 参数: run_id (可选，默认最新)

GET /api/projects/{project_id}/quality-report/runs
  → 返回历史翻译记录列表

POST /api/projects/{project_id}/quality-report/issues/{issue_id}/mark-resolved
  → 标记问题已处理
```

#### 3.2.3 数据模型

```typescript
interface QualityReport {
  run_id: string;
  project_id: string;
  started_at: string;
  finished_at: string;
  
  // 全文评分
  overall: {
    score: number;              // 综合评分 (加权平均)
    readability: number;        // 可读性
    accuracy: number;           // 准确性
    conciseness: number;        // 简洁性
  };
  
  // 章节评分列表
  sections: Array<{
    section_id: string;
    title: string;
    score: number;              // 章节综合评分
    readability: number;
    accuracy: number;
    conciseness: number;
    is_excellent: boolean;
    issue_count: number;
  }>;
  
  // 问题列表
  issues: Array<{
    id: string;                 // 唯一标识
    section_id: string;
    paragraph_index: number;
    issue_type: string;         // accuracy, terminology, readability, tone, etc.
    severity: string;           // critical, high, medium, low
    status: string;             // auto_fixed, manual_review
    description: string;        // 问题描述
    suggestion: string;         // 修复建议
    original_text?: string;     // 原文片段
    fixed_text?: string;        // 修复后文本 (如果已自动修复)
  }>;
  
  // 一致性统计
  consistency: {
    is_consistent: boolean;
    term_stats: Record<string, {
      total_count: number;
      translations: Record<string, number>;
      is_consistent: boolean;
      preferred: string;
    }>;
  };
}
```

### 3.3 质量报告页设计

#### 3.3.1 页面路由

```
/projects/{project_id}/quality-report
```

**入口**：
- 文档页顶部"质量报告"按钮
- 翻译完成后自动弹出提示："翻译完成，查看质量报告"

#### 3.3.2 页面布局

**顶部：全文质量仪表盘**
```
┌─────────────────────────────────────────────────────┐
│  翻译质量报告                    [历史记录 ▼]        │
│  2026-04-09 02:40 - 03:13  |  耗时 33分钟           │
├─────────────────────────────────────────────────────┤
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐           │
│  │ 综合 │  │ 准确 │  │ 可读 │  │ 简洁 │           │
│  │ 8.9  │  │ 9.2  │  │ 8.5  │  │ 8.8  │           │
│  └──────┘  └──────┘  └──────┘  └──────┘           │
│                                                      │
│  问题统计：共 12 个问题                              │
│  ✅ 已自动修复 8 个  |  ⚠️ 待人工审核 4 个          │
└─────────────────────────────────────────────────────┘
```

**中部：章节评分列表**
```
┌─────────────────────────────────────────────────────┐
│  章节质量                        [按评分排序 ▼]      │
├─────────────────────────────────────────────────────┤
│  🟢 00-intro                                  9.0    │
│     准确 9.8 | 可读 8.5 | 简洁 9.0  |  1 个问题     │
│                                                      │
│  🟡 01-the-inevitability...                   7.8    │
│     准确 8.2 | 可读 7.5 | 简洁 7.6  |  5 个问题     │
│                                                      │
│  🟢 02-memory-cycle...                        8.5    │
│     准确 9.0 | 可读 8.2 | 简洁 8.3  |  2 个问题     │
└─────────────────────────────────────────────────────┘
```

**底部：问题审核队列**
```
┌─────────────────────────────────────────────────────┐
│  问题列表                                            │
│  [全部] [待审核] [已修复]  [按严重程度 ▼]           │
├─────────────────────────────────────────────────────┤
│  ⚠️ [待审核] 00-intro 段落 3                         │
│     类型: readability  |  严重程度: medium          │
│     译文中出现了大量不正常的排版空格...              │
│     建议: 去除多余的空格，并优化翻译腔               │
│     [查看段落] [标记已处理]                          │
│                                                      │
│  ✅ [已修复] 01-the-inevitability 段落 5             │
│     类型: terminology  |  严重程度: high            │
│     术语 "DRAM" 翻译不一致                           │
│     修复: 统一为 "DRAM"                              │
│     [查看修复对比]                                   │
└─────────────────────────────────────────────────────┘
```

#### 3.3.3 交互功能

1. **点击章节** → 展开该章节的所有问题
2. **点击"查看段落"** → 跳转到文档页对应段落
3. **点击"查看修复对比"** → 弹窗显示修复前后对比
4. **筛选和排序** → 按状态、类型、严重程度筛选
5. **历史记录下拉** → 查看之前的翻译批次报告

### 3.4 文档页内嵌集成

#### 3.4.1 章节标题增强

**改进后**：
```
## 00-intro  [🟢 9.0] [⚠️ 1]
Memory Mania: How A Once-In-Four-Decades...
```

**说明**：
- `[🟢 9.0]` = 评分徽章（绿色 ≥8.5，黄色 7.0-8.5，红色 <7.0）
- `[⚠️ 1]` = 问题数量（点击跳转到质量报告页该章节）
- 悬停显示 tooltip：准确性 9.8 | 可读性 8.5 | 简洁性 9.0

#### 3.4.2 段落问题标记

**在段落编辑器左侧添加问题指示器**：

```
┌─────────────────────────────────────────────────┐
│ ⚠️ │ We go through fab by fab production...    │
│    │ 我们将逐个晶圆厂的产量与扩产计划...        │
│    │                                            │
│    │ [编辑] [重译]                              │
└─────────────────────────────────────────────────┘
```

**点击 ⚠️ 图标**：
- 展开问题详情面板（侧边栏或弹窗）
- 显示：问题描述、修复建议、状态
- 提供操作：[查看完整报告] [标记已处理]

**悬停 ⚠️ 图标**：
- 显示问题摘要 tooltip

#### 3.4.3 顶部快速入口

```
┌─────────────────────────────────────────────────┐
│ [← 返回项目]  存储狂热  [导出] [质量报告 🟢 8.9] │
└─────────────────────────────────────────────────┘
```

**"质量报告"按钮**：
- 显示全文综合评分
- 点击跳转到质量报告页
- 如果有待审核问题，显示红点提示

#### 3.4.4 翻译完成提示

```
┌─────────────────────────────────────────────────┐
│  ✅ 翻译完成！                                   │
│                                                  │
│  综合评分：8.9 / 10                              │
│  发现 12 个问题，已自动修复 8 个                 │
│                                                  │
│  [查看质量报告]  [稍后查看]                      │
└─────────────────────────────────────────────────┘
```

## 4. 实现细节

### 4.1 后端实现

#### 4.1.1 新增服务

**文件**：`src/services/quality_report_service.py`

**核心职责**：
1. 从 `artifacts/runs/{run_id}/` 读取所有评审数据
2. 聚合计算全文评分（加权平均各章节评分）
3. 合并所有问题列表（section-critique + consistency）
4. 标记问题状态（auto_fixed vs manual_review）
5. 生成修复前后对比数据

**关键方法**：
```python
class QualityReportService:
    def get_latest_report(self, project_id: str) -> QualityReport:
        """获取最新一次翻译的质量报告"""
        
    def get_report_by_run_id(self, project_id: str, run_id: str) -> QualityReport:
        """获取指定批次的质量报告"""
        
    def list_report_history(self, project_id: str) -> List[ReportSummary]:
        """列出历史翻译记录"""
        
    def _aggregate_section_scores(self, sections_data: List) -> OverallScore:
        """聚合章节评分为全文评分"""
        
    def _merge_issues(self, critique_data: Dict, consistency_data: Dict) -> List[Issue]:
        """合并所有问题并标记状态"""
```

#### 4.1.2 问题状态判断逻辑

```python
def _determine_issue_status(self, issue: TranslationIssue, section_result: SectionTranslationResult) -> str:
    """
    判断问题状态：
    1. 如果 reflection.is_excellent = False 且有 issues
       → 触发了 Step 4 润色 → 标记为 auto_fixed
    2. 如果 issue.auto_fixable = True
       → 一致性审查自动修复 → 标记为 auto_fixed
    3. 否则 → 标记为 manual_review
    """
    if not section_result.reflection.is_excellent and section_result.revised_translations:
        return "auto_fixed"
    elif issue.auto_fixable:
        return "auto_fixed"
    else:
        return "manual_review"
```

#### 4.1.3 修复前后对比

```python
def _build_fix_comparison(self, issue: Issue, section: Section) -> Optional[FixComparison]:
    """
    构建修复对比：
    - original_text: section_result.draft_translations[paragraph_index]
    - fixed_text: section_result.revised_translations[paragraph_index]
    """
    if issue.status == "auto_fixed":
        return FixComparison(
            original=draft_translations[issue.paragraph_index],
            fixed=revised_translations[issue.paragraph_index],
            suggestion=issue.suggestion
        )
    return None
```

#### 4.1.4 数据持久化

**问题处理状态存储**：`artifacts/runs/{run_id}/issue-resolutions.json`

```json
{
  "issue_id_1": {
    "resolved_at": "2026-04-09T10:30:00",
    "resolved_by": "user",
    "note": "已手动修改段落"
  }
}
```

**优势**：
- 问题状态属于特定翻译批次，和该批次数据放在一起
- 不污染项目元数据
- 方便查看历史批次的问题处理情况

### 4.2 前端实现

#### 4.2.1 页面和组件结构

```
web/frontend/src/features/quality-report/
├── index.tsx                      # 质量报告页主入口
├── components/
│   ├── QualityDashboard.tsx      # 全文质量仪表盘
│   ├── SectionScoreList.tsx      # 章节评分列表
│   ├── IssueQueue.tsx            # 问题审核队列
│   ├── IssueCard.tsx             # 单个问题卡片
│   ├── FixComparisonModal.tsx    # 修复对比弹窗
│   └── HistorySelector.tsx       # 历史记录选择器
├── services/
│   └── qualityReportService.ts   # API 调用服务
└── types.ts                       # TypeScript 类型定义
```

**文档页集成组件**：
```
web/frontend/src/features/document/
├── components/
│   ├── SectionHeader.tsx         # 增强：添加评分徽章
│   ├── ParagraphEditor.tsx       # 增强：添加问题标记
│   ├── IssueIndicator.tsx        # 新增：问题指示器
│   └── IssueDetailPanel.tsx      # 新增：问题详情面板
```

#### 4.2.2 状态管理

**使用 Zustand**：

```typescript
interface QualityReportStore {
  // 数据
  currentReport: QualityReport | null;
  reportHistory: ReportSummary[];
  selectedRunId: string | null;
  
  // 筛选和排序
  issueFilter: 'all' | 'manual_review' | 'auto_fixed';
  issueSort: 'severity' | 'type' | 'section';
  
  // 操作
  fetchReport: (projectId: string, runId?: string) => Promise<void>;
  fetchHistory: (projectId: string) => Promise<void>;
  setIssueFilter: (filter: string) => void;
  markIssueResolved: (issueId: string) => Promise<void>;
}
```

#### 4.2.3 关键交互逻辑

**1. 从问题跳转到段落**：

```typescript
const handleViewParagraph = (issue: Issue) => {
  navigate(`/projects/${projectId}/document`, {
    state: {
      scrollTo: {
        sectionId: issue.section_id,
        paragraphIndex: issue.paragraph_index
      },
      highlightIssue: issue.id
    }
  });
};
```

**2. 文档页接收跳转参数**：

```typescript
const location = useLocation();
const { scrollTo, highlightIssue } = location.state || {};

useEffect(() => {
  if (scrollTo) {
    scrollToParagraph(scrollTo.sectionId, scrollTo.paragraphIndex);
    if (highlightIssue) {
      highlightIssueIndicator(highlightIssue);
    }
  }
}, [scrollTo, highlightIssue]);
```

**3. 实时更新问题状态**：

```typescript
const handleParagraphUpdate = async (paragraphId: string, newText: string) => {
  await updateParagraph(paragraphId, newText);
  
  const relatedIssues = getIssuesForParagraph(paragraphId);
  if (relatedIssues.length > 0) {
    showToast({
      title: "检测到问题修改",
      description: "是否标记相关问题为已处理？",
      action: () => markIssuesResolved(relatedIssues.map(i => i.id))
    });
  }
};
```

#### 4.2.4 UI 组件库

**基于 shadcn/ui**：
- `Card` - 评分卡片、问题卡片
- `Badge` - 评分徽章、状态标签
- `Tabs` - 问题筛选标签
- `Select` - 排序选择器、历史记录选择器
- `Dialog` - 修复对比弹窗
- `Tooltip` - 悬停提示
- `Progress` - 评分进度条
- `Alert` - 翻译完成提示

#### 4.2.5 响应式设计

- **桌面端**（≥1024px）：三栏布局
- **平板端**（768px - 1023px）：两栏布局
- **移动端**（<768px）：单栏布局，垂直滚动

## 5. 数据流

### 5.1 完整数据流

```
翻译完成
  ↓
BatchTranslationService
  ├─ FourStepTranslator (生成 section-critique, section-revision)
  └─ ConsistencyReviewer (生成 consistency.json)
  ↓
保存到 artifacts/runs/{run_id}/
  ↓
前端请求 GET /quality-report
  ↓
QualityReportService
  ├─ 读取所有评审数据
  ├─ 聚合评分
  ├─ 合并问题
  └─ 判断状态
  ↓
返回 QualityReport
  ↓
前端渲染质量报告页
```

### 5.2 边界情况处理

**情况 1：没有评审数据**
- **场景**：使用普通翻译模式（非四步法）
- **处理**：显示"此翻译未生成质量报告（仅四步法翻译支持）"

**情况 2：评审数据不完整**
- **场景**：翻译中途取消
- **处理**：只显示已完成章节，标记未完成章节为"未评审"

**情况 3：历史数据兼容**
- **场景**：旧批次没有 `section-revision` 数据
- **处理**：降级显示，只显示 reflection 数据

**情况 4：artifacts 目录被删除**
- **场景**：用户手动清理
- **处理**：返回 404，提示"质量报告数据已丢失"

**情况 5：问题已在文档页修改**
- **场景**：段落已修改但问题状态未更新
- **处理**：显示"段落已修改"提示，提供"标记已解决"按钮

## 6. 性能优化

### 6.1 后端优化

```python
@lru_cache(maxsize=10)
def get_report_by_run_id(self, project_id: str, run_id: str) -> QualityReport:
    """缓存最近 10 个报告"""
```

### 6.2 前端优化

- 问题列表虚拟滚动（如果问题数量 > 100）
- 图表按需渲染（进入视口才渲染）
- 使用 React Query 缓存 API 响应

## 7. 扩展性设计

### 7.1 预留扩展点

1. **问题优先级排序** - 未来可加入 AI 推荐优先级
2. **批次对比** - 对比两次翻译的质量变化
3. **导出报告** - 导出 PDF/Excel 报告
4. **问题讨论** - 添加评论、讨论修改方案
5. **质量趋势** - 显示项目历史翻译质量趋势图

## 8. 实现优先级

### Phase 1：核心功能（MVP）
1. 后端：QualityReportService + API 路由
2. 前端：质量报告页（仪表盘 + 章节列表 + 问题队列）
3. 数据流：从 artifacts 读取并聚合数据

### Phase 2：文档页集成
1. 章节标题评分徽章
2. 段落问题标记
3. 跳转和高亮逻辑

### Phase 3：增强功能
1. 修复前后对比弹窗
2. 问题状态标记
3. 历史记录查看

### Phase 4：优化和扩展
1. 性能优化（缓存、虚拟滚动）
2. 响应式设计
3. 导出报告功能

## 9. 成功标准

### 9.1 功能完整性
- ✅ 用户能查看全文和章节级评分
- ✅ 用户能看到所有问题（已修复 + 待审核）
- ✅ 用户能从问题跳转到对应段落
- ✅ 用户能在文档页看到问题标记

### 9.2 用户体验
- ✅ 翻译完成后自动提示查看报告
- ✅ 问题列表支持筛选和排序
- ✅ 修复前后对比清晰可见
- ✅ 响应式设计适配各种屏幕

### 9.3 性能指标
- ✅ 报告页加载时间 < 2 秒
- ✅ 问题列表滚动流畅（60fps）
- ✅ API 响应时间 < 500ms

## 10. 风险和缓解

### 10.1 数据兼容性风险
- **风险**：旧批次数据格式不同
- **缓解**：实现降级显示逻辑，兼容旧格式

### 10.2 性能风险
- **风险**：大量问题导致页面卡顿
- **缓解**：虚拟滚动 + 分页加载

### 10.3 用户理解风险
- **风险**：用户不理解"已修复"的含义
- **缓解**：提供修复前后对比，清晰说明自动修复逻辑

## 11. 后续迭代方向

1. **智能推荐**：基于问题类型和严重程度，AI 推荐优先处理的问题
2. **协作功能**：多人协作时，问题分配和讨论
3. **质量预测**：基于历史数据，预测翻译质量
4. **自定义规则**：用户自定义评审规则和阈值
