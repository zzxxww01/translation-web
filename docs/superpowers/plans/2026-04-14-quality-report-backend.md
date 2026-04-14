# Plan 1: 后端质量报告服务和 API

**规格文档**: [docs/superpowers/specs/2026-04-14-quality-report-redesign.md](../specs/2026-04-14-quality-report-redesign.md)

**范围**: 后端数据服务和 API 端点，包括数据模型、服务层、路由层

**不包含**: 前端界面实现（见 Plan 2）

---

## 目标

实现后端质量报告服务，提供统一的 API 端点来聚合和查询四步法翻译生成的评审数据（section-critique、section-revision、consistency.json、run-summary.json），支持前端展示质量评分、问题列表、修复对比等功能。

---

## 实现步骤

### Step 1: 扩展数据模型

**文件**: `src/core/models/analysis.py`

**任务**:
1. 在现有 `TranslationIssue` 模型中添加字段：
   - `auto_fixed: bool = False` - 是否已自动修复
   - `revised_text: Optional[str] = None` - 修复后的文本
   - `fix_method: Optional[str] = None` - 修复方式（"step4_refine" | "step5_style_polish" | "consistency_auto_fix"）

2. 在现有 `ReflectionResult` 模型中添加字段：
   - `revised_translations: Optional[Dict[int, str]] = None` - Step 4 修复后的段落映射

3. 新增 `SectionQualityScore` 模型：
```python
class SectionQualityScore(BaseModel):
    section_id: str
    section_title: str
    overall_score: float
    readability_score: float
    accuracy_score: float
    conciseness_score: float
    is_excellent: bool
    issue_count: int
    auto_fixed_count: int
    manual_review_count: int
```

4. 新增 `QualityReportSummary` 模型：
```python
class QualityReportSummary(BaseModel):
    run_id: str
    project_id: str
    timestamp: str
    overall_score: float
    sections: List[SectionQualityScore]
    total_issues: int
    auto_fixed_issues: int
    manual_review_issues: int
    consistency_stats: Dict[str, Any]  # 来自 consistency.json
```

**验证**: 模型可以正常导入和实例化

---

### Step 2: 实现质量报告服务

**文件**: `src/services/quality_report_service.py` (新建)

**任务**:
1. 创建 `QualityReportService` 类，包含以下方法：

```python
class QualityReportService:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.artifacts_dir = project_root / "artifacts"
    
    def get_latest_report(self, project_id: str) -> Optional[QualityReportSummary]:
        """获取项目最新的质量报告"""
        # 1. 扫描 artifacts/runs/ 找到最新的 run_id
        # 2. 调用 get_report_by_run_id
    
    def get_report_by_run_id(self, run_id: str) -> Optional[QualityReportSummary]:
        """根据 run_id 生成质量报告"""
        # 1. 读取 run-summary.json 获取基础信息
        # 2. 读取 consistency.json 获取一致性统计
        # 3. 遍历 section-critique/*.json 聚合评分
        # 4. 遍历 section-revision/*.json 判断问题修复状态
        # 5. 调用 _merge_issues 合并问题列表
        # 6. 返回 QualityReportSummary
    
    def list_report_history(self, project_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """列出项目的历史报告（简化版）"""
        # 返回 [{run_id, timestamp, overall_score, total_issues}, ...]
    
    def get_section_issues(self, run_id: str, section_id: str) -> List[TranslationIssue]:
        """获取特定章节的问题列表（带修复状态）"""
        # 1. 读取 section-critique/{section_id}.json
        # 2. 读取 section-revision/{section_id}.json（如果存在）
        # 3. 标记 auto_fixed 和 revised_text
        # 4. 返回问题列表
    
    def _aggregate_section_scores(self, run_dir: Path) -> List[SectionQualityScore]:
        """聚合所有章节的评分"""
        # 遍历 section-critique/*.json，提取评分和问题统计
    
    def _merge_issues(self, run_dir: Path) -> Tuple[List[TranslationIssue], int, int]:
        """合并所有问题并标记修复状态"""
        # 1. 收集所有 section-critique/*.json 中的 issues
        # 2. 检查对应的 section-revision/*.json 判断是否修复
        # 3. 检查 consistency.json 中的 auto_fixable 问题
        # 4. 返回 (issues, auto_fixed_count, manual_review_count)
```

2. 实现问题修复状态判断逻辑：
   - 如果 `reflection.is_excellent == False` 且存在 `section-revision/{section_id}.json`，则该章节的问题标记为 `auto_fixed=True`
   - 如果 `issue.auto_fixable == True`（来自 consistency.json），标记为 `auto_fixed=True`
   - 其他问题标记为 `auto_fixed=False`（需要人工审核）

3. 实现评分聚合逻辑：
   - 全文 overall_score = 所有章节 overall_score 的加权平均（按段落数加权）
   - 各维度评分同理

**验证**: 单元测试覆盖所有方法，使用真实的 artifacts 数据测试

---

### Step 3: 实现 API 路由

**文件**: `src/api/routers/quality_report.py` (新建)

**任务**:
1. 创建路由文件，定义以下端点：

