# Plan 3: 术语确认流程

## 概述

实现术语提取、冲突检测、用户确认的完整工作流，确保翻译前所有术语问题都已解决。

**目标**：
- 实现术语提取服务（TermExtractionService）
- 实现冲突检测器（TermConflictDetector）
- 实现确认服务（TermConfirmationService）
- 提供交互式 CLI 确认界面
- 支持批量确认和跳过

**预计时间**：1.5-2 周

---

## 任务清单

### Task 3.1: 实现术语提取服务

**目标**：从源文档中提取候选术语

**文件**：`src/services/term_extraction_service.py`

**核心功能**：

```python
from dataclasses import dataclass

@dataclass
class TermCandidate:
    """候选术语"""
    original: str
    suggested_translation: str
    confidence: float  # 0.0-1.0
    context: str  # 首次出现的上下文
    occurrence_count: int
    hit_title: bool  # 是否出现在标题中
    sections: list[str]  # 出现在哪些章节

class TermExtractionService:
    """术语提取服务"""
    
    def __init__(self, llm_provider: BaseLLMProvider, storage: GlossaryStorage):
        self.llm = llm_provider
        self.storage = storage
    
    async def extract_all(self, project_id: str) -> list[TermCandidate]:
        """提取项目中的所有候选术语（Phase 0）"""
        
        # 1. 加载项目元数据
        project = self._load_project(project_id)
        
        # 2. 收集所有文本
        all_text = self._collect_text(project)
        
        # 3. 调用 LLM 提取术语
        prompt = self._build_extraction_prompt(all_text, project)
        response = await self.llm.generate(prompt)
        raw_candidates = self._parse_extraction_response(response)
        
        # 4. 使用 TermMatcher 统计出现次数
        existing_terms = self.storage.get_active_terms(project_id)
        matcher = TermMatcher(existing_terms)
        
        candidates = []
        for raw in raw_candidates:
            # 统计出现次数
            count = matcher.count_occurrences(
                Term(original=raw["original"], translation=""), 
                all_text
            )
            
            # 检查是否在标题中
            hit_title = self._check_title_hit(raw["original"], project)
            
            # 找出出现的章节
            sections = self._find_sections(raw["original"], project)
            
            candidates.append(TermCandidate(
                original=raw["original"],
                suggested_translation=raw["translation"],
                confidence=raw.get("confidence", 0.8),
                context=raw["context"],
                occurrence_count=count,
                hit_title=hit_title,
                sections=sections
            ))
        
        # 5. 按重要性排序（标题 > 出现次数 > 置信度）
        candidates.sort(key=lambda c: (
            -int(c.hit_title),
            -c.occurrence_count,
            -c.confidence
        ))
        
        # 6. 保存提取结果
        self._save_extraction_result(project_id, candidates)
        
        return candidates
    
    def _build_extraction_prompt(self, text: str, project: dict) -> str:
        """构建提取 prompt"""
        return f"""
你是一个专业的术语提取专家。请从以下技术文档中提取所有重要的专业术语。

文档主题：{project['title']}
文档领域：半导体、芯片、存储技术

要求：
1. 提取所有专业术语（技术名词、产品名、公司名、缩写）
2. 为每个术语提供准确的中文翻译
3. 提供术语首次出现的上下文（前后各 20 字符）
4. 评估翻译置信度（0.0-1.0）

输出格式（JSON）：
[
  {{
    "original": "HBM",
    "translation": "高带宽内存",
    "confidence": 0.95,
    "context": "...using HBM memory for..."
  }},
  ...
]

文档内容：
{text[:10000]}  # 限制长度
"""
    
    def _collect_text(self, project: dict) -> str:
        """收集项目所有文本"""
        texts = []
        
        # 标题
        texts.append(f"# {project['title']}")
        
        # 各章节
        for section in project['sections']:
            source_path = section['source_path']
            if source_path.exists():
                texts.append(source_path.read_text(encoding='utf-8'))
        
        return "\n\n".join(texts)
    
    def _check_title_hit(self, term: str, project: dict) -> bool:
        """检查术语是否在标题中"""
        title = project['title'].lower()
        return term.lower() in title
    
    def _find_sections(self, term: str, project: dict) -> list[str]:
        """找出术语出现的章节"""
        sections = []
        for section in project['sections']:
            source_path = section['source_path']
            if source_path.exists():
                text = source_path.read_text(encoding='utf-8')
                if term.lower() in text.lower():
                    sections.append(section['id'])
        return sections
    
    def _save_extraction_result(self, project_id: str, candidates: list[TermCandidate]):
        """保存提取结果"""
        output_path = Path(f"projects/{project_id}/artifacts/term-extraction/latest.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [asdict(c) for c in candidates]
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
```

