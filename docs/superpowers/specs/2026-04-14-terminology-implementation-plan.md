# 术语系统重构实施计划

**日期**: 2026-04-14  
**关联设计**: `2026-04-14-terminology-system-redesign.md`

---

## 实施策略

### 原则
1. **分阶段实施** — 每个阶段可独立验证
2. **向后兼容** — 保留旧 API 作为兼容层
3. **测试先行** — 每个模块先写测试
4. **增量迁移** — 新旧系统并存，逐步切换

### 里程碑

```
Milestone 1: 存储层 (Week 1-2)
  ↓
Milestone 2: 匹配引擎 (Week 2-3)
  ↓
Milestone 3: 确认流程 (Week 3-4)
  ↓
Milestone 4: 会话管理 (Week 4-5)
  ↓
Milestone 5: 翻译集成 (Week 5-6)
  ↓
Milestone 6: 数据迁移 (Week 6-7)
  ↓
Milestone 7: 上线切换 (Week 7-8)
```

---

## Milestone 1: 存储层 (Week 1-2)

### 目标
实现新的数据模型和存储层，支持读写、查询、关系管理。

### 任务清单

#### Task 1.1: 数据模型定义
**文件**: `src/core/models/terminology.py`

**内容**:
```python
# 新增模型
- Term
- TermMetadata
- TermDecisionRecord
- TranslationSession
- TermCandidate
- TermConflict
- ConfirmationPackage
```

**验收标准**:
- [ ] 所有模型定义完整
- [ ] Pydantic 验证通过
- [ ] 类型提示完整
- [ ] 文档字符串完整

**预计时间**: 1 天

---

#### Task 1.2: ID 生成器
**文件**: `src/core/terminology/id_generator.py`

**内容**:
```python
def generate_term_id(original: str, scope: str, project_id: Optional[str] = None) -> str:
    """
    使用 UUID v5 确定性生成术语 ID
    - global: 基于 NAMESPACE_GLOBAL + original.lower()
    - project: 基于 NAMESPACE_PROJECT + f"{project_id}:{original.lower()}"
    """
```

**验收标准**:
- [ ] 同一术语生成相同 ID（幂等性）
- [ ] 不同 scope 生成不同 ID
- [ ] 大小写不敏感
- [ ] 单元测试覆盖

**预计时间**: 0.5 天

---

#### Task 1.3: 存储层实现
**文件**: `src/core/terminology/storage.py`

**内容**:
```python
class GlossaryStorage:
    def load_terms(self, scope: str, project_id: Optional[str] = None) -> List[Term]
    def save_terms(self, terms: List[Term], scope: str, project_id: Optional[str] = None)
    def load_metadata(self, scope: str, project_id: Optional[str] = None) -> List[TermMetadata]
    def save_metadata(self, metadata: List[TermMetadata], scope: str, project_id: Optional[str] = None)
    def load_effective_terms(self, project_id: str) -> tuple[List[Term], List[TermMetadata]]
    def find_global_term(self, original: str) -> Optional[Term]
    def save_term(self, term: Term, scope: str, project_id: Optional[str] = None, overrides_term_id: Optional[str] = None)
    def delete_term(self, term_id: str, scope: str, project_id: Optional[str] = None)

class SessionStorage:
    def save_session(self, session: TranslationSession)
    def load_session(self, session_id: str) -> TranslationSession
    def list_sessions(self, project_id: str) -> List[TranslationSession]
    def delete_session(self, session_id: str)

class AuditStorage:
    def append_decision(self, record: TermDecisionRecord, project_id: str)
    def load_decisions(self, project_id: str, term_original: Optional[str] = None) -> List[TermDecisionRecord]
```

**验收标准**:
- [ ] 所有方法实现完整
- [ ] 文件读写正确
- [ ] 覆盖关系正确处理
- [ ] 软删除正确实现
- [ ] 单元测试覆盖 > 90%

**预计时间**: 3 天

---

#### Task 1.4: 存储层集成测试
**文件**: `tests/integration/test_terminology_storage.py`

**测试场景**:
```python
def test_save_and_load_global_terms()
def test_save_and_load_project_terms()
def test_project_overrides_global()
def test_load_effective_terms()
def test_soft_delete()
def test_audit_log_append()
def test_session_persistence()
```

**验收标准**:
- [ ] 所有测试通过
- [ ] 覆盖率 > 90%
- [ ] 边界情况覆盖

**预计时间**: 2 天

---

### Milestone 1 验收