```python
from fastapi import APIRouter, HTTPException, Depends
from src.services.quality_report_service import QualityReportService
from src.core.models.analysis import QualityReportSummary, TranslationIssue

router = APIRouter(prefix="/api/quality-report", tags=["quality-report"])

@router.get("/projects/{project_id}/latest")
async def get_latest_quality_report(project_id: str) -> QualityReportSummary:
    """获取项目最新的质量报告"""
    service = QualityReportService(PROJECT_ROOT)
    report = service.get_latest_report(project_id)
    if not report:
        raise HTTPException(404, "No quality report found")
    return report

@router.get("/runs/{run_id}")
async def get_quality_report_by_run(run_id: str) -> QualityReportSummary:
    """根据 run_id 获取质量报告"""
    service = QualityReportService(PROJECT_ROOT)
    report = service.get_report_by_run_id(run_id)
    if not report:
        raise HTTPException(404, "Quality report not found")
    return report

@router.get("/projects/{project_id}/history")
async def get_quality_report_history(project_id: str, limit: int = 10):
    """获取项目的历史报告列表"""
    service = QualityReportService(PROJECT_ROOT)
    return service.list_report_history(project_id, limit)

@router.get("/runs/{run_id}/sections/{section_id}/issues")
async def get_section_issues(run_id: str, section_id: str) -> List[TranslationIssue]:
    """获取特定章节的问题列表"""
    service = QualityReportService(PROJECT_ROOT)
    issues = service.get_section_issues(run_id, section_id)
    return issues
```

2. 在 `src/api/routers/__init__.py` 中注册路由：
```python
from .quality_report import router as quality_report_router
# 在 app 中添加: app.include_router(quality_report_router)
```

**验证**: 使用 curl 或 Postman 测试所有端点，确保返回正确的数据

---

### Step 4: 更新模型导出

**文件**: `src/core/models/__init__.py`

**任务**:
1. 在 `__all__` 列表中添加新模型：
   - `SectionQualityScore`
   - `QualityReportSummary`

2. 确保新字段（`auto_fixed`, `revised_text`, `fix_method`, `revised_translations`）可以正常序列化和反序列化

**验证**: 导入测试通过

---

### Step 5: 集成测试

**任务**:
1. 使用真实的 artifacts 数据（如 `artifacts/runs/20260410_114905/`）测试完整流程：
   - 调用 `GET /api/quality-report/projects/{project_id}/latest`
   - 验证返回的 `QualityReportSummary` 包含正确的评分和问题统计
   - 验证 `auto_fixed` 和 `manual_review` 问题数量正确

2. 测试边界情况：
   - 项目没有 artifacts 数据
   - run_id 不存在
   - section-revision 文件缺失（部分章节未修复）
   - consistency.json 缺失

**验证**: 所有测试通过，边界情况正确处理

---

## 关键文件

### 新建文件
- `src/services/quality_report_service.py` - 质量报告服务
- `src/api/routers/quality_report.py` - API 路由

### 修改文件
- `src/core/models/analysis.py` - 扩展数据模型
- `src/core/models/__init__.py` - 导出新模型
- `src/api/routers/__init__.py` - 注册路由

---

## 数据流

```
前端请求
  ↓
GET /api/quality-report/projects/{project_id}/latest
  ↓
QualityReportService.get_latest_report()
  ↓
扫描 artifacts/runs/ 找到最新 run_id
  ↓
QualityReportService.get_report_by_run_id(run_id)
  ↓
读取 artifacts/runs/{run_id}/ 下的文件：
  - run-summary.json (基础信息)
  - consistency.json (一致性统计)
  - section-critique/*.json (评分和问题)
  - section-revision/*.json (修复状态)
  ↓
聚合数据 → QualityReportSummary
  ↓
返回 JSON 响应
```

---

## 边界处理

1. **文件缺失**:
   - `run-summary.json` 缺失 → 返回 404
   - `consistency.json` 缺失 → consistency_stats 为空字典
   - `section-revision/*.json` 缺失 → 该章节问题标记为 `auto_fixed=False`

2. **数据不一致**:
   - `section-critique` 中的 section_id 在 `run-summary.json` 中不存在 → 跳过该章节
   - `issues` 列表为空 → `issue_count=0`

3. **性能优化**:
   - 缓存最新报告（5分钟过期）
   - 懒加载章节问题（只在请求时读取）

---

## 验收标准

- [ ] 所有新模型可以正常导入和实例化
- [ ] `QualityReportService` 所有方法通过单元测试
- [ ] API 端点返回正确的数据结构
- [ ] 使用真实 artifacts 数据测试通过
- [ ] 边界情况正确处理（文件缺失、数据不一致）
- [ ] 问题修复状态判断逻辑正确（auto_fixed vs manual_review）
- [ ] 评分聚合逻辑正确（加权平均）

---

## 依赖

- 现有模型: `TranslationIssue`, `ReflectionResult`, `ConsistencyReport`
- 现有服务: 无（独立服务）
- 外部依赖: FastAPI, Pydantic

---

## 风险

1. **数据格式变化**: 如果 `section-critique` 或 `section-revision` 的 JSON 格式发生变化，需要更新解析逻辑
   - 缓解: 使用 Pydantic 模型验证，添加版本兼容性检查

2. **性能问题**: 如果 artifacts 文件很多，扫描和聚合可能较慢
   - 缓解: 添加缓存，懒加载章节问题

3. **并发访问**: 多个请求同时读取同一个 run 的文件
   - 缓解: 文件系统读取是线程安全的，无需额外处理

---

## 后续工作

完成后端实现后，继续 Plan 2: 前端质量报告界面