**验收标准**：
- [ ] 能从真实项目中提取术语
- [ ] 出现次数统计准确
- [ ] 标题命中检测正确
- [ ] 提取结果正确保存
- [ ] 单元测试覆盖率 > 85%

---

### Task 3.2: 实现冲突检测器

**目标**：检测候选术语与已有术语的冲突

**文件**：`src/services/term_conflict_detector.py`

**冲突类型**：

```python
from enum import Enum

class ConflictType(str, Enum):
    """冲突类型"""
    TRANSLATION_MISMATCH = "translation_mismatch"  # 翻译不一致
    CONTEXT_MISMATCH = "context_mismatch"          # 上下文不匹配

@dataclass
class TermConflict:
    """术语冲突"""
    original: str
    existing_term_id: str
    existing_translation: str
    existing_scope: Literal["global", "project"]
    suggested_translation: str
    context: str
    conflict_type: ConflictType

class TermConflictDetector:
    """术语冲突检测器"""
    
    def __init__(self, storage: GlossaryStorage):
        self.storage = storage
    
    def detect(self, candidates: list[TermCandidate], project_id: str) -> list[TermConflict]:
        """检测冲突"""
        conflicts = []
        
        # 加载已有术语
        global_terms = self.storage.load_terms("global")
        project_terms = self.storage.load_terms("project", project_id)
        
        # 构建查找表（original -> Term）
        existing = {}
        for term in global_terms:
            if term.status == "active":
                existing[term.original.lower()] = (term, "global")
        for term in project_terms:
            if term.status == "active":
                existing[term.original.lower()] = (term, "project")  # 项目覆盖全局
        
        # 检测每个候选
        for candidate in candidates:
            key = candidate.original.lower()
            if key in existing:
                term, scope = existing[key]
                
                # 检查翻译是否一致
                if term.translation != candidate.suggested_translation:
                    conflicts.append(TermConflict(
                        original=candidate.original,
                        existing_term_id=term.id,
                        existing_translation=term.translation,
                        existing_scope=scope,
                        suggested_translation=candidate.suggested_translation,
                        context=candidate.context,
                        conflict_type=ConflictType.TRANSLATION_MISMATCH
                    ))
        
        return conflicts
```

**验收标准**：
- [ ] 正确检测翻译不一致
- [ ] 正确处理全局/项目优先级
- [ ] 单元测试覆盖率 > 90%

---

### Task 3.3: 实现确认服务

**目标**：管理用户确认流程

**文件**：`src/services/term_confirmation_service.py`

**核心功能**：

