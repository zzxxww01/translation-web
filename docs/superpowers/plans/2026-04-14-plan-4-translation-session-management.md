# Plan 4: 翻译会话管理

## 概述

实现翻译会话的完整生命周期管理，包括会话创建、进度追踪、断点续传、术语注入和翻译后验证。

**目标**：
- 实现会话管理服务（TranslationSessionService）
- 实现术语注入服务（TermInjectionService）
- 实现翻译后验证服务（TermValidationService）
- 支持断点续传和术语变更检测
- 集成到现有翻译流程

**预计时间**：2-2.5 周

---

## 任务清单

### Task 4.1: 实现会话管理服务

**目标**：管理翻译会话的生命周期

**文件**：`src/services/translation_session_service.py`

**数据模型**：

```python
from enum import Enum
from dataclasses import dataclass

class SessionStatus(str, Enum):
    """会话状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"

@dataclass
class TranslationSession:
    """翻译会话"""
    session_id: str
    project_id: str
    
    # 术语快照
    active_terms: list[Term]
    excluded_terms: list[str]  # 被 skip 的术语 original
    snapshot_version: int
    
    # 进度追踪
    total_sections: int
    completed_sections: list[str]
    current_section: Optional[str]
    
    # 术语使用统计
    term_usage: dict[str, int]  # term_id -> count
    
    # 状态
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    
    # 断点续传
    can_resume: bool
    resume_options: Optional['ResumeOptions'] = None

@dataclass
class ResumeOptions:
    """续传选项"""
    has_term_changes: bool
    term_changes: dict  # {"added": [...], "modified": [...], "deleted": [...]}
    use_snapshot: bool  # True=使用原快照, False=重新生成
    snapshot_version: int

class TranslationSessionService:
    """翻译会话管理服务"""
    
    def __init__(self, storage: GlossaryStorage):
        self.storage = storage
    
    def create_session(self, project_id: str, excluded_terms: list[str] = None) -> TranslationSession:
        """创建翻译会话"""
        
        # 1. 加载激活术语
        active_terms = self.storage.get_active_terms(project_id)
        
        # 2. 过滤被排除的术语
        if excluded_terms:
            active_terms = [t for t in active_terms if t.original not in excluded_terms]
        
        # 3. 加载项目元数据
        project = self._load_project(project_id)
        
        # 4. 创建会话
        session = TranslationSession(
            session_id=str(uuid.uuid4()),
            project_id=project_id,
            active_terms=active_terms,
            excluded_terms=excluded_terms or [],
            snapshot_version=1,
            total_sections=len(project['sections']),
            completed_sections=[],
            current_section=None,
            term_usage={},
            status=SessionStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            can_resume=False
        )
        
        # 5. 保存会话快照
        self._save_session(session)
        
        return session
    
    def start_session(self, session_id: str) -> TranslationSession:
        """开始会话"""
        session = self._load_session(session_id)
        session.status = SessionStatus.IN_PROGRESS
        session.updated_at = datetime.utcnow()
        self._save_session(session)
        return session
    
    def pause_session(self, session_id: str) -> TranslationSession:
        """暂停会话"""
        session = self._load_session(session_id)
        session.status = SessionStatus.PAUSED
        session.can_resume = True
        session.updated_at = datetime.utcnow()
        self._save_session(session)
        return session
    
    def complete_section(self, session_id: str, section_id: str, term_usage: dict[str, int]):
        """完成一个章节"""
        session = self._load_session(session_id)
        
        # 更新进度
        if section_id not in session.completed_sections:
            session.completed_sections.append(section_id)
        
        # 更新术语使用统计
        for term_id, count in term_usage.items():
            session.term_usage[term_id] = session.term_usage.get(term_id, 0) + count
        
        # 更新状态
        if len(session.completed_sections) == session.total_sections:
            session.status = SessionStatus.COMPLETED
        
        session.updated_at = datetime.utcnow()
        self._save_session(session)
    
    def prepare_resume(self, session_id: str) -> ResumeOptions:
        """准备续传（检测术语变更）"""
        session = self._load_session(session_id)
        
        if not session.can_resume:
            raise ValueError("Session cannot be resumed")
        
        # 加载当前激活术语
        current_terms = self.storage.get_active_terms(session.project_id)
        
        # 检测变更
        changes = self._detect_term_changes(session.active_terms, current_terms)
        
        # 构建续传选项
        options = ResumeOptions(
            has_term_changes=bool(changes["added"] or changes["modified"] or changes["deleted"]),
            term_changes=changes,
            use_snapshot=True,  # 默认使用快照
            snapshot_version=session.snapshot_version
        )
        
        session.resume_options = options
        self._save_session(session)
        
        return options
    
    def resume_session(self, session_id: str, use_snapshot: bool = True) -> TranslationSession:
        """续传会话"""
        session = self._load_session(session_id)
        
        if not session.can_resume:
            raise ValueError("Session cannot be resumed")
        
        if not use_snapshot:
            # 重新生成术语快照
            active_terms = self.storage.get_active_terms(session.project_id)
            if session.excluded_terms:
                active_terms = [t for t in active_terms if t.original not in session.excluded_terms]
            
            session.active_terms = active_terms
            session.snapshot_version += 1
        
        session.status = SessionStatus.IN_PROGRESS
        session.can_resume = False
        session.resume_options = None
        session.updated_at = datetime.utcnow()
        self._save_session(session)
        
        return session
    
    def get_active_matcher(self, session_id: str) -> TermMatcher:
        """获取会话的术语匹配器"""
        session = self._load_session(session_id)
        return TermMatcher(session.active_terms)
    
    def _detect_term_changes(self, old_terms: list[Term], new_terms: list[Term]) -> dict:
        """检测术语变更"""
        old_dict = {t.id: t for t in old_terms}
        new_dict = {t.id: t for t in new_terms}
        
        added = [t for t in new_terms if t.id not in old_dict]
        deleted = [t for t in old_terms if t.id not in new_dict]
        modified = []
        
        for term_id in old_dict.keys() & new_dict.keys():
            old = old_dict[term_id]
            new = new_dict[term_id]
            if old.translation != new.translation or old.strategy != new.strategy:
                modified.append({
                    "id": term_id,
                    "original": old.original,
                    "old_translation": old.translation,
                    "new_translation": new.translation
                })
        
        return {
            "added": [{"id": t.id, "original": t.original, "translation": t.translation} for t in added],
            "modified": modified,
            "deleted": [{"id": t.id, "original": t.original} for t in deleted]
        }
    
    def _save_session(self, session: TranslationSession):
        """保存会话快照"""
        path = Path(f"projects/{session.project_id}/glossary/sessions/{session.session_id}.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = asdict(session)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))
    
    def _load_session(self, session_id: str) -> TranslationSession:
        """加载会话快照"""
        # 需要先找到项目ID（可以从session_id中编码，或维护索引）
        pass
```