- [ ] 数据模型定义完整
- [ ] 存储层实现完整
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 代码审查通过

---

## Milestone 2: 匹配引擎 (Week 2-3)

### 目标
实现高准确率的术语匹配引擎，支持分类匹配和边界验证。

### 任务清单

#### Task 2.1: 术语分类器
**文件**: `src/core/terminology/classifier.py`

**内容**:
```python
class TermType(Enum):
    SHORT_ACRONYM = "short_acronym"
    MIXED_CASE = "mixed_case"
    COMMON_WORD = "common_word"
    SPECIAL_CHAR = "special_char"
    CHINESE = "chinese"

class TermClassifier:
    @staticmethod
    def classify(original: str) -> TermType
```

**验收标准**:
- [ ] 分类逻辑正确
- [ ] 单元测试覆盖所有类型
- [ ] 边界情况覆盖

**预计时间**: 1 天

---

#### Task 2.2: 正则预编译器
**文件**: `src/core/terminology/pattern_compiler.py`

**内容**:
```python
class CompiledPattern:
    pattern: re.Pattern
    term_type: TermType
    requires_validation: bool

class PatternCompiler:
    def __init__(self)
    def compile(self, term: Term) -> CompiledPattern
    def _compile_short_acronym(self, term_lower: str) -> CompiledPattern
    def _compile_mixed_case(self, term_lower: str) -> CompiledPattern
    def _compile_common_word(self, term_lower: str) -> CompiledPattern
    def _compile_special_char(self, term_lower: str) -> CompiledPattern
    def _compile_chinese(self, term: str) -> CompiledPattern
```

**验收标准**:
- [ ] 所有类型编译正确
- [ ] 缓存机制工作
- [ ] 单元测试覆盖

**预计时间**: 2 天

---

#### Task 2.3: 匹配验证器
**文件**: `src/core/terminology/match_validator.py`

**内容**:
```python
class MatchValidator:
    @staticmethod
    def validate(text: str, match: re.Match, term_type: TermType) -> bool
```

**验收标准**:
- [ ] 短缩写验证正确（AI 不匹配 DRAM）
- [ ] 单元测试覆盖

**预计时间**: 1 天

---

#### Task 2.4: 术语匹配器
**文件**: `src/core/terminology/matcher.py`

**内容**:
```python
class MatchResult:
    term_id: str
    term_original: str
    start: int
    end: int
    matched_text: str

class TermMatcher:
    def __init__(self, terms: List[Term])
    def match_all(self, text: str) -> List[MatchResult]
    def match_term(self, text: str, term_id: str) -> List[MatchResult]
    def _match_chinese(self, text: str, term: str) -> List[re.Match]
```

**验收标准**:
- [ ] 所有匹配策略正确
- [ ] 性能达标（< 10ms / 1000 字）
- [ ] 单元测试覆盖

**预计时间**: 2 天

---

#### Task 2.5: 匹配引擎回归测试
**文件**: `tests/test_term_matcher_regression.py`

**测试用例**:
```python
# 短缩写
def test_short_acronym_ai_not_in_dram()
def test_short_acronym_case_insensitive()

# 混合大小写
def test_mixed_case_cowos()
def test_mixed_case_hbm3e_not_hbm3()

# 普通词
def test_common_word_memory()
def test_common_word_plural_memories()

# 中文
def test_chinese_substring()

# 性能
def test_performance_100_terms_1000_chars()
```

**验收标准**:
- [ ] 准确率 > 95%
- [ ] 所有测试通过
- [ ] 性能达标

**预计时间**: 2 天

---

### Milestone 2 验收

- [ ] 匹配引擎实现完整
- [ ] 准确率 > 95%
- [ ] 性能达标
- [ ] 回归测试通过
- [ ] 代码审查通过

---

## Milestone 3: 确认流程 (Week 3-4)

### 目标
实现术语确认流程，包括提取、冲突检测、用户决策应用。

### 任务清单

#### Task 3.1: 术语提取服务
**文件**: `src/services/terminology/extraction_service.py`

**内容**:
```python
class TermExtractionService:
    def __init__(self, llm_provider: LLMProvider)
    def extract_all(self, project_id: str, sections: List[Section]) -> List[TermCandidate]
    def _build_candidate(self, term_data: dict, sections: List[Section]) -> TermCandidate
    def _build_outline(self, sections: List[Section]) -> str
```

**验收标准**:
- [ ] 一次性提取所有候选
- [ ] 使用 TermMatcher 统计出现次数
- [ ] 单元测试覆盖