```python
from enum import Enum

class ConfirmationAction(str, Enum):
    """确认动作"""
    ACCEPT = "accept"              # 接受建议
    MODIFY = "modify"              # 修改翻译
    SKIP = "skip"                  # 跳过（本次不使用）
    USE_EXISTING = "use_existing"  # 使用已有术语
    REJECT = "reject"              # 拒绝（不是术语）

@dataclass
class ConfirmationDecision:
    """确认决策"""
    original: str
    action: ConfirmationAction
    final_translation: Optional[str] = None
    strategy: TranslationStrategy = TranslationStrategy.TRANSLATE
    note: Optional[str] = None
    scope: Literal["global", "project"] = "project"

@dataclass
class ConfirmationPackage:
    """确认包"""
    package_id: str
    project_id: str
    candidates: list[TermCandidate]
    conflicts: list[TermConflict]
    created_at: datetime
    expires_at: datetime  # 24 小时后过期

class TermConfirmationService:
    """术语确认服务"""
    
    def __init__(self, storage: GlossaryStorage, detector: TermConflictDetector):
        self.storage = storage
        self.detector = detector
    
    def prepare(self, candidates: list[TermCandidate], project_id: str) -> ConfirmationPackage:
        """准备确认包"""
        
        # 检测冲突
        conflicts = self.detector.detect(candidates, project_id)
        
        # 创建确认包
        package = ConfirmationPackage(
            package_id=str(uuid.uuid4()),
            project_id=project_id,
            candidates=candidates,
            conflicts=conflicts,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        # 保存确认包
        self._save_package(package)
        
        return package
    
    def apply(self, package_id: str, decisions: list[ConfirmationDecision]) -> dict:
        """应用用户决策"""
        
        # 加载确认包
        package = self._load_package(package_id)
        
        # 验证完整性
        self._validate_decisions(package, decisions)
        
        # 应用决策
        results = {
            "added": [],
            "updated": [],
            "skipped": [],
            "rejected": []
        }
        
        for decision in decisions:
            if decision.action == ConfirmationAction.ACCEPT:
                term = self._create_term(decision, package.project_id)
                self.storage.add_term(term, self._create_metadata(term, decision, package.project_id))
                results["added"].append(term.id)
            
            elif decision.action == ConfirmationAction.MODIFY:
                term = self._create_term(decision, package.project_id)
                self.storage.add_term(term, self._create_metadata(term, decision, package.project_id))
                results["added"].append(term.id)
            
            elif decision.action == ConfirmationAction.SKIP:
                results["skipped"].append(decision.original)
            
            elif decision.action == ConfirmationAction.USE_EXISTING:
                # 不需要操作，已有术语会被使用
                pass
            
            elif decision.action == ConfirmationAction.REJECT:
                results["rejected"].append(decision.original)
        
        # 删除确认包
        self._delete_package(package_id)
        
        return results
    
    def _create_term(self, decision: ConfirmationDecision, project_id: str) -> Term:
        """创建术语"""
        return Term(
            id=Term.generate_id(decision.original, decision.scope, project_id if decision.scope == "project" else None),
            original=decision.original,
            translation=decision.final_translation,
            strategy=decision.strategy,
            note=decision.note,
            status="active"
        )
    
    def _create_metadata(self, term: Term, decision: ConfirmationDecision, project_id: str) -> TermMetadata:
        """创建元数据"""
        return TermMetadata(
            term_id=term.id,
            scope=decision.scope,
            project_id=project_id if decision.scope == "project" else None,
            term_original=term.original,
            term_translation=term.translation,
            source="extracted",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def _validate_decisions(self, package: ConfirmationPackage, decisions: list[ConfirmationDecision]):
        """验证决策完整性"""
        # 检查所有候选都有决策
        candidate_originals = {c.original for c in package.candidates}
        decision_originals = {d.original for d in decisions}
        
        missing = candidate_originals - decision_originals
        if missing:
            raise ValueError(f"Missing decisions for: {missing}")
        
        # 检查所有冲突都已解决
        conflict_originals = {c.original for c in package.conflicts}
        for original in conflict_originals:
            decision = next((d for d in decisions if d.original == original), None)
            if not decision or decision.action not in [ConfirmationAction.USE_EXISTING, ConfirmationAction.MODIFY, ConfirmationAction.REJECT]:
                raise ValueError(f"Conflict not resolved for: {original}")
```

**验收标准**：
- [ ] 正确创建确认包
- [ ] 验证决策完整性
- [ ] 正确应用所有决策类型
- [ ] 单元测试覆盖率 > 90%