**验收标准**：
- [ ] 会话创建正确生成快照
- [ ] 进度追踪准确
- [ ] 术语变更检测正确
- [ ] 断点续传逻辑正确
- [ ] 单元测试覆盖率 > 90%

---

### Task 4.2: 实现术语注入服务

**目标**：构建翻译 prompt 的术语约束块

**文件**：`src/services/term_injection_service.py`

**核心功能**：

```python
class TermInjectionService:
    """术语注入服务"""
    
    def __init__(self, matcher: TermMatcher):
        self.matcher = matcher
    
    def build_prompt_block(self, text: str, first_occurrence_tracker: dict = None) -> str:
        """构建术语约束块"""
        
        # 1. 匹配当前段落的术语
        matches = self.matcher.match_all(text)
        
        if not matches:
            return ""
        
        # 2. 去重（同一术语只列一次）
        unique_terms = {}
        for match in matches:
            if match.term.id not in unique_terms:
                unique_terms[match.term.id] = match.term
        
        # 3. 按策略分组
        groups = {
            TranslationStrategy.TRANSLATE: [],
            TranslationStrategy.PRESERVE: [],
            TranslationStrategy.FIRST_ANNOTATE: [],
            TranslationStrategy.PRESERVE_ANNOTATE: []
        }
        
        for term in unique_terms.values():
            groups[term.strategy].append(term)
        
        # 4. 构建约束块
        lines = ["## 术语约束\n"]
        
        # TRANSLATE
        if groups[TranslationStrategy.TRANSLATE]:
            lines.append("**必须翻译的术语**：")
            for term in groups[TranslationStrategy.TRANSLATE]:
                note = f"（{term.note}）" if term.note else ""
                lines.append(f"- {term.original} → {term.translation}{note}")
            lines.append("")
        
        # PRESERVE
        if groups[TranslationStrategy.PRESERVE]:
            lines.append("**必须保留原文的术语**：")
            for term in groups[TranslationStrategy.PRESERVE]:
                note = f"（{term.note}）" if term.note else ""
                lines.append(f"- {term.original}{note}")
            lines.append("")
        
        # FIRST_ANNOTATE
        if groups[TranslationStrategy.FIRST_ANNOTATE]:
            lines.append("**首次出现需注释的术语**：")
            for term in groups[TranslationStrategy.FIRST_ANNOTATE]:
                # 检查是否首次出现
                is_first = self._is_first_occurrence(term, first_occurrence_tracker)
                if is_first:
                    note = f"（{term.note}）" if term.note else ""
                    lines.append(f"- {term.original} → {term.translation}（首次出现请注释）{note}")
                else:
                    lines.append(f"- {term.original} → {term.translation}")
            lines.append("")
        
        # PRESERVE_ANNOTATE
        if groups[TranslationStrategy.PRESERVE_ANNOTATE]:
            lines.append("**保留原文并注释的术语**：")
            for term in groups[TranslationStrategy.PRESERVE_ANNOTATE]:
                note = f"（{term.note}）" if term.note else ""
                lines.append(f"- {term.original}（注释：{term.translation}）{note}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _is_first_occurrence(self, term: Term, tracker: dict) -> bool:
        """检查是否首次出现"""
        if tracker is None:
            return True
        
        if term.id not in tracker:
            tracker[term.id] = True
            return True
        
        return False
```

