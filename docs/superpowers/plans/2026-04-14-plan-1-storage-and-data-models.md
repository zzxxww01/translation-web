# Plan 1: 存储层与数据模型

## 概述

实现术语系统的基础存储层和核心数据模型，为后续所有功能提供稳定的数据访问接口。

**目标**：
- 定义清晰的数据模型（Term、TermMetadata、DecisionRecord）
- 实现 GlossaryStorage 服务
- 建立文件系统存储结构
- 提供完整的单元测试覆盖

**预计时间**：1-1.5 周

---

## 任务清单

### Task 1.1: 定义核心数据模型

**目标**：创建 Pydantic 数据模型类

**文件**：`src/core/models/term.py`

**实现要点**：

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime
import uuid

class TranslationStrategy(str, Enum):
    """翻译策略枚举"""
    TRANSLATE = "translate"              # 正常翻译
    PRESERVE = "preserve"                # 保留原文
    FIRST_ANNOTATE = "first_annotate"    # 首次注释
    PRESERVE_ANNOTATE = "preserve_annotate"  # 保留+注释

class Term(BaseModel):
    """术语核心实体"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original: str
    translation: str
    strategy: TranslationStrategy = TranslationStrategy.TRANSLATE
    note: Optional[str] = None
    status: Literal["active", "inactive"] = "active"
    
    @staticmethod
    def generate_id(original: str, scope: str, project_id: Optional[str] = None) -> str:
        """使用 UUID v5 生成确定性 ID"""
        namespace = uuid.NAMESPACE_DNS
        name = f"{scope}:{project_id or 'global'}:{original.lower()}"
        return str(uuid.uuid5(namespace, name))
    
    class Config:
        frozen = False  # 允许修改

class TermMetadata(BaseModel):
    """术语元数据"""
    term_id: str
    scope: Literal["global", "project"]
    project_id: Optional[str] = None
    
    # 冗余字段（软删除后仍可查询）
    term_original: str
    term_translation: str
    
    # 关系字段
    overrides_term_id: Optional[str] = None      # 项目术语覆盖全局术语
    promoted_from_term_id: Optional[str] = None  # 从项目提升到全局
    
    # 管理字段
    tags: list[str] = Field(default_factory=list)
    source: str = "manual"  # manual, extracted, imported
    usage_count: int = 0
    last_used_at: Optional[datetime] = None
    is_deleted: bool = False
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class DecisionRecord(BaseModel):
    """术语决策审计记录"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action: Literal["create", "update", "delete", "activate", "deactivate", "skip"]
    term_id: str
    term_original: str
    scope: Literal["global", "project"]
    project_id: Optional[str] = None
    
    # 变更详情
    changes: dict  # {"field": {"old": ..., "new": ...}}
    reason: Optional[str] = None
    session_id: Optional[str] = None