---

### Task 3.4: 实现交互式 CLI 界面

**目标**：提供友好的命令行确认界面

**文件**：`src/cli/term_confirm.py`

**界面设计**：

```python
import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()

@click.command()
@click.option('--project', required=True, help='Project ID')
def confirm_terms(project: str):
    """交互式术语确认"""
    
    # 1. 提取术语
    console.print("[bold blue]Phase 0: Extracting terms...[/bold blue]")
    extraction_service = TermExtractionService(...)
    candidates = await extraction_service.extract_all(project)
    console.print(f"[green]Found {len(candidates)} candidates[/green]")
    
    # 2. 检测冲突
    console.print("[bold blue]Detecting conflicts...[/bold blue]")
    confirmation_service = TermConfirmationService(...)
    package = confirmation_service.prepare(candidates, project)
    
    if package.conflicts:
        console.print(f"[yellow]Found {len(package.conflicts)} conflicts[/yellow]")
    
    # 3. 逐个确认
    decisions = []
    
    for i, candidate in enumerate(package.candidates, 1):
        console.print(f"\n[bold]Term {i}/{len(package.candidates)}[/bold]")
        
        # 显示候选信息
        table = Table(show_header=False)
        table.add_row("Original", candidate.original)
        table.add_row("Translation", candidate.suggested_translation)
        table.add_row("Occurrences", str(candidate.occurrence_count))
        table.add_row("In Title", "Yes" if candidate.hit_title else "No")
        table.add_row("Context", candidate.context)
        console.print(table)
        
        # 检查冲突
        conflict = next((c for c in package.conflicts if c.original == candidate.original), None)
        if conflict:
            console.print(f"[red]⚠ Conflict: Existing translation is '{conflict.existing_translation}' ({conflict.existing_scope})[/red]")
        
        # 用户选择
        action = Prompt.ask(
            "Action",
            choices=["accept", "modify", "skip", "use_existing" if conflict else None, "reject"],
            default="accept"
        )
        
        decision = ConfirmationDecision(
            original=candidate.original,
            action=ConfirmationAction(action)
        )
        
        if action == "accept":
            decision.final_translation = candidate.suggested_translation
        elif action == "modify":
            decision.final_translation = Prompt.ask("New translation")
            decision.strategy = Prompt.ask("Strategy", choices=["translate", "preserve", "first_annotate"], default="translate")
            if Confirm.ask("Add note?"):
                decision.note = Prompt.ask("Note")
        
        decisions.append(decision)
    
    # 4. 应用决策
    console.print("\n[bold blue]Applying decisions...[/bold blue]")
    results = confirmation_service.apply(package.package_id, decisions)
    
    console.print(f"[green]✓ Added: {len(results['added'])}[/green]")
    console.print(f"[yellow]⊘ Skipped: {len(results['skipped'])}[/yellow]")
    console.print(f"[red]✗ Rejected: {len(results['rejected'])}[/red]")
```

**批量模式**：

```python
@click.command()
@click.option('--project', required=True)
@click.option('--auto-accept', is_flag=True, help='Auto-accept all without conflicts')
def confirm_terms_batch(project: str, auto_accept: bool):
    """批量确认术语"""
    
    # ... 提取和检测 ...
    
    if auto_accept:
        decisions = []
        for candidate in package.candidates:
            conflict = next((c for c in package.conflicts if c.original == candidate.original), None)
            if conflict:
                # 有冲突，需要手动处理
                console.print(f"[yellow]Skipping {candidate.original} (conflict)[/yellow]")
                continue
            
            decisions.append(ConfirmationDecision(
                original=candidate.original,
                action=ConfirmationAction.ACCEPT,
                final_translation=candidate.suggested_translation
            ))
        
        results = confirmation_service.apply(package.package_id, decisions)
        console.print(f"[green]Auto-accepted {len(results['added'])} terms[/green]")
```