**验收标准**：
- [ ] 正确构建所有策略的约束块
- [ ] 首次出现追踪正确
- [ ] 只注入当前段落命中的术语
- [ ] 单元测试覆盖率 > 90%

---

### Task 4.3: 实现翻译后验证服务

**目标**：验证翻译结果的术语一致性

**文件**：`src/services/term_validation_service.py`

**核心功能**：

```python
@dataclass
class ValidationIssue:
    """验证问题"""
    term: Term
    issue_type: Literal["missing", "incorrect", "inconsistent"]
    expected: str
    actual: Optional[str]
    location: str  # 章节ID
    context: str

@dataclass
class ValidationReport:
    """验证报告"""
    session_id: str
    total_terms: int
    validated_terms: int
    issues: list[ValidationIssue]
    is_valid: bool

class TermValidationService:
    """术语验证服务"""
    
    def __init__(self, matcher: TermMatcher):
        self.matcher = matcher
    
    def validate_translation(self, 
                            source_text: str, 
                            translated_text: str,
                            section_id: str) -> list[ValidationIssue]:
        """验证单个章节的翻译"""
        issues = []
        
        # 1. 匹配源文本中的术语
        source_matches = self.matcher.match_all(source_text)
        
        # 2. 检查每个术语
        for match in source_matches:
            term = match.term
            
            if term.strategy == TranslationStrategy.TRANSLATE:
                # 检查翻译是否出现
                if term.translation not in translated_text:
                    issues.append(ValidationIssue(
                        term=term,
                        issue_type="missing",
                        expected=term.translation,
                        actual=None,
                        location=section_id,
                        context=match.context
                    ))
            
            elif term.strategy == TranslationStrategy.PRESERVE:
                # 检查原文是否保留
                if term.original not in translated_text:
                    issues.append(ValidationIssue(
                        term=term,
                        issue_type="missing",
                        expected=term.original,
                        actual=None,
                        location=section_id,
                        context=match.context
                    ))
        
        return issues
    
    def validate_session(self, session_id: str) -> ValidationReport:
        """验证整个会话的翻译"""
        session = self._load_session(session_id)
        
        all_issues = []
        validated_count = 0
        
        for section_id in session.completed_sections:
            # 加载源文本和翻译
            source = self._load_source(session.project_id, section_id)
            translation = self._load_translation(session.project_id, section_id)
            
            # 验证
            issues = self.validate_translation(source, translation, section_id)
            all_issues.extend(issues)
            
            # 统计
            source_matches = self.matcher.match_all(source)
            validated_count += len(set(m.term.id for m in source_matches))
        
        return ValidationReport(
            session_id=session_id,
            total_terms=len(session.active_terms),
            validated_terms=validated_count,
            issues=all_issues,
            is_valid=len(all_issues) == 0
        )
```

**验收标准**：
- [ ] 正确检测缺失术语
- [ ] 正确检测错误翻译
- [ ] 生成详细的验证报告
- [ ] 单元测试覆盖率 > 85%

---

### Task 4.4: 集成到翻译流程

**目标**：将术语系统集成到现有的四步翻译法

**文件**：`src/agents/four_step_translator.py`（修改）

**集成点**：

