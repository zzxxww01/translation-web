# Plan 5 代码审查报告

**审查日期**：2026-04-14  
**审查范围**：数据迁移和系统切换实现  
**总体评级**：B+ (良好，但有关键问题)

## 执行摘要

Plan 5 成功迁移了 513 个术语，验证通过率 100%。架构设计良好，关注点分离清晰。但发现了 **4 个 P0 关键问题**需要立即修复，以及多个设计和安全性问题。

## 关键发现

### 🔴 P0 - 关键问题（立即修复）

#### 1. UUID 生成不一致
**位置**：`scripts/migrate_terminology.py:54-58` vs `src/models/terminology.py:14-39`

**问题**：
- 迁移脚本：`scope:original:translation`
- 模型函数：`scope:original` 或 `scope:project_id:original`
- **结果**：迁移后的术语 ID 无法通过模型的 `generate_term_id()` 查找

**影响**：破坏了整个确定性 ID 系统

**修复**：迁移脚本必须使用与模型相同的 ID 生成逻辑

---

#### 2. 迁移脚本引用不存在的字段
**位置**：`scripts/migrate_terminology.py:106-107`

```python
term = Term(
    id=term_id,
    original=original,
    translation=translation,
    strategy=new_strategy,
    source_lang="en",  # ❌ Term 模型中不存在
    target_lang="zh"   # ❌ Term 模型中不存在
)
```

**影响**：迁移脚本应该失败但成功了，说明验证不够严格

**修复**：移除 `source_lang` 和 `target_lang` 字段

---

#### 3. 缺少 portalocker 依赖
**位置**：`src/services/glossary_storage.py:14-18`

**问题**：
- `portalocker` 未安装
- 文件锁定完全禁用
- 回退到弱的 3 次重试机制
- 并发访问时存在数据损坏风险

**修复**：
1. 添加到 requirements.txt
2. 安装该包
3. 验证文件锁定工作正常

---

#### 4. 回滚脚本备份路径错误
**位置**：`scripts/rollback_migration.py`

**问题**：
- 脚本期望：`glossary_backup/`
- 实际位置：`backups/terminology/20260414_170417/`

**修复**：更新回滚脚本使用正确的备份路径

---

### 🟡 P1 - 高优先级（生产前修复）

#### 5. add_term 中的竞态条件
**位置**：`src/services/glossary_storage.py:284-318`

```python
def add_term(self, term: Term, metadata: TermMetadata) -> Term:
    terms = self.load_terms(scope, project_id)  # ← 读取
    if any(t.id == term.id for t in terms):     # ← 检查
        raise ValueError(...)
    terms.append(term)                           # ← 修改
    self.save_terms(terms, scope, project_id)    # ← 写入
```

**问题**：TOCTOU (Time-of-Check-Time-of-Use) 竞态条件

**影响**：并发场景下可能丢失或重复术语

---

#### 6. 缺少事务支持
**位置**：`src/services/glossary_storage.py:284-318`

```python
self.save_terms(terms, scope, project_id)      # ← 写入 1
# ... metadata 操作 ...
self.save_metadata(metadata_list, scope, project_id)  # ← 写入 2（可能失败）
```

**问题**：如果写入 2 失败，会留下没有元数据的孤立术语

**修复**：实现原子操作或回滚机制

---

#### 7. 软删除实现不完整
**位置**：`src/services/glossary_storage.py:365-416`

**问题**：
- 同时使用 `Term.status` 和 `TermMetadata.is_deleted`
- `load_terms()` 返回所有术语包括 inactive
- `get_active_terms()` 只检查 status 不检查 is_deleted
- 不一致：为什么需要两个标志？

**修复**：只使用一个标志，统一软删除逻辑

---

### ⚠️ 设计问题

#### 元数据冗余
**位置**：`src/models/terminology.py:156-158`

```python
class TermMetadata(BaseModel):
    term_id: str
    term_original: str      # ← 冗余副本
    term_translation: str   # ← 冗余副本
```

**理由**："用于软删除查询"

**问题**：创建数据同步问题。如果 `Term.translation` 更新但 `TermMetadata.term_translation` 没更新，它们会分歧。