**验收标准**：
- [ ] 交互界面友好易用
- [ ] 正确显示所有信息
- [ ] 批量模式正常工作
- [ ] 错误处理完善

---

### Task 3.5: 编写集成测试

**目标**：验证完整确认流程

**文件**：`tests/integration/test_term_confirmation_workflow.py`

**测试场景**：

```python
class TestTermConfirmationWorkflow:
    """术语确认流程集成测试"""
    
    async def test_full_workflow(self, tmp_path):
        """测试完整流程"""
        
        # 1. 准备测试项目
        project_id = "test-project"
        # ... 创建测试文档 ...
        
        # 2. 提取术语
        extraction_service = TermExtractionService(...)
        candidates = await extraction_service.extract_all(project_id)
        assert len(candidates) > 0
        
        # 3. 检测冲突
        confirmation_service = TermConfirmationService(...)
        package = confirmation_service.prepare(candidates, project_id)
        
        # 4. 模拟用户决策
        decisions = [
            ConfirmationDecision(
                original=c.original,
                action=ConfirmationAction.ACCEPT,
                final_translation=c.suggested_translation
            )
            for c in package.candidates
        ]
        
        # 5. 应用决策
        results = confirmation_service.apply(package.package_id, decisions)
        assert len(results["added"]) == len(candidates)
        
        # 6. 验证术语已保存
        storage = GlossaryStorage(tmp_path)
        terms = storage.load_terms("project", project_id)
        assert len(terms) == len(candidates)
    
    async def test_conflict_resolution(self, tmp_path):
        """测试冲突解决"""
        
        # 1. 添加已有术语
        storage = GlossaryStorage(tmp_path)
        existing = Term(original="AI", translation="人工智能")
        storage.add_term(existing, ...)
        
        # 2. 提取候选（包含冲突）
        candidates = [
            TermCandidate(original="AI", suggested_translation="AI", ...)
        ]
        
        # 3. 检测冲突
        confirmation_service = TermConfirmationService(storage, ...)
        package = confirmation_service.prepare(candidates, "test-project")
        assert len(package.conflicts) == 1
        
        # 4. 解决冲突（使用已有）
        decisions = [
            ConfirmationDecision(
                original="AI",
                action=ConfirmationAction.USE_EXISTING
            )
        ]
        results = confirmation_service.apply(package.package_id, decisions)
        
        # 5. 验证没有创建新术语
        assert len(results["added"]) == 0
```

**验收标准**：
- [ ] 所有集成测试通过
- [ ] 覆盖所有确认动作
- [ ] 覆盖冲突解决场景

---

## 交付物

1. **代码**：
   - `src/services/term_extraction_service.py`
   - `src/services/term_conflict_detector.py`
   - `src/services/term_confirmation_service.py`
   - `src/cli/term_confirm.py`

2. **测试**：
   - `tests/unit/services/test_term_extraction.py`
   - `tests/unit/services/test_term_conflict_detector.py`
   - `tests/unit/services/test_term_confirmation.py`
   - `tests/integration/test_term_confirmation_workflow.py`

3. **文档**：
   - 更新 `docs/术语库系统手册.md` 的"术语确认流程"章节
   - 添加 CLI 使用指南

---

## 验收标准

- [ ] 所有任务完成
- [ ] 单元测试覆盖率 > 85%
- [ ] 集成测试全部通过
- [ ] CLI 界面友好易用
- [ ] 代码通过类型检查和格式检查

---

## 依赖和风险

**依赖**：
- Plan 1（GlossaryStorage）
- Plan 2（TermMatcher）

**风险**：
1. **LLM 提取质量不稳定**
   - 缓解：使用结构化输出、添加示例、多次重试
   
2. **确认包过期处理**
   - 缓解：定期清理过期包、提供恢复机制

3. **批量确认误操作**
   - 缓解：添加确认提示、支持撤销

---

## 后续计划

完成 Plan 3 后，可以开始：
- **Plan 4**：翻译会话管理（依赖确认流程）