**预计时间**: 2 天

---

#### Task 3.2: 冲突检测器
**文件**: `src/services/terminology/conflict_detector.py`

**内容**:
```python
class TermConflictDetector:
    @staticmethod
    def detect(
        candidates: List[TermCandidate],
        existing_terms: List[Term],
        existing_metadata: List[TermMetadata]
    ) -> tuple[List[TermCandidate], List[TermConflict]]
```

**验收标准**:
- [ ] 正确检测译法冲突
- [ ] 正确检测上下文冲突
- [ ] 单元测试覆盖

**预计时间**: 1 天

---

#### Task 3.3: 术语确认服务
**文件**: `src/services/terminology/confirmation_service.py`

**内容**:
```python
class TermConfirmationService:
    def __init__(self, storage: GlossaryStorage, extraction_service: TermExtractionService, conflict_detector: TermConflictDetector)
    def prepare(self, project_id: str, sections: List[Section]) -> ConfirmationPackage
    def apply(self, submission: ConfirmationSubmission) -> tuple[List[Term], List[str]]
    def _validate_submission(self, package: ConfirmationPackage, submission: ConfirmationSubmission)
    def _create_term_from_candidate(self, candidate: TermCandidate, project_id: str) -> Term
    def _create_term_from_decision(self, decision: TermDecision, candidate: TermCandidate, project_id: str) -> Term
```

**验收标准**:
- [ ] 确认包生成正确
- [ ] 决策应用正确
- [ ] 持久化正确
- [ ] 审计日志完整
- [ ] 单元测试覆盖

**预计时间**: 3 天

---

#### Task 3.4: API 路由
**文件**: `src/api/routers/terminology_confirmation.py`

**内容**:
```python
@router.post("/projects/{project_id}/terminology/prepare-confirmation")
async def prepare_confirmation(project_id: str, service: TermConfirmationService = Depends()) -> ConfirmationPackage

@router.post("/projects/{project_id}/terminology/submit-confirmation")
async def submit_confirmation(project_id: str, submission: ConfirmationSubmission, service: TermConfirmationService = Depends())
```

**验收标准**:
- [ ] API 正确实现
- [ ] 错误处理完整
- [ ] API 测试通过

**预计时间**: 1 天

---

#### Task 3.5: 前端确认页面
**文件**: `web/frontend/src/features/terminology/ConfirmationPage.tsx`

**内容**:
- 新术语列表（accept/custom/skip）
- 冲突术语列表（use_existing/use_new/custom/skip）
- 必须确认项标记
- 提交验证

**验收标准**:
- [ ] UI 完整
- [ ] 交互流畅
- [ ] 验证正确
- [ ] 手动测试通过

**预计时间**: 3 天

---

### Milestone 3 验收

- [ ] 确认流程实现完整
- [ ] API 测试通过
- [ ] 前端测试通过
- [ ] 端到端测试通过
- [ ] 代码审查通过

---

## Milestone 4: 会话管理 (Week 4-5)

### 目标
实现翻译会话管理，支持断点续传和术语快照。

### 任务清单

#### Task 4.1: 会话服务
**文件**: `src/services/terminology/session_service.py`

**内容**:
```python
class TranslationSessionService:
    def __init__(self, storage: GlossaryStorage, session_storage: SessionStorage, matcher_factory: TermMatcherFactory)
    def create_session(self, project_id: str, active_terms: List[Term], excluded_terms: List[str], total_sections: int) -> TranslationSession
    def start_translation(self, session_id: str, section_id: str)
    def complete_section(self, session_id: str, section_id: str, term_usage: dict[str, int])
    def pause_session(self, session_id: str)
    def prepare_resume(self, session_id: str) -> ResumeOptions
    def resume_session(self, session_id: str, use_snapshot: bool) -> TranslationSession
    def get_active_matcher(self, session_id: str) -> TermMatcher
    def get_session_summary(self, session_id: str) -> dict
```

**验收标准**:
- [ ] 会话创建正确
- [ ] 进度追踪正确
- [ ] 断点续传正确
- [ ] 术语变更检测正确
- [ ] 单元测试覆盖

**预计时间**: 3 天

---

#### Task 4.2: API 路由
**文件**: `src/api/routers/translation_session.py`

**内容**:
```python
@router.post("/sessions/{session_id}/pause")
@router.get("/sessions/{session_id}/resume-options")
@router.post("/sessions/{session_id}/resume")
@router.get("/sessions/{session_id}/summary")
```