**建议**：移除冗余字段。通过 `term_id` 连接 Term + TermMetadata 查询软删除术语。

---

### 📊 性能评估

**评级**：C (可接受但低效)

**问题**：

1. **每次操作都完整读取文件**
   - `load_terms()` 读取整个 JSON 文件，即使只查找单个术语
   - 无缓存层
   - 513 术语 × 2 文件 = 每次操作 ~1MB 读取

2. **无批量操作**
   - `add_term()` 为每个术语写入整个文件
   - 应该有 `add_terms_batch()` 用于批量导入

3. **find_terms() 中的线性搜索**
   - O(n) 搜索所有术语
   - 大型术语表应使用索引或数据库

4. **portalocker 回退效率低**
   - 3 次重试加睡眠延迟在冲突时增加 0.3s 延迟

---

### 🔒 迁移安全性

**评级**：B (良好但可改进)

**优势**：
- ✅ 迁移前创建备份
- ✅ 支持 dry-run 模式
- ✅ 4 检查验证系统通过
- ✅ 提供回滚脚本

**劣势**：
- ❌ 迁移脚本有 bug 但验证通过（说明验证没有捕获 bug）
- ❌ 无备份校验和验证
- ❌ 回滚脚本在恢复前不验证备份完整性
- ⚠️ 回滚期望 `glossary_backup` 但备份在 `backups/terminology/`

---

### 🔗 集成质量

**评级**：B (结构良好，实现不完整)

**four_step_translator.py**：
- ✅ 服务通过构造函数正确注入
- ✅ 可选依赖处理优雅
- ⚠️ 服务已初始化但在显示的代码中**未实际使用**

**term_injection_service.py**：
- ✅ 构建约束块的清晰 API
- ✅ 首次出现跟踪已实现
- ✅ 基于策略的分组工作良好

**term_validation_service.py**：
- ✅ 全面的验证和违规跟踪
- ⚠️ 依赖未审查的 `TermMatcher`
- ⚠️ 简单的子串匹配可能有误报

**translation_session_service.py**：
- ✅ 会话生命周期定义良好
- ✅ 变更检测的快照机制
- ⚠️ `detect_term_changes()` 实现不完整（第 160-162 行）

---

## 优先级修复建议

### P0 - 关键（立即修复）

1. ✅ **修复 UUID 生成不一致** - 迁移和模型必须使用相同逻辑
2. ✅ **从迁移脚本移除 source_lang/target_lang** - 字段不存在
3. ✅ **安装 portalocker** - 添加到 requirements.txt 并安装
4. ✅ **修复回滚脚本备份路径** - 更新为使用 `backups/terminology/`

### P1 - 高（生产前修复）

5. **为 add_term/update_term 添加事务支持** - 实现部分失败时的回滚
6. **实现无 portalocker 的正确锁定** - 使用基于文件的锁或 SQLite
7. **添加批量操作** - `add_terms_batch()`, `update_terms_batch()`
8. **完善软删除实现** - 移除冗余字段，修复查询

### P2 - 中（提高质量）

9. **添加全面的日志记录** - 所有 CRUD 操作应记录日志
10. **缩小异常处理范围** - 只捕获特定异常
11. **添加集成测试** - 测试并发访问、回滚、验证
12. **添加缓存层** - 缓存频繁访问的术语

### P3 - 低（锦上添花）

13. **为搜索添加索引** - 使用 SQLite 或内存索引
14. **添加校验和验证** - 验证备份完整性
15. **添加指标/监控** - 跟踪操作延迟、错误率
16. **考虑数据库迁移** - SQLite 可以解决许多问题

---

## 总结

Plan 5 实现展示了扎实的架构思维，关注点分离良好，验证全面。但是，**UUID 生成中的关键 bug 和缺少依赖**带来数据完整性风险。尽管有 bug，迁移仍然成功，说明验证系统需要加强。

**关键行动项**：
1. 立即修复 UUID 生成不匹配
2. 安装 portalocker 或实现正确的锁定
3. 添加事务支持以防止部分写入
4. 完善软删除实现
5. 添加全面的集成测试

**数据丢失风险**：中等 - 竞态条件和缺少事务可能在并发场景下导致数据丢失，但单线程使用是安全的。
