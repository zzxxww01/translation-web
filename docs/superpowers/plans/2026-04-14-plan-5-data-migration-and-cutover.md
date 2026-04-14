# Plan 5: 数据迁移和系统切换

## 概述

将旧术语系统的数据迁移到新系统，清理遗留代码，完成系统切换上线。

**目标**：
- 实现数据迁移脚本
- 验证迁移数据完整性
- 清理旧代码和文件
- 更新文档和配置
- 平滑切换到新系统

**预计时间**：1.5-2 周

---

## 任务清单

### Task 5.1: 分析旧系统数据结构

**目标**：理解旧系统的数据格式和存储位置

**文件**：`docs/superpowers/migration/old-system-analysis.md`

**需要分析的文件**：

```python
# 旧系统文件清单
OLD_SYSTEM_FILES = [
    "glossary/global_glossary.json",
    "glossary/global_glossary_semi.json",
    "projects/{project_id}/glossary.json",
    "projects/{project_id}/meta.json",
]

# 旧数据模型
@dataclass
class OldGlossaryEntry:
    """旧术语条目"""
    original: str
    translation: str
    note: Optional[str]
    # ... 其他字段 ...
```

**分析内容**：
1. 旧系统的数据模型
2. 全局/项目术语的存储方式
3. 术语状态和元数据
4. 已知的数据质量问题

**验收标准**：
- [ ] 完成旧系统数据结构文档
- [ ] 识别所有需要迁移的字段
- [ ] 识别数据质量问题

---

### Task 5.2: 实现数据迁移脚本

**目标**：将旧数据转换为新格式

**文件**：`scripts/migrate_terminology.py`

**迁移逻辑**：