**验收标准**:
- [ ] API 正确实现
- [ ] API 测试通过

**预计时间**: 1 天

---

#### Task 4.3: 前端断点续传
**文件**: `web/frontend/src/features/translation/ResumeDialog.tsx`

**内容**:
- 术语变更对话框
- 使用快照 / 重新生成选择
- 变更详情展示

**验收标准**:
- [ ] UI 完整
- [ ] 交互流畅
- [ ] 手动测试通过

**预计时间**: 2 天

---

### Milestone 4 验收

- [ ] 会话管理实现完整
- [ ] 断点续传正确
- [ ] API 测试通过
- [ ] 前端测试通过
- [ ] 代码审查通过

---

## Milestone 5: 翻译集成 (Week 5-6)

### 目标
将新术语系统集成到翻译流程中。

### 任务清单

#### Task 5.1: Prompt 注入服务
**文件**: `src/services/terminology/injection_service.py`

**内容**:
```python
class TermInjectionService:
    def build_prompt_block(self, text: str, matcher: TermMatcher, term_usage_tracker: Optional[dict[str, int]] = None) -> str
    def _format_term_constraint(self, term: Term, term_usage_tracker: Optional[dict[str, int]]) -> str
    def _get_strategy_description(self, term: Term, is_first_occurrence: bool) -> str
    def _is_first_occurrence(self, term: Term, term_usage_tracker: Optional[dict[str, int]]) -> bool
```

**验收标准**:
- [ ] Prompt 格式正确
- [ ] 策略描述正确
- [ ] 首次出现判断正确
- [ ] 单元测试覆盖

**预计时间**: 2 天

---

#### Task 5.2: 翻译流程集成
**文件**: `src/services/batch_translation_service.py`

**修改**:
```python
# 替换旧的术语加载逻辑
# 使用 TranslationSessionService.get_active_matcher()
# 使用 TermInjectionService.build_prompt_block()
```

**验收标准**:
- [ ] 翻译流程正确
- [ ] 术语注入正确
- [ ] 使用追踪正确
- [ ] 集成测试通过

**预计时间**: 3 天

---

#### Task 5.3: 翻译后验证服务
**文件**: `src/services/terminology/validation_service.py`

**内容**:
```python
class TermValidationService:
    def __init__(self, matcher_factory: TermMatcherFactory)
    def validate_session(self, session: TranslationSession, translations: dict[str, List[str]]) -> ValidationReport
    def _check_term_usage(self, term: Term, translations: dict[str, List[str]], matcher: TermMatcher) -> TermUsageReport
```

**验收标准**:
- [ ] 验证逻辑正确
- [ ] 报告生成正确
- [ ] 单元测试覆盖

**预计时间**: 2 天

---

### Milestone 5 验收

- [ ] 翻译集成完整
- [ ] 端到端测试通过
- [ ] 性能测试通过
- [ ] 代码审查通过

---

## Milestone 6: 数据迁移 (Week 6-7)

### 目标
将旧系统数据迁移到新系统。

### 任务清单

#### Task 6.1: 迁移脚本
**文件**: `scripts/migrate_terminology.py`

**内容**:
```python
class DataMigrationService:
    def migrate_all(self) -> MigrationReport
    def _migrate_global_terms(self) -> int
    def _migrate_all_projects(self) -> int
    def _migrate_project_terms(self, project_id: str) -> int
```

**验收标准**:
- [ ] 迁移逻辑正确
- [ ] 覆盖关系推断正确
- [ ] 迁移报告完整
- [ ] 回滚机制完整

**预计时间**: 3 天

---

#### Task 6.2: 迁移验证
**文件**: `scripts/validate_migration.py`

**验证项**:
- 术语数量一致
- 译法一致
- 覆盖关系正确
- 元数据完整

**验收标准**:
- [ ] 验证脚本完整
- [ ] 所有验证通过

**预计时间**: 2 天

---

#### Task 6.3: 数据备份与恢复
**文件**: `scripts/backup_terminology.py`, `scripts/restore_terminology.py`

**验收标准**:
- [ ] 备份脚本完整
- [ ] 恢复脚本完整
- [ ] 测试通过

**预计时间**: 1 天

---

### Milestone 6 验收

- [ ] 迁移脚本完整
- [ ] 迁移验证通过
- [ ] 备份恢复测试通过
- [ ] 代码审查通过

---

## Milestone 7: 上线切换 (Week 7-8)

