# 术语提取和确认流程完整指南

**更新日期**：2026-04-14  
**适用系统**：新术语系统（Plan 5 迁移后）

---

## 概述

术语提取和确认是一个多步骤流程，包括：
1. **自动提取**：LLM 从文档中提取候选术语
2. **冲突检测**：检查与已有术语的冲突
3. **策略确定**：自动推断或手动选择翻译策略
4. **用户确认**：用户审核并决定如何处理
5. **应用决策**：将确认的术语添加到术语库

---

## 第一步：术语提取

### 触发方式
```python
from src.services.term_extraction_service import TermExtractionService

# 初始化服务
extraction_service = TermExtractionService(llm_provider, storage)

# 提取项目中的所有候选术语
candidates = await extraction_service.extract_all(project_id)
```

### 提取过程

#### 1. 收集文本
- 项目标题
- 所有章节的源文本
- 合并为完整文档

#### 2. LLM 提取
系统会调用 LLM 提取候选术语，LLM 会返回：
```json
{
  "original": "TSMC",
  "translation": "台积电",
  "confidence": 0.95,
  "context": "TSMC is the leading foundry..."
}
```

#### 3. 统计分析
- **出现次数**：在文档中出现多少次
- **标题命中**：是否出现在标题中
- **章节分布**：出现在哪些章节

#### 4. 重要性排序
按以下优先级排序：
1. 是否在标题中（标题术语更重要）
2. 出现次数（高频术语更重要）
3. LLM 置信度（高置信度更可靠）

### 提取结果
```python
@dataclass
class TermCandidate:
    original: str                    # "TSMC"
    suggested_translation: str       # "台积电"
    confidence: float                # 0.95
    context: str                     # "TSMC is the leading..."
    occurrence_count: int            # 15
    hit_title: bool                  # True
    sections: List[str]              # ["intro", "section-1"]
```

---

## 第二步：冲突检测

### 触发方式
```python
from src.services.term_conflict_detector import TermConflictDetector

# 初始化检测器
detector = TermConflictDetector(storage)

# 检测冲突
conflicts = detector.detect(candidates, project_id)
```

### 冲突类型

#### 1. TRANSLATION_MISMATCH（翻译不一致）
**场景**：候选术语的翻译与已有术语不同

**示例**：
```
候选术语：foundry → 代工厂
已有术语：foundry → 晶圆代工厂（全局术语）
冲突类型：TRANSLATION_MISMATCH
```

#### 2. 作用域优先级
- **项目术语** > **全局术语**
- 如果项目中已有该术语，不会与全局术语冲突
- 如果只有全局术语，会检测冲突

### 冲突检测逻辑

```python
def detect(candidates, project_id):
    conflicts = []
    
    for candidate in candidates:
        # 1. 查找已有术语（大小写不敏感）
        existing_terms = find_existing_terms(candidate.original, project_id)
        
        if not existing_terms:
            continue  # 没有冲突
        
        # 2. 检查每个已有术语
        for term, metadata in existing_terms:
            # 忽略非激活术语
            if term.status != "active":
                continue
            
            # 3. 检查翻译是否一致
            if term.translation != candidate.suggested_translation:
                conflicts.append(TermConflict(
                    original=candidate.original,
                    existing_term_id=term.id,
                    existing_translation=term.translation,
                    existing_scope=metadata.scope,  # "global" or "project"
                    suggested_translation=candidate.suggested_translation,
                    context=candidate.context,
                    conflict_type=ConflictType.TRANSLATION_MISMATCH
                ))
    
    return conflicts
```

### 冲突结果
```python
@dataclass
class TermConflict:
    original: str                    # "foundry"
    existing_term_id: str            # "uuid-xxx"
    existing_translation: str        # "晶圆代工厂"
    existing_scope: str              # "global"
    suggested_translation: str       # "代工厂"
    context: str                     # "The foundry uses..."
    conflict_type: ConflictType      # TRANSLATION_MISMATCH
```

---

## 第三步：策略确定

### 自动推断策略

当前系统使用**简单规则**自动推断策略：

```python
def _add_term(candidate_data, translation, project_id):
    # 推断策略
    if candidate_data["original"] == translation:
        strategy = "KEEP"  # 原文和翻译相同 → 保留原文
    else:
        strategy = "TRANSLATE"  # 原文和翻译不同 → 标准翻译
```

### 策略推断规则

| 情况 | 推断策略 | 示例 |
|------|----------|------|
| 原文 == 翻译 | `KEEP` | GPU → GPU |
| 原文 != 翻译 | `TRANSLATE` | wafer → 晶圆 |

### 当前限制

⚠️ **当前系统不支持自动推断 `TRANSLATE_ANNOTATE` 和 `KEEP_ANNOTATE`**

这两种策略需要：
1. 手动在确认时指定
2. 或者在术语库中预先配置