```python
import json
from pathlib import Path
from datetime import datetime
import uuid

class TerminologyMigration:
    """术语系统数据迁移"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.stats = {
            "global_terms": 0,
            "project_terms": 0,
            "skipped": 0,
            "errors": []
        }
    
    def migrate_all(self):
        """迁移所有数据"""
        print("=== Terminology System Migration ===\n")
        
        # 1. 迁移全局术语
        print("Step 1: Migrating global glossary...")
        self.migrate_global_glossary()
        
        # 2. 迁移项目术语
        print("\nStep 2: Migrating project glossaries...")
        self.migrate_project_glossaries()
        
        # 3. 生成报告
        print("\n=== Migration Report ===")
        print(f"Global terms migrated: {self.stats['global_terms']}")
        print(f"Project terms migrated: {self.stats['project_terms']}")
        print(f"Skipped entries: {self.stats['skipped']}")
        if self.stats['errors']:
            print(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors']:
                print(f"  - {error}")
        
        if self.dry_run:
            print("\n[DRY RUN] No files were modified.")
        else:
            print("\n[DONE] Migration completed.")
    
    def migrate_global_glossary(self):
        """迁移全局术语库"""
        
        # 读取旧文件
        old_path = Path("glossary/global_glossary.json")
        if not old_path.exists():
            print("  ⚠ global_glossary.json not found, skipping")
            return
        
        old_data = json.loads(old_path.read_text(encoding='utf-8'))
        
        # 转换为新格式
        new_terms = []
        new_metadata = []
        
        for old_entry in old_data:
            try:
                # 创建 Term
                term = self._convert_to_term(old_entry, scope="global")
                new_terms.append(term)
                
                # 创建 TermMetadata
                metadata = self._create_metadata(term, old_entry, scope="global")
                new_metadata.append(metadata)
                
                self.stats['global_terms'] += 1
            
            except Exception as e:
                self.stats['errors'].append(f"Global term '{old_entry.get('original')}': {e}")
                self.stats['skipped'] += 1
        
        # 保存新文件
        if not self.dry_run:
            new_terms_path = Path("glossary/terms.json")
            new_metadata_path = Path("glossary/metadata.json")
            
            new_terms_path.write_text(json.dumps(new_terms, ensure_ascii=False, indent=2))
            new_metadata_path.write_text(json.dumps(new_metadata, ensure_ascii=False, indent=2))
        
        print(f"  ✓ Migrated {len(new_terms)} global terms")
    
    def migrate_project_glossaries(self):
        """迁移所有项目术语库"""
        
        projects_dir = Path("projects")
        if not projects_dir.exists():
            print("  ⚠ projects/ directory not found")
            return
        
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue
            
            project_id = project_dir.name
            old_glossary = project_dir / "glossary.json"
            
            if not old_glossary.exists():
                continue
            
            print(f"  Migrating {project_id}...")
            self.migrate_project_glossary(project_id, old_glossary)
    
    def migrate_project_glossary(self, project_id: str, old_path: Path):
        """迁移单个项目术语库"""
        
        old_data = json.loads(old_path.read_text(encoding='utf-8'))
        
        new_terms = []
        new_metadata = []
        
        for old_entry in old_data:
            try:
                term = self._convert_to_term(old_entry, scope="project", project_id=project_id)
                new_terms.append(term)
                
                metadata = self._create_metadata(term, old_entry, scope="project", project_id=project_id)
                new_metadata.append(metadata)
                
                self.stats['project_terms'] += 1
            
            except Exception as e:
                self.stats['errors'].append(f"Project {project_id} term '{old_entry.get('original')}': {e}")
                self.stats['skipped'] += 1
        
        # 保存新文件
        if not self.dry_run:
            new_dir = Path(f"projects/{project_id}/glossary")
            new_dir.mkdir(parents=True, exist_ok=True)
            
            (new_dir / "terms.json").write_text(json.dumps(new_terms, ensure_ascii=False, indent=2))
            (new_dir / "metadata.json").write_text(json.dumps(new_metadata, ensure_ascii=False, indent=2))
        
        print(f"    ✓ {len(new_terms)} terms")
    
    def _convert_to_term(self, old_entry: dict, scope: str, project_id: str = None) -> dict:
        """转换为新 Term 格式"""
        
        original = old_entry['original']
        translation = old_entry.get('translation', '')
        
        # 生成确定性 ID
        term_id = self._generate_term_id(original, scope, project_id)
        
        # 推断翻译策略
        strategy = self._infer_strategy(old_entry)
        
        return {
            "id": term_id,
            "original": original,
            "translation": translation,
            "strategy": strategy,
            "note": old_entry.get('note'),
            "status": "active"  # 旧系统所有术语默认激活
        }
    
    def _create_metadata(self, term: dict, old_entry: dict, scope: str, project_id: str = None) -> dict:
        """创建 TermMetadata"""
        
        now = datetime.utcnow().isoformat()
        
        return {
            "term_id": term['id'],
            "scope": scope,
            "project_id": project_id,
            "term_original": term['original'],
            "term_translation": term['translation'],
            "overrides_term_id": None,  # 迁移时无法确定，需要后处理
            "promoted_from_term_id": None,
            "tags": old_entry.get('tags', []),
            "source": "migrated",
            "usage_count": old_entry.get('usage_count', 0),
            "last_used_at": old_entry.get('last_used_at'),
            "is_deleted": False,
            "created_at": old_entry.get('created_at', now),
            "updated_at": now
        }
    
    def _generate_term_id(self, original: str, scope: str, project_id: str = None) -> str:
        """生成确定性 Term ID"""
        namespace = uuid.UUID('00000000-0000-0000-0000-000000000000')
        name = f"{original}:{scope}:{project_id or ''}"
        return str(uuid.uuid5(namespace, name))
    
    def _infer_strategy(self, old_entry: dict) -> str:
        """推断翻译策略"""
        # 简单规则：如果 translation == original，推断为 preserve
        if old_entry['original'] == old_entry.get('translation'):
            return "preserve"
        return "translate"

# 使用示例
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate terminology system data")
    parser.add_argument('--dry-run', action='store_true', help='Preview changes without modifying files')
    parser.add_argument('--backup', action='store_true', help='Create backup before migration')
    args = parser.parse_args()
    
    # 备份
    if args.backup and not args.dry_run:
        print("Creating backup...")
        import shutil
        from datetime import datetime
        backup_dir = Path(f"backups/terminology-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree("glossary", backup_dir / "glossary")
        shutil.copytree("projects", backup_dir / "projects")
        print(f"Backup created at {backup_dir}\n")
    
    # 执行迁移
    migration = TerminologyMigration(dry_run=args.dry_run)
    migration.migrate_all()
```