### 目标
完成新旧系统切换，上线新术语系统。

### 任务清单

#### Task 7.1: 兼容层
**文件**: `src/api/routers/glossary_compat.py`

**内容**:
- 保留旧 API 端点
- 转发到新系统
- 数据格式转换

**验收标准**:
- [ ] 旧 API 仍可用
- [ ] 数据格式兼容
- [ ] 测试通过

**预计时间**: 2 天

---

#### Task 7.2: 灰度发布
**策略**:
1. 先在测试环境验证
2. 选择 1-2 个项目试点
3. 监控错误和性能
4. 逐步扩大范围
5. 全量切换

**验收标准**:
- [ ] 试点项目成功
- [ ] 无严重错误
- [ ] 性能达标

**预计时间**: 3 天

---

#### Task 7.3: 监控与告警
**内容**:
- 术语匹配准确率监控
- 性能监控
- 错误告警

**验收标准**:
- [ ] 监控完整
- [ ] 告警及时

**预计时间**: 1 天

---

#### Task 7.4: 文档更新
**文件**:
- `docs/术语库系统手册.md` — 更新为新系统
- `docs/API文档.md` — 更新 API 文档
- `README.md` — 更新使用说明

**验收标准**:
- [ ] 文档完整
- [ ] 示例正确

**预计时间**: 2 天

---

### Milestone 7 验收

- [ ] 灰度发布成功
- [ ] 全量切换完成
- [ ] 监控正常
- [ ] 文档更新完成

---

## 总体时间表

| Milestone | 任务 | 预计时间 | 累计时间 |
|-----------|------|----------|----------|
| M1 | 存储层 | 6.5 天 | 6.5 天 |
| M2 | 匹配引擎 | 8 天 | 14.5 天 |
| M3 | 确认流程 | 10 天 | 24.5 天 |
| M4 | 会话管理 | 6 天 | 30.5 天 |
| M5 | 翻译集成 | 7 天 | 37.5 天 |
| M6 | 数据迁移 | 6 天 | 43.5 天 |
| M7 | 上线切换 | 8 天 | 51.5 天 |

**总计**: ~52 天（约 7-8 周）

---

## 风险管理

### 高风险项

1. **匹配引擎准确率**
   - 风险：准确率达不到 95%
   - 缓解：充分的回归测试，逐步调优

2. **数据迁移**
   - 风险：迁移失败导致数据丢失
   - 缓解：完整备份，分阶段迁移，充分验证

3. **性能问题**
   - 风险：匹配引擎性能不足
   - 缓解：预编译、缓存、性能测试

### 中风险项

1. **前端适配**
   - 风险：前端改动较大，可能引入 bug
   - 缓解：充分测试，灰度发布

2. **API 兼容性**
   - 风险：旧 API 不兼容
   - 缓解：保留兼容层，逐步迁移

---

## 资源需求

### 人力
- 后端开发：1 人全职
- 前端开发：1 人 50% 时间
- 测试：1 人 30% 时间
- Code Review：1 人 20% 时间

### 环境
- 测试环境：1 套
- 灰度环境：1 套
- 生产环境：1 套

---

## 验收标准总览

### 功能完整性
- [ ] 术语提取一次性完成
- [ ] 术语确认阻塞翻译
- [ ] 所有冲突前置解决
- [ ] 会话快照不可变
- [ ] 断点续传检测变更
- [ ] 审计日志完整

### 性能指标
- [ ] 匹配准确率 > 95%
- [ ] 匹配时间 < 10ms / 1000 字
- [ ] 预编译时间 < 100ms / 100 术语
- [ ] 内存占用 < 50MB / 1000 术语

### 质量指标
- [ ] 单元测试覆盖率 > 90%
- [ ] 集成测试覆盖率 > 80%
- [ ] 代码审查通过率 100%
- [ ] 无严重 bug

---

## 后续优化

1. **术语推荐** — 基于使用统计自动推荐
2. **术语分组** — 支持按领域分组
3. **术语版本** — 支持版本管理和回滚
4. **多用户协作** — 支持多用户编辑
5. **批量导入导出** — 支持 CSV/Excel

---

## 总结

本实施计划将术语系统重构分为 7 个里程碑，每个里程碑可独立验证。预计总时间 7-8 周，采用分阶段实施、向后兼容、测试先行的策略，确保平稳过渡。

**关键成功因素**：
1. 充分的测试覆盖
2. 分阶段验证
3. 完整的数据备份
4. 灰度发布策略
5. 及时的监控告警