```python
class FourStepTranslator:
    """四步翻译法（集成术语系统）"""
    
    def __init__(self, ..., session_service: TranslationSessionService):
        # ...
        self.session_service = session_service
        self.injection_service = None  # 延迟初始化
        self.first_occurrence_tracker = {}
    
    async def translate_section(self, section_id: str, session_id: str):
        """翻译单个章节"""
        
        # 1. 加载会话和匹配器
        session = self.session_service._load_session(session_id)
        matcher = self.session_service.get_active_matcher(session_id)
        self.injection_service = TermInjectionService(matcher)
        
        # 2. 加载源文本
        source_text = self._load_source(section_id)
        
        # 3. 构建术语约束块
        term_block = self.injection_service.build_prompt_block(
            source_text, 
            self.first_occurrence_tracker
        )
        
        # 4. 执行四步翻译（注入术语约束）
        translation = await self._four_step_translate(source_text, term_block)
        
        # 5. 统计术语使用
        term_usage = self._count_term_usage(source_text, matcher)
        
        # 6. 更新会话进度
        self.session_service.complete_section(session_id, section_id, term_usage)
        
        return translation
    
    def _four_step_translate(self, source: str, term_block: str) -> str:
        """四步翻译（注入术语约束）"""
        
        # Step 1: Initial translation
        prompt = f"""
{term_block}

请翻译以下内容：
{source}
"""
        # ... 执行翻译 ...
```

**验收标准**：
- [ ] 术语约束正确注入到 prompt
- [ ] 翻译结果符合术语约束
- [ ] 会话进度正确更新
- [ ] 集成测试通过

---

### Task 4.5: 编写端到端测试

**目标**：验证完整的翻译会话流程

**文件**：`tests/e2e/test_translation_with_terminology.py`

**测试场景**：

```python
class TestTranslationWithTerminology:
    """术语系统端到端测试"""
    
    async def test_full_translation_workflow(self):
        """测试完整翻译流程"""
        
        # 1. 准备项目和术语
        project_id = "test-project"
        # ... 创建测试项目 ...
        # ... 添加术语 ...
        
        # 2. 创建会话
        session_service = TranslationSessionService(...)
        session = session_service.create_session(project_id)
        session = session_service.start_session(session.session_id)
        
        # 3. 翻译所有章节
        translator = FourStepTranslator(..., session_service)
        for section_id in ["section-1", "section-2"]:
            await translator.translate_section(section_id, session.session_id)
        
        # 4. 验证翻译
        validation_service = TermValidationService(...)
        report = validation_service.validate_session(session.session_id)
        
        assert report.is_valid
        assert len(report.issues) == 0
    
    async def test_resume_after_pause(self):
        """测试断点续传"""
        
        # 1. 创建会话并翻译一半
        session = session_service.create_session(project_id)
        session = session_service.start_session(session.session_id)
        await translator.translate_section("section-1", session.session_id)
        
        # 2. 暂停
        session = session_service.pause_session(session.session_id)
        
        # 3. 修改术语
        # ... 添加新术语 ...
        
        # 4. 准备续传
        options = session_service.prepare_resume(session.session_id)
        assert options.has_term_changes
        
        # 5. 续传（使用快照）
        session = session_service.resume_session(session.session_id, use_snapshot=True)
        await translator.translate_section("section-2", session.session_id)
        
        # 6. 验证一致性
        report = validation_service.validate_session(session.session_id)
        assert report.is_valid
```

**验收标准**：
- [ ] 完整流程测试通过
- [ ] 断点续传测试通过
- [ ] 术语一致性验证通过

---

## 交付物

1. **代码**：
   - `src/services/translation_session_service.py`
   - `src/services/term_injection_service.py`
   - `src/services/term_validation_service.py`
   - `src/agents/four_step_translator.py`（修改）

2. **测试**：
   - `tests/unit/services/test_translation_session.py`
   - `tests/unit/services/test_term_injection.py`
   - `tests/unit/services/test_term_validation.py`
   - `tests/e2e/test_translation_with_terminology.py`

3. **文档**：
   - 更新 `docs/术语库系统手册.md` 的"翻译会话"章节
   - 添加断点续传使用指南

---

## 验收标准

- [ ] 所有任务完成
- [ ] 单元测试覆盖率 > 85%
- [ ] 端到端测试通过
- [ ] 术语约束正确注入
- [ ] 断点续传功能正常
- [ ] 代码通过类型检查和格式检查

---

## 依赖和风险

**依赖**：
- Plan 1（GlossaryStorage）
- Plan 2（TermMatcher）
- Plan 3（术语确认流程）

**风险**：
1. **会话快照过大**
   - 缓解：只保存必要字段，术语列表使用引用

2. **首次出现追踪不准确**
   - 缓解：在会话级别维护全局追踪器

3. **验证服务性能问题**
   - 缓解：异步验证、批量处理

---

## 后续计划

完成 Plan 4 后，可以开始：
- **Plan 5**：数据迁移和清理（迁移旧系统数据）