### 手动指定策略

用户在确认时可以手动指定策略：

```python
# 前端 UI 示例
{
  "candidate_index": 0,
  "action": "ACCEPT",
  "final_translation": "台积电",
  "strategy": "TRANSLATE_ANNOTATE"  # 手动指定策略
}
```

---

## 第四步：用户确认

### 准备确认包

```python
from src.services.term_confirmation_service import TermConfirmationService

# 初始化服务
confirmation_service = TermConfirmationService(storage)

# 准备确认包
package_id = confirmation_service.prepare_confirmation(
    candidates=candidates,
    conflicts=conflicts,
    project_id=project_id
)
```

### 确认包内容

```python
@dataclass
class ConfirmationPackage:
    package_id: str                  # "uuid-xxx"
    project_id: str                  # "memory-mania"
    candidates: List[Dict]           # 候选术语列表
    conflicts: List[Dict]            # 冲突列表
    created_at: str                  # "2026-04-14T10:00:00"
    expires_at: str                  # "2026-04-15T10:00:00" (24小时后)
```

### 确认包存储位置

```
projects/{project_id}/artifacts/term-extraction/confirmations/{package_id}.json
```

### 用户决策选项

```python
class ConfirmationAction(Enum):
    ACCEPT = "accept"              # 接受建议翻译
    MODIFY = "modify"              # 修改翻译
    SKIP = "skip"                  # 跳过（本次不处理）
    USE_EXISTING = "use_existing"  # 使用已有术语
    REJECT = "reject"              # 拒绝（永久不添加）
```

### 决策示例

#### 场景 1：接受建议翻译
```json
{
  "candidate_index": 0,
  "action": "ACCEPT",
  "final_translation": "台积电"
}
```
**结果**：添加术语 `TSMC → 台积电`，策略自动推断为 `TRANSLATE`

---

#### 场景 2：修改翻译
```json
{
  "candidate_index": 1,
  "action": "MODIFY",
  "final_translation": "晶圆代工厂"
}
```
**结果**：添加术语 `foundry → 晶圆代工厂`，策略自动推断为 `TRANSLATE`

---

#### 场景 3：使用已有术语（解决冲突）
```json
{
  "candidate_index": 2,
  "action": "USE_EXISTING",
  "existing_term_id": "uuid-xxx"
}
```
**结果**：不添加新术语，使用已有的全局术语

---

#### 场景 4：跳过
```json
{
  "candidate_index": 3,
  "action": "SKIP"
}
```
**结果**：本次不处理，下次提取时可能再次出现

---

#### 场景 5：拒绝
```json
{
  "candidate_index": 4,
  "action": "REJECT"
}
```
**结果**：不添加术语，可以考虑加入黑名单（当前未实现）

---

## 第五步：应用决策

### 应用单个决策

```python
# 应用决策
confirmation_service.apply_decision(
    package_id=package_id,
    decision=decision,
    project_id=project_id
)
```

### 应用逻辑

#### ACCEPT / MODIFY
```python
def _apply_accept(candidate_data, decision, project_id):
    # 1. 生成术语 ID
    term_id = str(uuid.uuid4())
    
    # 2. 推断策略
    if candidate_data["original"] == decision.final_translation:
        strategy = "KEEP"
    else:
        strategy = "TRANSLATE"
    
    # 3. 创建 Term
    term = Term(
        id=term_id,
        original=candidate_data["original"],
        translation=decision.final_translation,
        strategy=strategy,
        status="active"
    )
    
    # 4. 创建 TermMetadata
    metadata = TermMetadata(
        term_id=term_id,
        scope="project",
        project_id=project_id,
        term_original=candidate_data["original"],
        term_translation=decision.final_translation,
        tags=[],
        source="extracted",  # 标记为提取来源
        usage_count=0
    )
    
    # 5. 添加到存储
    storage.add_term(term, metadata)
```

#### USE_EXISTING
不添加新术语，使用已有术语

#### SKIP / REJECT
不做任何操作

---

## 冲突处理流程

### 场景：候选术语与全局术语冲突

**情况**：
- 候选术语：`foundry → 代工厂`
- 全局术语：`foundry → 晶圆代工厂`

**用户选项**：

#### 选项 1：使用已有全局术语
```json
{
  "action": "USE_EXISTING",
  "existing_term_id": "global-term-id"
}
```
**结果**：不添加项目术语，使用全局术语 `foundry → 晶圆代工厂`

---

#### 选项 2：覆盖为项目术语
```json
{
  "action": "ACCEPT",
  "final_translation": "代工厂"
}
```
**结果**：添加项目术语 `foundry → 代工厂`，在该项目中覆盖全局术语

---

