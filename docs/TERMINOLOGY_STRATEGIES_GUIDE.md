# 术语翻译策略完整指南

**更新日期**：2026-04-14  
**适用系统**：新术语系统（Plan 5 迁移后）

---

## 概述

当前术语系统支持 **4 种翻译策略**，每种策略在翻译时有不同的表现方式。

---

## 策略类型详解

### 1. TRANSLATE（标准翻译）

**旧系统名称**：`translate`  
**新系统名称**：`TRANSLATE`

#### 说明
全文直接使用中文翻译，不保留原文，不添加注释。

#### 翻译表现
```
原文：The wafer is processed in the fab.
术语：wafer → 晶圆
译文：晶圆在晶圆厂中加工。
```

#### Prompt 格式
```markdown
**Standard Translations:**
- wafer → 晶圆
- node → 制程节点
- yield → 良率
```

#### 适用场景
- 常见技术术语
- 已被广泛接受的中文翻译
- 不需要保留原文的术语

#### 示例术语
- wafer → 晶圆
- node → 制程节点
- bandwidth → 带宽
- latency → 延迟

---

### 2. KEEP（保留原文）

**旧系统名称**：`preserve`  
**新系统名称**：`KEEP`

#### 说明
全文保持英文原文，不翻译，不加注释。

#### 翻译表现
```
原文：Apple Silicon uses HBM memory.
术语：Apple Silicon → Apple Silicon（保留）
      HBM → HBM（保留）
译文：Apple Silicon 使用 HBM 内存。
```

#### Prompt 格式
```markdown
**Preserve Original (Do Not Translate):**
- Apple Silicon, GPU, CPU, HBM, DRAM
```

#### 适用场景
- 专有品牌名称
- 行业标准缩写
- 翻译后会失去专业性的术语
- 中英文混用更自然的术语

#### 示例术语
- Apple Silicon（品牌名）
- GPU（标准缩写）
- CPU（标准缩写）
- HBM（技术缩写）
- AI（通用缩写）
- token（保留更专业）

---

### 3. TRANSLATE_ANNOTATE（翻译+首次标注）

**旧系统名称**：`first_annotate`  
**新系统名称**：`TRANSLATE_ANNOTATE`

#### 说明
首次出现时使用"中文翻译（英文原文）"格式，后续只用中文。

#### 翻译表现
```
原文：TSMC is the leading foundry. The foundry uses EUV.
术语：TSMC → 台积电
      foundry → 晶圆代工厂

首次出现：
译文：台积电（TSMC）是领先的晶圆代工厂（foundry）。

后续出现：
译文：该代工厂使用 EUV。
```

#### Prompt 格式
```markdown
**Translate with First-Occurrence Annotation:**
- TSMC → 台积电 [FIRST OCCURRENCE - ADD ANNOTATION]
- foundry → 晶圆代工厂 [FIRST OCCURRENCE - ADD ANNOTATION]
- NVIDIA → 英伟达
```

注：已出现过的术语不会有 `[FIRST OCCURRENCE]` 标记。

#### 适用场景
- 公司名称（需要中文但也要标注英文）
- 专业术语（首次需要解释）
- 读者可能不熟悉的概念

#### 示例术语
- TSMC → 台积电
- NVIDIA → 英伟达
- Intel → 英特尔
- foundry → 晶圆代工厂
- chiplet → 芯粒
- SoC → SoC（系统级芯片）

---

### 4. KEEP_ANNOTATE（保留+首次标注）

**旧系统名称**：`preserve_annotate`  
**新系统名称**：`KEEP_ANNOTATE`

#### 说明
首次出现时使用"英文原文（中文注释）"格式，后续只保留英文。

#### 翻译表现
```
原文：The transformer uses self-attention. Self-attention is key.
术语：transformer → Transformer
      self-attention → 自注意力机制

首次出现：
译文：Transformer（一种深度学习模型架构）使用 self-attention（自注意力机制）。

后续出现：
译文：Self-attention 是关键。
```

#### Prompt 格式
```markdown
**Preserve with Annotation:**
- transformer (add annotation: 一种深度学习模型架构)
- self-attention (add annotation: 自注意力机制)
```

#### 适用场景
- 保留原文更专业，但首次需要解释
- 技术概念（英文是标准术语）
- 算法或模型名称

#### 示例术语
- transformer（一种深度学习模型架构）
- RLHF（基于人类反馈的强化学习）
- Moore's Law（摩尔定律）

---

## 策略映射表

| 旧系统 | 新系统 | 首次出现 | 后续出现 | 是否翻译 |
|--------|--------|----------|----------|----------|
| `translate` | `TRANSLATE` | 中文 | 中文 | ✅ |
| `preserve` | `KEEP` | 英文 | 英文 | ❌ |
| `first_annotate` | `TRANSLATE_ANNOTATE` | 中文（英文） | 中文 | ✅ |
| `preserve_annotate` | `KEEP_ANNOTATE` | 英文（中文） | 英文 | ❌ |

---

## 完整示例