**验收标准**：
- [ ] 迁移脚本正确转换所有字段
- [ ] Dry-run 模式正常工作
- [ ] 生成详细的迁移报告
- [ ] 支持备份功能

---

### Task 5.3: 验证迁移数据

**目标**：确保迁移后的数据完整且正确

**文件**：`scripts/validate_migration.py`

**验证内容**：

```python
class MigrationValidator:
    """迁移数据验证器"""
    
    def validate_all(self):
        """验证所有迁移数据"""
        
        print("=== Migration Validation ===\n")
        
        issues = []
        
        # 1. 验证文件结构
        print("Step 1: Validating file structure...")
        issues.extend(self.validate_file_structure())
        
        # 2. 验证数据完整性
        print("Step 2: Validating data integrity...")
        issues.extend(self.validate_data_integrity())
        
        # 3. 验证术语数量
        print("Step 3: Validating term counts...")
        issues.extend(self.validate_term_counts())
        
        # 4. 验证引用关系
        print("Step 4: Validating references...")
        issues.extend(self.validate_references())
        
        # 报告
        if issues:
            print(f"\n⚠ Found {len(issues)} issues:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("\n✓ All validations passed!")
            return True
    
    def validate_file_structure(self) -> list[str]:
        """验证文件结构"""
        issues = []
        
        # 检查必需文件
        required_files = [
            "glossary/terms.json",
            "glossary/metadata.json"
        ]
        
        for file_path in required_files:
            if not Path(file_path).exists():
                issues.append(f"Missing file: {file_path}")
        
        return issues
    
    def validate_data_integrity(self) -> list[str]:
        """验证数据完整性"""
        issues = []
        
        # 加载数据
        terms = self._load_json("glossary/terms.json")
        metadata = self._load_json("glossary/metadata.json")
        
        # 检查每个 term 都有对应的 metadata
        term_ids = {t['id'] for t in terms}
        metadata_term_ids = {m['term_id'] for m in metadata}
        
        missing_metadata = term_ids - metadata_term_ids
        if missing_metadata:
            issues.append(f"Terms without metadata: {missing_metadata}")
        
        orphan_metadata = metadata_term_ids - term_ids
        if orphan_metadata:
            issues.append(f"Metadata without terms: {orphan_metadata}")
        
        return issues
    
    def validate_term_counts(self) -> list[str]:
        """验证术语数量"""
        issues = []
        
        # 统计旧系统术语数量
        old_global = self._count_old_terms("glossary/global_glossary.json")
        
        # 统计新系统术语数量
        new_global = len(self._load_json("glossary/terms.json"))
        
        if old_global != new_global:
            issues.append(f"Global term count mismatch: old={old_global}, new={new_global}")
        
        return issues
    
    def validate_references(self) -> list[str]:
        """验证引用关系"""
        issues = []
        
        metadata = self._load_json("glossary/metadata.json")
        term_ids = {t['id'] for t in self._load_json("glossary/terms.json")}
        
        for m in metadata:
            # 检查 overrides_term_id
            if m.get('overrides_term_id') and m['overrides_term_id'] not in term_ids:
                issues.append(f"Invalid overrides_term_id: {m['overrides_term_id']}")
            
            # 检查 promoted_from_term_id
            if m.get('promoted_from_term_id') and m['promoted_from_term_id'] not in term_ids:
                issues.append(f"Invalid promoted_from_term_id: {m['promoted_from_term_id']}")
        
        return issues
```

**验收标准**：
- [ ] 验证脚本检测所有数据问题
- [ ] 生成详细的验证报告
- [ ] 所有验证通过

---

### Task 5.4: 清理旧代码

**目标**：删除旧术语系统的代码和文件

**需要清理的文件**：