```

**验收标准**：
- [ ] 所有模型通过 Pydantic 验证
- [ ] Term.generate_id() 生成确定性 UUID
- [ ] 模型支持 JSON 序列化/反序列化
- [ ] 单元测试覆盖率 > 95%

---

### Task 1.2: 实现 GlossaryStorage 服务

**目标**：提供术语和元数据的 CRUD 操作

**文件**：`src/services/glossary_storage.py`

**核心接口**：

```python
class GlossaryStorage:
    """术语存储服务"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.global_path = base_path / "glossary"
        
    # === Term CRUD ===
    
    def load_terms(self, scope: str, project_id: Optional[str] = None) -> list[Term]:
        """加载术语列表"""
        pass
    
    def save_terms(self, terms: list[Term], scope: str, project_id: Optional[str] = None):
        """保存术语列表（覆盖写入）"""
        pass
    
    def get_term(self, term_id: str, scope: str, project_id: Optional[str] = None) -> Optional[Term]:
        """获取单个术语"""
        pass
    
    def add_term(self, term: Term, metadata: TermMetadata) -> Term:
        """添加新术语（原子操作）"""
        pass
    
    def update_term(self, term: Term, metadata: TermMetadata, changes: dict) -> Term:
        """更新术语（记录审计日志）"""
        pass
    
    def delete_term(self, term_id: str, scope: str, project_id: Optional[str] = None, reason: str = ""):
        """软删除术语"""
        pass
    
    # === Metadata CRUD ===
    
    def load_metadata(self, scope: str, project_id: Optional[str] = None) -> list[TermMetadata]:
        """加载元数据列表"""
        pass
    
    def save_metadata(self, metadata_list: list[TermMetadata], scope: str, project_id: Optional[str] = None):
        """保存元数据列表"""
        pass
    
    def get_metadata(self, term_id: str, scope: str, project_id: Optional[str] = None) -> Optional[TermMetadata]:
        """获取术语元数据"""
        pass
    
    # === 审计日志 ===
    
    def append_decision(self, record: DecisionRecord, scope: str, project_id: Optional[str] = None):
        """追加决策记录（JSONL）"""
        pass
    
    def load_decisions(self, scope: str, project_id: Optional[str] = None, 
                      since: Optional[datetime] = None) -> list[DecisionRecord]:
        """加载决策记录"""
        pass
    
    # === 高级查询 ===
    
    def find_terms(self, 
                   scope: str,
                   project_id: Optional[str] = None,
                   status: Optional[str] = None,
                   original_pattern: Optional[str] = None) -> list[tuple[Term, TermMetadata]]:
        """查询术语（支持过滤）"""
        pass
    
    def get_active_terms(self, project_id: Optional[str] = None) -> list[Term]:
        """获取所有激活术语（全局 + 项目，项目覆盖全局）"""
        pass
```

**实现要点**：
1. 使用 `fcntl.flock()` (Unix) 或 `msvcrt.locking()` (Windows) 实现文件锁
2. 原子写入：先写临时文件，再 rename
3. 错误处理：文件不存在时返回空列表，损坏时抛出异常
4. 性能优化：缓存最近加载的数据（带 TTL）

**验收标准**：
- [ ] 所有 CRUD 操作正常工作
- [ ] 并发写入不会导致数据损坏（使用文件锁）
- [ ] 软删除正确更新 Term.status 和 TermMetadata.is_deleted
- [ ] get_active_terms() 正确处理项目覆盖全局的逻辑
- [ ] 单元测试覆盖率 > 90%

---

### Task 1.3: 建立文件系统存储结构

**目标**：创建标准化的目录和文件布局

**目录结构**：

```
glossary/                          # 全局术语库
├── terms.json                     # List[Term]
├── metadata.json                  # List[TermMetadata]
└── audit/
    └── decisions.jsonl            # 审计日志

projects/{project_id}/
├── glossary/
│   ├── terms.json                 # 项目术语
│   ├── metadata.json              # 项目元数据
│   └── sessions/
│       ├── {session_id}.json      # 会话快照
│       └── ...
└── artifacts/
    ├── term-extraction/
    │   └── latest.json            # 最近一次提取结果
    └── audit/
        └── decisions.jsonl        # 项目审计日志
```

**实现任务**：

1. **创建初始化脚本**：`src/services/glossary_storage.py::initialize_storage()`
   ```python
   def initialize_storage(base_path: Path, project_id: Optional[str] = None):
       """初始化存储结构"""
       if project_id:
           # 初始化项目目录
           project_path = base_path / "projects" / project_id
           (project_path / "glossary" / "sessions").mkdir(parents=True, exist_ok=True)
           (project_path / "artifacts" / "term-extraction").mkdir(parents=True, exist_ok=True)
           (project_path / "artifacts" / "audit").mkdir(parents=True, exist_ok=True)
           
           # 创建空文件
           for file in ["glossary/terms.json", "glossary/metadata.json"]:
               file_path = project_path / file
               if not file_path.exists():
                   file_path.write_text("[]")
       else:
           # 初始化全局目录
           global_path = base_path / "glossary"
           (global_path / "audit").mkdir(parents=True, exist_ok=True)
           
           for file in ["terms.json", "metadata.json"]:
               file_path = global_path / file
               if not file_path.exists():
                   file_path.write_text("[]")
   ```

2. **创建 CLI 命令**：`src/cli/glossary.py`
   ```bash
   # 初始化全局术语库
   python -m src.cli.glossary init
   
   # 初始化项目术语库
   python -m src.cli.glossary init --project memory-mania
   ```

**验收标准**：
- [ ] 初始化脚本创建所有必需目录和文件
- [ ] CLI 命令正常工作
- [ ] 重复初始化不会覆盖现有数据

---

### Task 1.4: 实现数据验证和修复工具

**目标**：检测和修复数据完整性问题

**文件**：`src/services/glossary_validator.py`

**功能**：

```python
class GlossaryValidator:
    """术语库数据验证器"""
    
    def validate_storage(self, scope: str, project_id: Optional[str] = None) -> ValidationReport:
        """验证存储完整性"""
        issues = []
        
        # 1. 检查文件存在性
        # 2. 检查 JSON 格式
        # 3. 检查 Term 和 Metadata 一致性
        # 4. 检查 ID 唯一性
        # 5. 检查引用完整性（overrides_term_id 必须存在）
        # 6. 检查软删除一致性（Term.status == "deleted" <=> TermMetadata.is_deleted == True）
        
        return ValidationReport(is_valid=len(issues) == 0, issues=issues)
    
    def repair_storage(self, scope: str, project_id: Optional[str] = None, dry_run: bool = True) -> RepairReport:
        """修复数据问题"""
        # 1. 移除孤立的 Metadata（对应的 Term 不存在）
        # 2. 为缺失 Metadata 的 Term 创建默认 Metadata
        # 3. 修复软删除不一致
        # 4. 重新生成 UUID（如果格式错误）
        pass
```

**CLI 命令**：
```bash
# 验证全局术语库
python -m src.cli.glossary validate

# 验证项目术语库
python -m src.cli.glossary validate --project memory-mania

# 修复数据问题（dry-run）
python -m src.cli.glossary repair --dry-run

# 实际修复
python -m src.cli.glossary repair
```

**验收标准**：
- [ ] 能检测所有定义的数据完整性问题
- [ ] 修复操作不会丢失数据
- [ ] dry-run 模式不修改文件
- [ ] 生成详细的验证和修复报告

---

### Task 1.5: 编写单元测试

**目标**：确保存储层稳定可靠

**文件**：`tests/unit/services/test_glossary_storage.py`

**测试用例**：

```python
class TestGlossaryStorage:
    """GlossaryStorage 单元测试"""
    
    def test_term_crud_operations(self, tmp_path):
        """测试术语 CRUD"""
        storage = GlossaryStorage(tmp_path)
        
        # Create
        term = Term(original="AI", translation="人工智能")
        metadata = TermMetadata(term_id=term.id, scope="global", term_original=term.original, term_translation=term.translation)
        storage.add_term(term, metadata)
        
        # Read
        loaded = storage.get_term(term.id, "global")
        assert loaded.original == "AI"
        
        # Update
        term.translation = "AI"
        storage.update_term(term, metadata, {"translation": {"old": "人工智能", "new": "AI"}})
        
        # Delete (soft)
        storage.delete_term(term.id, "global", reason="测试删除")
        deleted = storage.get_term(term.id, "global")
        assert deleted.status == "deleted"
    
    def test_concurrent_writes(self, tmp_path):
        """测试并发写入（使用文件锁）"""
        # 使用 threading 模拟并发
        pass
    
    def test_atomic_write(self, tmp_path):
        """测试原子写入（中断不会损坏数据）"""
        pass
    
    def test_get_active_terms_with_override(self, tmp_path):
        """测试项目术语覆盖全局术语"""
        storage = GlossaryStorage(tmp_path)
        
        # 添加全局术语
        global_term = Term(id=Term.generate_id("AI", "global"), original="AI", translation="人工智能")
        global_meta = TermMetadata(term_id=global_term.id, scope="global", term_original="AI", term_translation="人工智能")
        storage.add_term(global_term, global_meta)
        
        # 添加项目术语（覆盖）
        project_term = Term(id=Term.generate_id("AI", "project", "test-project"), original="AI", translation="AI")
        project_meta = TermMetadata(
            term_id=project_term.id, 
            scope="project", 
            project_id="test-project",
            term_original="AI", 
            term_translation="AI",
            overrides_term_id=global_term.id
        )
        storage.add_term(project_term, project_meta)
        
        # 获取激活术语
        active = storage.get_active_terms(project_id="test-project")
        ai_term = next(t for t in active if t.original == "AI")
        assert ai_term.translation == "AI"  # 项目术语覆盖全局
    
    def test_decision_audit_log(self, tmp_path):
        """测试审计日志追加"""
        pass
```

**测试覆盖目标**：
- 单元测试覆盖率 > 90%
- 所有边界情况（空文件、损坏文件、并发访问）
- 所有错误路径（文件不存在、权限错误）

**验收标准**：
- [ ] 所有测试通过
- [ ] 覆盖率达标
- [ ] 测试运行时间 < 5 秒

---

## 集成测试

**文件**：`tests/integration/test_glossary_storage_integration.py`

**测试场景**：

1. **完整生命周期测试**：
   - 初始化存储 → 添加术语 → 更新 → 软删除 → 验证审计日志

2. **跨作用域测试**：
   - 添加全局术语 → 添加项目术语（覆盖）→ 获取激活术语 → 验证优先级

3. **数据迁移准备**：
   - 加载旧格式数据 → 验证能正常读取（为 Plan 5 做准备）

**验收标准**：
- [ ] 所有集成测试通过
- [ ] 测试覆盖真实使用场景

---

## 交付物

1. **代码**：
   - `src/core/models/term.py` - 数据模型
   - `src/services/glossary_storage.py` - 存储服务
   - `src/services/glossary_validator.py` - 验证工具
   - `src/cli/glossary.py` - CLI 命令

2. **测试**：
   - `tests/unit/services/test_glossary_storage.py`
   - `tests/integration/test_glossary_storage_integration.py`

3. **文档**：
   - 更新 `docs/术语库系统手册.md` 的"数据模型"章节
   - 添加 API 文档（docstrings）

4. **工具**：
   - CLI 命令：`init`, `validate`, `repair`

---

## 验收标准

- [ ] 所有任务完成
- [ ] 单元测试覆盖率 > 90%
- [ ] 集成测试全部通过
- [ ] CLI 命令正常工作
- [ ] 代码通过 mypy 类型检查
- [ ] 代码通过 ruff 格式检查
- [ ] 文档更新完成

---

## 依赖和风险

**依赖**：
- 无外部依赖（这是第一个 Plan）

**风险**：
1. **文件锁在 Windows 上的兼容性**
   - 缓解：使用 `portalocker` 库统一跨平台文件锁
   
2. **UUID v5 生成的确定性**
   - 缓解：编写详细的单元测试验证

3. **软删除导致的查询复杂度**
   - 缓解：在 `get_active_terms()` 中明确过滤 `status != "deleted"`

---

## 后续计划

完成 Plan 1 后，可以开始：
- **Plan 2**：术语匹配引擎（依赖 Term 数据模型）
- **Plan 3**：术语确认流程（依赖 GlossaryStorage）