#### 选项 3：修改为一致
```json
{
  "action": "MODIFY",
  "final_translation": "晶圆代工厂"
}
```
**结果**：添加项目术语 `foundry → 晶圆代工厂`，与全局术语一致

---

## 完整流程示例

### 步骤 1：提取术语
```python
candidates = await extraction_service.extract_all("memory-mania")
# 结果：
# - TSMC → 台积电 (15次, 标题中)
# - foundry → 代工厂 (8次)
# - HBM → HBM (12次)
```

### 步骤 2：检测冲突
```python
conflicts = detector.detect(candidates, "memory-mania")
# 结果：
# - foundry: 候选"代工厂" vs 全局"晶圆代工厂"
```

### 步骤 3：准备确认包
```python
package_id = confirmation_service.prepare_confirmation(
    candidates, conflicts, "memory-mania"
)
# 结果：package_id = "uuid-abc123"
```

### 步骤 4：用户确认
```python
# 决策 1：接受 TSMC
decision1 = ConfirmationDecision(
    candidate_index=0,
    action=ConfirmationAction.ACCEPT,
    final_translation="台积电"
)
confirmation_service.apply_decision(package_id, decision1, "memory-mania")
# 添加：TSMC → 台积电 (TRANSLATE)

# 决策 2：修改 foundry
decision2 = ConfirmationDecision(
    candidate_index=1,
    action=ConfirmationAction.MODIFY,
    final_translation="晶圆代工厂"
)
confirmation_service.apply_decision(package_id, decision2, "memory-mania")
# 添加：foundry → 晶圆代工厂 (TRANSLATE)

# 决策 3：接受 HBM
decision3 = ConfirmationDecision(
    candidate_index=2,
    action=ConfirmationAction.ACCEPT,
    final_translation="HBM"
)
confirmation_service.apply_decision(package_id, decision3, "memory-mania")
# 添加：HBM → HBM (KEEP)
```

### 步骤 5：清理确认包
```python
confirmation_service.delete_confirmation_package(package_id, "memory-mania")
```

---

## 策略确定的改进建议

### 当前问题
⚠️ 策略推断过于简单，只能区分 `TRANSLATE` 和 `KEEP`

### 改进方案

#### 方案 1：基于规则的推断
```python
def infer_strategy(original, translation, context):
    # 规则 1：原文 == 翻译 → KEEP
    if original == translation:
        return "KEEP"
    
    # 规则 2：全大写缩写 + 有翻译 → KEEP_ANNOTATE
    if original.isupper() and len(original) <= 5 and translation != original:
        return "KEEP_ANNOTATE"
    
    # 规则 3：公司名（首字母大写）+ 有翻译 → TRANSLATE_ANNOTATE
    if original[0].isupper() and is_company_name(original):
        return "TRANSLATE_ANNOTATE"
    
    # 默认：TRANSLATE
    return "TRANSLATE"
```

#### 方案 2：LLM 推断策略
在提取时让 LLM 同时推荐策略：
```json
{
  "original": "TSMC",
  "translation": "台积电",
  "suggested_strategy": "TRANSLATE_ANNOTATE",
  "reason": "公司名称，首次需要标注英文"
}
```

#### 方案 3：用户手动选择
在确认 UI 中提供策略选择器：
```
术语：TSMC → 台积电
策略：[TRANSLATE] [KEEP] [TRANSLATE_ANNOTATE ✓] [KEEP_ANNOTATE]
```

---

## 常见问题

### Q1: 如何批量确认术语？
A: 当前需要逐个确认。可以考虑添加批量操作：
```python
decisions = [
    ConfirmationDecision(0, ConfirmationAction.ACCEPT, "台积电"),
    ConfirmationDecision(1, ConfirmationAction.ACCEPT, "晶圆"),
    ConfirmationDecision(2, ConfirmationAction.SKIP)
]
confirmation_service.apply_decisions_batch(package_id, decisions, project_id)
```

### Q2: 确认包过期后怎么办？
A: 确认包 24 小时后自动过期并删除。需要重新提取术语。

### Q3: 如何修改已添加的术语？
A: 使用术语管理 API：
```python
# 更新术语
storage.update_term(term, metadata, changes={"translation": "新翻译"})
```

### Q4: 冲突检测是否区分大小写？
A: 不区分。`TSMC` 和 `tsmc` 会被视为同一术语。

### Q5: 如何查看提取历史？
A: 提取结果保存在：
```
projects/{project_id}/artifacts/term-extraction/extractions/{timestamp}.json
```

---

## 相关文档

- `src/services/term_extraction_service.py` - 提取服务实现
- `src/services/term_conflict_detector.py` - 冲突检测实现
- `src/services/term_confirmation_service.py` - 确认服务实现
- `docs/TERMINOLOGY_STRATEGIES_GUIDE.md` - 策略详细说明

---

**最后更新**：2026-04-14  
**维护者**：Translation Agent Team