```python
# 旧代码文件
OLD_CODE_FILES = [
    "src/services/terminology_review_service.py",
    "src/agents/consistency_reviewer.py",
    # ... 其他旧文件 ...
]

# 旧数据文件（迁移后备份）
OLD_DATA_FILES = [
    "glossary/global_glossary.json",
    "glossary/global_glossary_semi.json",
    "projects/*/glossary.json",  # 项目级旧文件
]
```

**清理步骤**：

1. 备份旧文件到 `backups/old-system/`
2. 删除旧代码文件
3. 更新 import 语句
4. 删除未使用的依赖

**验收标准**：
- [ ] 所有旧代码已删除
- [ ] 旧数据已备份
- [ ] 代码库可以正常运行
- [ ] 无 import 错误

---

### Task 5.5: 更新文档和配置

**目标**：更新所有相关文档

**需要更新的文档**：

1. **docs/术语库系统手册.md**
   - 更新为新系统的使用说明
   - 添加迁移指南

2. **README.md**
   - 更新术语系统介绍

3. **docs/superpowers/migration/migration-guide.md**（新建）
   - 迁移步骤
   - 回滚方案
   - 常见问题

**验收标准**：
- [ ] 所有文档已更新
- [ ] 迁移指南完整
- [ ] 用户手册准确

---

### Task 5.6: 系统切换和上线

**目标**：平滑切换到新系统

**切换步骤**：

```bash
# 1. 备份当前系统
python scripts/backup_system.py

# 2. 运行迁移（dry-run）
python scripts/migrate_terminology.py --dry-run

# 3. 验证迁移结果
python scripts/validate_migration.py

# 4. 执行迁移
python scripts/migrate_terminology.py --backup

# 5. 再次验证
python scripts/validate_migration.py

# 6. 运行集成测试
pytest tests/integration/

# 7. 清理旧代码
python scripts/cleanup_old_system.py --backup

# 8. 提交变更
git add .
git commit -m "feat: migrate to new terminology system"
```

**回滚方案**：

```bash
# 如果出现问题，从备份恢复
python scripts/rollback_migration.py --backup-id <backup-timestamp>
```

**验收标准**：
- [ ] 切换步骤文档化
- [ ] 回滚方案可用
- [ ] 所有测试通过
- [ ] 系统正常运行

---

## 交付物

1. **脚本**：
   - `scripts/migrate_terminology.py`
   - `scripts/validate_migration.py`
   - `scripts/cleanup_old_system.py`
   - `scripts/rollback_migration.py`

2. **文档**：
   - `docs/superpowers/migration/old-system-analysis.md`
   - `docs/superpowers/migration/migration-guide.md`
   - 更新 `docs/术语库系统手册.md`

3. **备份**：
   - `backups/old-system/` 目录

---

## 验收标准

- [ ] 所有任务完成
- [ ] 迁移脚本正确运行
- [ ] 数据验证通过
- [ ] 旧代码已清理
- [ ] 文档已更新
- [ ] 系统正常运行
- [ ] 回滚方案可用

---

## 依赖和风险

**依赖**：
- Plan 1-4（新系统已实现并测试）

**风险**：
1. **数据丢失**
   - 缓解：多次备份、dry-run 验证、分步迁移

2. **迁移失败**
   - 缓解：完善的回滚方案、详细的错误日志

3. **业务中断**
   - 缓解：选择低峰期迁移、准备快速回滚

4. **数据不一致**
   - 缓解：严格的验证流程、人工抽查

---

## 后续计划

完成 Plan 5 后：
- 监控新系统运行状态
- 收集用户反馈
- 优化性能
- 添加新功能（如术语推荐、自动分类等）

---

## 附录：迁移检查清单

### 迁移前
- [ ] 备份所有数据
- [ ] 通知相关人员
- [ ] 准备回滚方案
- [ ] 运行 dry-run

### 迁移中
- [ ] 执行迁移脚本
- [ ] 验证数据完整性
- [ ] 运行集成测试
- [ ] 清理旧代码

### 迁移后
- [ ] 验证系统功能
- [ ] 检查性能指标
- [ ] 更新文档
- [ ] 培训用户
- [ ] 监控运行状态

### 回滚触发条件
- 数据验证失败
- 集成测试失败
- 关键功能不可用
- 性能严重下降