### 原文
```
Apple Silicon uses TSMC's 3nm node. The foundry achieved 95% yield 
using EUV lithography. This transformer model requires HBM memory 
for training. The self-attention mechanism is key.
```

### 术语配置
```json
{
  "Apple Silicon": {"strategy": "KEEP"},
  "TSMC": {"strategy": "TRANSLATE_ANNOTATE", "translation": "台积电"},
  "node": {"strategy": "TRANSLATE", "translation": "制程节点"},
  "foundry": {"strategy": "TRANSLATE_ANNOTATE", "translation": "晶圆代工厂"},
  "yield": {"strategy": "TRANSLATE", "translation": "良率"},
  "EUV": {"strategy": "KEEP"},
  "transformer": {"strategy": "KEEP_ANNOTATE", "translation": "一种深度学习模型架构"},
  "HBM": {"strategy": "KEEP"},
  "self-attention": {"strategy": "KEEP_ANNOTATE", "translation": "自注意力机制"}
}
```

### 译文（首次出现）
```
Apple Silicon 使用台积电（TSMC）的 3nm 制程节点。该晶圆代工厂（foundry）
使用 EUV 光刻实现了 95% 的良率。这个 Transformer（一种深度学习模型架构）
模型需要 HBM 内存进行训练。Self-attention（自注意力机制）机制是关键。
```

### 译文（后续出现）
```
该代工厂继续使用 EUV 技术。Transformer 模型的 self-attention 层
需要更多 HBM 容量。
```

---

## 策略选择指南

### 何时使用 TRANSLATE
- ✅ 有标准中文翻译
- ✅ 读者熟悉中文术语
- ✅ 翻译不会造成歧义

### 何时使用 KEEP
- ✅ 品牌名称（Apple Silicon）
- ✅ 标准缩写（GPU, CPU, AI）
- ✅ 保留英文更专业
- ✅ 中文翻译会失去精确性

### 何时使用 TRANSLATE_ANNOTATE
- ✅ 公司名称（需要中文）
- ✅ 专业术语（首次需解释）
- ✅ 后续使用中文更自然

### 何时使用 KEEP_ANNOTATE
- ✅ 技术概念（英文是标准）
- ✅ 算法名称（保留英文）
- ✅ 首次需要解释含义

---

## 首次出现跟踪

系统会自动跟踪每个术语在翻译会话中的首次出现：

```python
# 会话开始
session_id = "translation-session-001"

# 第一段翻译
terms_used = ["TSMC", "foundry"]
service.mark_terms_used(session_id, terms_used)

# 第二段翻译
# TSMC 和 foundry 不再标记为 [FIRST OCCURRENCE]
# 新术语会被标记
```

---

## 在 Prompt 中的完整格式

```markdown
## Terminology Constraints

**Standard Translations:**
- wafer → 晶圆
- node → 制程节点
- bandwidth → 带宽

**Preserve Original (Do Not Translate):**
- Apple Silicon, GPU, CPU, HBM, DRAM, AI

**Translate with First-Occurrence Annotation:**
- TSMC → 台积电 [FIRST OCCURRENCE - ADD ANNOTATION]
- foundry → 晶圆代工厂 [FIRST OCCURRENCE - ADD ANNOTATION]
- NVIDIA → 英伟达
- Intel → 英特尔

**Preserve with Annotation:**
- transformer (add annotation: 一种深度学习模型架构)
- self-attention (add annotation: 自注意力机制)
- RLHF (add annotation: 基于人类反馈的强化学习)
```

---

## 技术实现

### 策略定义位置
- **旧系统**：`src/core/models/enums.py` - `TranslationStrategy` 枚举
- **新系统**：`src/models/terminology.py` - `Term.strategy` 字符串字段
- **迁移映射**：`scripts/migrate_terminology.py` - `_map_strategy()` 方法

### 策略应用位置
- **Prompt 构建**：`src/services/term_injection_service.py`
- **首次跟踪**：`TermInjectionService.first_occurrence_tracker`
- **旧系统应用**：`src/core/glossary.py` - `apply_strategy()` 方法

---

## 常见问题

### Q: 如何修改术语的策略？
A: 通过 API 或直接编辑术语表 JSON 文件中的 `strategy` 字段。

### Q: 首次出现跟踪在哪里重置？
A: 每个翻译会话（session）独立跟踪，会话结束后自动清理。

### Q: 可以混合使用多种策略吗？
A: 可以，每个术语独立设置策略，系统会按策略分组处理。

### Q: 如果不设置策略会怎样？
A: 默认使用 `TRANSLATE` 策略。

### Q: 策略可以动态改变吗？
A: 可以，但需要更新术语表并重新加载。建议在翻译前确定策略。

---

## 相关文档

- `src/services/term_injection_service.py` - 策略实现
- `src/models/terminology.py` - 术语模型
- `docs/migration-mapping.md` - 策略迁移映射
- `src/core/glossary.py` - 旧系统策略应用

---

**最后更新**：2026-04-14  
**维护者**：Translation Agent Team
