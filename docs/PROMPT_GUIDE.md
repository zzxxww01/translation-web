# 长文翻译系统技术手册

更新时间：2026-03-12

本文档覆盖长文翻译的三大核心子系统：**Prompt 链路**、**术语库**、**学习链路**，以及各环节的模型配置。

---

# 一、业务链路总览

## 1.1 三条翻译链路

| 简称 | 入口 | 说明 |
|---|---|---|
| **链路 A** | `POST /api/projects/{id}/translate-stream` | 文档页普通全篇翻译。逐段调用 `TranslationAgent`，**不做**全文分析、section role 分析、术语预扫描。上下文最少（仅术语表 + 前后文 + 学习规则）。 |
| **链路 B** | `POST /api/projects/{id}/translate-four-step` | 文档页四步法全篇翻译。先做全文分析 + section role 分析，再逐 section 执行 prescan → draft → critique → revision。上下文最完整。 |
| **链路 C** | `POST /api/projects/{id}/translate-all` | 确认流项目级翻译。先做全文分析 + section role 分析 + prescan，然后按 section 批量翻译（`section_batch_translate`）。不走段落级 prompt builder，走独立模板。 |

## 1.2 模型配置

### 设计原则

模型分配在代码中**固定写死**，不暴露给前端用户选择。前端 UI 和 API 请求体中**没有** model 参数。

- **核心翻译和分析任务** → preview（最强模型）
- **轻量辅助任务**（术语预扫描、规则提取） → flash（快速低成本）
- **降级场景**（preview 触发限制时） → 自动降级到 backup 模型

### 全局模型设置（`.env`）

```
GEMINI_FLASH_MODEL=gemini-flash-latest        # 轻量模型
GEMINI_PRO_MODEL=gemini-3-pro-preview          # 标准模型
GEMINI_PREVIEW_MODEL=gemini-3.1-pro-preview    # 最强模型
GEMINI_MODEL=preview                           # 默认使用的模型别名
GEMINI_BACKUP_MODEL=pro                        # 触发限制时的降级模型
```

### 各 Prompt 模型分配

| Prompt | 模型 | Temperature | 改模型改哪里 |
|---|---|---|---|
| #1 全文分析 | preview | 0.7 | 跟随 `.env` `GEMINI_MODEL`（默认模型），或在 `deep_analyzer.py` 调用 `generate()` 时加 `model="flash"` |
| #2 section 角色分析 | preview | 0.7 | 同 #1 |
| #3 文章标题翻译 | preview | 0.3 | 跟随默认模型，或在 `gemini.py` `translate_title()` 内部调 `generate()` 时加 `model=` |
| #4 章节标题翻译 | preview | 0.3 | 同 #3，对应方法 `translate_section_title()` |
| #5 术语预扫描 | **flash** | 0.3 | `base.py` `prescan_section_with_flash()` → 改 `model="flash"` 参数 |
| #6 段落翻译 | preview | 0.5 | 跟随默认模型，或在 `gemini.py` `translate()` 内部调 `generate()` 时加 `model=` |
| #7 section 批量翻译 | preview | 0.5 | 跟随默认模型，或在 `gemini.py` `translate_section()` 内部调 `generate()` 时加 `model=` |
| #8 段落重译 | preview | 0.4 | 跟随默认模型，或在 `gemini.py` `retranslate()` 内部调 `generate()` 时加 `model=` |
| #9 四步法 critique | preview | 0.7 | 跟随默认模型，或在 `base.py` `reflect_on_translation()` 调 `generate()` 时加 `model=` |
| #10 四步法 revision | preview | 0.3 | 同 #9，对应方法 `refine_translation()` |
| #11-#13 规则提取 | **flash** | 0.3 | `memory_service.py` → `create_llm_provider(model_type="flash")`，改 `model_type=` |
| #14 规则库梳理 | **flash** | 0.3 | 同 #11（复用同一个 Flash 实例） |

### 模型决定的两条路径

1. **默认模型**（#1-#4, #6-#10）：由 `.env` 的 `GEMINI_MODEL=preview` 决定。`GeminiProvider` 构造时读取该值作为 `self.model_name`，所有不传 `model` 参数的 `generate()` 调用都走这个默认值。**改全局默认：只改 `.env`。改单个 prompt：在对应方法调 `generate()` 时传 `model="flash"` / `"pro"` / `"preview"`。**

2. **独立 Flash 实例**（#11-#14）：`memory_service.py` 通过 `create_llm_provider(model_type="flash")` 创建一个独立的 Flash Provider 实例，与主翻译 Provider 互不影响。改模型只需改 `model_type=` 参数。

### 降级逻辑

`gemini.py` → `_build_attempt_plan()` 自动构建 attempt 列表：primary model × 所有 API key → backup model × 所有 API key。当 primary 触发限制时自动降级到 backup。

---

# 二、术语库系统

## 2.1 术语数据模型

| 模型 | 文件 | 用途 |
|---|---|---|
| `GlossaryTerm` | `core/models/glossary.py` | 持久化术语条目（original / translation / strategy / note[前端显示为“词义说明”] / scope / source / status） |
| `Glossary` | `core/models/glossary.py` | 术语表容器（`List[GlossaryTerm]`），支持 `get_term()` / `add_term()` |
| `EnhancedTerm` | `core/models/analysis.py` | LLM 分析产出的术语（term / context_meaning / translation / strategy / first_occurrence_note / rationale） |
| `PrescanTerm` | `core/models/memory.py` | Flash 预扫描发现的术语（term / suggested_translation / context / confidence） |
| `TermConflict` | `core/models/memory.py` | 术语冲突（已有翻译 vs 新翻译，含上下文和词义说明） |
| `TerminologyVersion` | `core/models/memory.py` | 运行时术语版本管理（含冲突检测和解决） |

### 翻译策略（`TranslationStrategy`）

| 策略 | 说明 | 示例 |
|---|---|---|
| `preserve` | 保留英文原文 | TSMC |
| `first_annotate` | 首次出现加中文注释，后续直接使用 | CoWoS（台积电先进封装技术） |
| `translate` | 直接翻译为中文 | wafer → 晶圆 |

## 2.2 术语存储结构

```
project_root/
├── glossary/                               # 全局术语表
│   └── global_glossary_semi.json           # 全局术语（scope=global）
├── projects/{project_id}/
│   ├── glossary.json                      # 项目级术语（scope=project，覆盖全局）
│   └── artifacts/
│       ├── runs/{run_id}/analysis.json    # 全文分析产出的术语快照
│       └── term-review/latest.json        # 术语审阅工作区
```

## 2.3 术语加载与合并

**入口：** `GlossaryManager.load_merged(project_id)` → `core/glossary.py`

```
全局术语表（glossary/global_glossary_semi.json）
    ↓ 加载
项目术语表 (projects/{project_id}/glossary.json)
    ↓ 合并（项目覆盖全局，case-insensitive）
merged_glossary
    ↓ 在链路 B/C 中进一步与全文分析术语合并
batch_translation_service._merge_analysis_with_project_glossary()
    ↓ 合并结果：analysis 术语优先，项目术语覆盖 analysis 同名项
最终术语表
```

**合并优先级：** 项目手动术语 > 全文分析术语 > 全局术语

## 2.4 术语匹配（TermMatcher）

**文件：** `core/term_matcher.py`

当前真正用于 prompt 注入的统一入口是：
- `src/core/glossary_prompt.py` → `select_glossary_terms_for_text()`
- `src/core/glossary_prompt.py` → `render_glossary_prompt_block()`

它内部仍然复用 `TermMatcher.match_paragraph()` 做排序，但在进入 prompt 前会再做一次“真实出现校验”：
1. 只保留当前待翻译文本里实际命中的术语
2. 英文/缩写术语按词边界校验，避免 `AI` 这类短词误命中普通单词片段
3. 统一按 `MAX_GLOSSARY_TERMS_IN_PROMPT = 15` 截断

`TermMatcher` 自身的匹配逻辑仍然是：

1. **精确匹配**（score 1.0-1.5）：术语原文在段落中出现，出现次数越多分越高，短术语（<5 字符）打折
2. **部分匹配**（score ≤ 0.7）：多词术语的部分词汇匹配
3. 按分数排序取 top 20，过滤 min_score < 0.3

**链路 A** 通过 `select_glossary_terms_for_text()` 注入术语；**链路 B/C** 通过 `LayeredContextManager._get_relevant_terms()` 做段落级过滤，并同样受 `MAX_GLOSSARY_TERMS_IN_PROMPT = 15` 限制。

## 2.5 术语预扫描（Prescan）

**Prompt：** `section_prescan.v2.txt`（#5），使用 Flash 模型

**触发：** 链路 B（四步法 Phase 1）和链路 C（确认流），逐 section 调用

**流程：**
1. 将 section 原文 + 已有术语表发给 Flash
2. Flash 返回 `new_terms`（新发现的术语）+ `term_usages`（已有术语的实际用法）
3. `context_manager.add_terms_from_prescan()` 合入运行时术语版本
4. 如果新术语与已有术语翻译冲突 → 生成 `TermConflict`

**链路 B 的实时冲突处理：** 四步法全篇翻译会把 `TermConflict` 通过 SSE 发给前端。payload 除了已有译法和新译法，还会带 `existing_note / new_note` 作为“词义说明”，以及 `existing_context / new_context` 作为“上下文”。

## 2.6 术语审阅服务

**文件：** `services/terminology_review_service.py`

独立的术语审阅流程，不在翻译链路中，由前端主动触发：

1. **prepare_review**：对所有 section 做 prescan，聚合候选术语，检测冲突/相似/高频术语 → 输出到 `artifacts/term-review/latest.json`
2. **apply_review**：用户在前端逐条决策（accept / skip / custom）→ 写入项目术语表
3. **promote_project_term**：将项目级术语提升为全局术语（`scope=global, source=promoted_from_project`）
4. **get_project_recommendations**：找出高频项目术语推荐提升为全局

**前端显示约定：** 相似术语推荐和推荐提升卡片里，如果术语带 `note`，会显示为“词义说明”。

---

# 三、学习链路（翻译规则自学习）

## 3.1 概述

学习链路从三种来源自动提取可复用翻译规则，存储为自然语言 markdown 条目，在后续翻译时注入 prompt。

**规则格式示例：**
```
- "wafer" 翻译为 "晶圆"，不要译为 "硅片"
- 避免 "进行了……" 句式，改用直接动词
- "CoWoS" 首次出现时加注释，后续直接使用
```

## 3.2 规则提取来源

| 来源 | Prompt | 触发条件 | 调用方 |
|---|---|---|---|
| 用户手动修改译文 | #11 `correction_rule_extraction.v2` | diff ≥ 5% | `projects_paragraphs.py` / `confirmation_service.py` |
| 四步法 critique 发现问题 | #12 `reflection_rule_extraction.v2` | critique score < 8.0 且有 issues | `four_step_translator.py` |
| 用户重译时给了指令 | #13 `retranslation_rule_extraction.v2` | 有 instruction 且 diff ≥ 5% | `confirmation_translation.py` |

所有提取均为 **fire-and-forget 异步**（`asyncio.create_task`），不阻塞主请求。

## 3.3 规则存储

- **项目级：** `data/memory/{project_id}.md`
- **全局：** `data/global_memory.md`
- **格式：** 纯 markdown bullet list，每行一条规则
- **去重：** 追加前做精确字符串匹配，跳过已存在的规则

## 3.4 规则注入翻译 prompt

`memory_service.get_rules_for_prompt(project_id)` → 读取规则列表 → 截断（上限 15 条 / 600 字符） → 通过 `prompt_builder._build_rules_section()` 拼入 `## 已学习的翻译规则` 区块（见 6.3.3）。

## 3.5 自动梳理

每次成功提取规则后，以 **5% 概率**触发 `rules_consolidation.v2`（#14）：
- **前置条件：** 规则库 ≥ 8 条
- **操作：** LLM 审查整个规则库，合并重复、解决矛盾、删除模糊规则、控制总量 ≤ 30
- **执行方式：** `asyncio.create_task`，异步非阻塞
- **结果：** 梳理后的规则直接替换原 `.md` 文件

## 3.6 管理 API

| 端点 | 方法 | 说明 |
|---|---|---|
| `/{project_id}/translation-rules` | GET | 查看所有规则 |
| `/{project_id}/translation-rules/{index}` | DELETE | 按索引删除规则 |

---

# 四、Prompt 参考

## 分析阶段（Phase 0）

### 1. article_analysis.v2.txt — 全文分析

**文件：** `src/prompts/longform/analysis/article_analysis.v2.txt`

**语言：** 英文（输出英文 JSON） · **模型：** preview · **链路：** B / C

**调用点：** `deep_analyzer.py` → `base.py`

**输入占位符：**
- `{sections_outline}` — 文章各 section 的大纲
- `{text}` — 原文采样片段

**7 步任务：**
1. 一句话核心主题
2. 3-6 个论证要点
3. 文章结构描述
4. 关键术语提取（精选，不罗列常见词）
5. 原文风格 + 中文译文语体定调
6. 翻译风险点
7. 4-7 条具体翻译指南

**输出 JSON 字段：**
| 字段 | 类型 | 说明 |
|---|---|---|
| `theme` | string | 核心主题 |
| `key_arguments` | string[] | 论证要点 |
| `structure_summary` | string | 结构描述 |
| `terminology` | object[] | 术语表（term / context_meaning / translation / strategy / first_occurrence_note / rationale） |
| `style` | object | 风格（tone / target_audience / translation_voice） |
| `challenges` | object[] | 翻译风险（location / issue / suggestion） |
| `guidelines` | string[] | 翻译指南 |

**术语 strategy：** `preserve`（保留英文）/ `first_annotate`（首次加注）/ `translate`（直接翻译）

**修改记录：**
- 2026-03-11：角色加"硬核科技长文"；删除 `data_density` 字段（无下游消费）

---

### 2. section_role_map.v2.txt — section 角色分析

**文件：** `src/prompts/longform/analysis/section_role_map.v2.txt`

**语言：** 英文（输出英文 JSON） · **模型：** preview · **链路：** B / C

**调用点：** `deep_analyzer.py`

**输入占位符：**
- `{article_theme}` — 来自全文分析
- `{structure_summary}` — 来自全文分析
- `{sections_summary}` — 各 section 的摘要文本

**输出 JSON 字段（每个 section）：**
| 字段 | 说明 |
|---|---|
| `role_in_article` | 在全文论证中的角色 |
| `relation_to_previous` | 与上一个 section 的逻辑关系 |
| `relation_to_next` | 对下一个 section 的铺垫 |
| `key_points` | 不可弱化的核心论点 |
| `translation_notes` | 操作性翻译提示 |

**修改记录：**
- 2026-03-11：角色改为通用定位；删除 `data-density handling`

---

## 辅助翻译（Phase 0 后段）

### 3. title_translate.v2.txt — 文章标题 + 副标题翻译

**文件：** `src/prompts/longform/auxiliary/title_translate.v2.txt`

**语言：** 中文 · **模型：** preview · **链路：** B / C

**调用点：** `batch_translation_service.py` → `gemini.py` (`translate_title`)

**输入占位符：** `{context_block}` / `{title}` / `{subtitle}`

**输出格式：** `标题: <中文标题>\n副标题: <中文副标题>`

**修改记录：**
- 2026-03-11：合并原 `metadata_subtitle_translate.v2.txt`，减少一次 API 调用

---

### 4. section_title_translate.v2.txt — 章节标题翻译

**文件：** `src/prompts/longform/auxiliary/section_title_translate.v2.txt`

**语言：** 中文 · **模型：** preview · **链路：** B / C

**调用点：** `batch_translation_service.py` → `gemini.py` (`translate_section_title`)

**输入占位符：** `{context_block}` / `{title}`

**输出：** 纯中文章节标题。每个 section 单独调用，上下文含前后 section 标题。

---

## 术语阶段（Phase 1）

### 5. section_prescan.v2.txt — 术语预扫描

**文件：** `src/prompts/longform/terminology/section_prescan.v2.txt`

**语言：** 英文（输出英文 JSON） · **模型：** flash · **链路：** B / C

**调用点：** `four_step_translator.py` → `gemini.py` (`prescan_section_with_flash`)

**输入占位符：** `{section_id}` / `{section_title}` / `{existing_terms}` / `{section_content}`

**输出 JSON：** `new_terms`（新术语列表）+ `term_usages`（已有术语用法映射）

**规则要点：** 精选 3-8 个强术语，不列通用英文词

---

## 翻译阶段（Phase 2）

### 6. paragraph_translate.v2.txt + prompt_builder.py — 段落翻译（核心）

**模板文件：** `src/prompts/longform/translation/paragraph_translate.v2.txt`
**拼装代码：** `src/prompts/prompt_builder.py`

**语言：** 中文 · **模型：** preview · **链路：** A（逐段翻译）/ B（四步法 draft）

**调用点：** `gemini.py` (`_build_translation_prompt`) → `prompt_builder.py` (`build_prompt`)

#### 6.1 翻译配置来源

`prompt_style` 由 `.env` 的 `TRANSLATION_PROMPT_STYLE` 决定（`config.py` → `settings.translation_prompt_style`）：

| .env 值 | builder profile | 注入 `{translation_profile_instructions}` 的内容 |
|---|---|---|
| `original`（默认） | `standard` | 保留密集推理和细腻判断，必要时用更完整的表述 |
| `simplified` | `lean` | 保留所有事实和逻辑，但优先使用更紧凑的中文表达 |

#### 6.2 模板静态骨架

```
角色设定（资深中英双语编辑，硬核科技长文）
翻译配置（{translation_profile_instructions}）
不可违反的原则（准确性 / 意思优先 / 分析师语气 / 只输出中文）
{dynamic_sections}
原文（{text}）
输出规则（禁 Markdown、格式 token 保护规则）
```

#### 6.3 动态区块详细生成逻辑

`{dynamic_sections}` 由 `_build_dynamic_sections()` 按以下顺序依次拼接（每个区块仅在有数据时才注入）：

##### 6.3.1 隐藏格式 Token（`_build_format_token_section`）
- **触发场景：** 段落含有行内格式（链接、粗体、斜体、行内代码）时。纯文本段落不触发。
- **数据来源：** `paragraph.inline_elements` → `format_token_context()` → `context["format_tokens"]`
- **生成内容：** 5 条 token 操作规则 + 本段 token 列表（最多 6 个，格式：`LINK_1 (link): 原文文本`）

##### 6.3.2 术语表（`_build_glossary_section`）
- **触发场景：**
  - **链路 A：** `select_glossary_terms_for_text()` 从项目+全局合并术语表里只选当前段落命中的条目。
  - **链路 B / C：** `LayeredContextManager._get_relevant_terms()` 从全文分析术语 + prescan + 项目术语覆盖结果中，只保留当前段落命中的条目。
- **数据来源：** `context["glossary"]`
- **生成内容：** 最多 15 个术语，统一格式为 `原文 / 标准写法 / 要求 / 词义`：
  - `preserve` → `原文：HBM；标准写法：HBM；要求：保留英文原文`
  - `first_annotate` → `原文：TSMC；标准写法：台积电；要求：首次出现写“台积电（TSMC）”，后文写“台积电”`
  - 有 `note` → `原文：wafer；标准写法：晶圆；要求：直接使用该写法；词义：这里指芯片制造中的硅片基底`
  - 其他 → `原文：chiplet；标准写法：小芯片；要求：直接使用该写法`

##### 6.3.3 已学习的翻译规则（`_build_rules_section`）
- **触发场景：** 项目有历史翻译规则时触发。新项目不触发。
- **数据来源：** `memory_service.get_rules_for_prompt(project_id)` → `context["learned_rules"]`（`List[str]`）
- **存储位置：** `data/memory/{project_id}.md`
- **生成内容：** 最多 15 条 / 600 字符，自然语言规则原样输出到 `## 已学习的翻译规则`

##### 6.3.4 额外翻译指令 / 修订任务（`_build_instruction_section`）
- **"额外翻译指令"分支**（有 instruction，无旧译文）：首次翻译时用户附带额外指令（少见）。
- **"修订任务"分支**（有旧译文）：用户对已有译文重新翻译。
- **不触发：** 首次全文翻译、四步法 draft（无 instruction 也无旧译文）。
- 仅在 `include_revision_task=True` 时检查。

##### 6.3.5 上下文（`_build_context_section` 第一部分）
- **链路 A：** 通常不触发（不传 `article_title`/`article_theme`）。
- **链路 B / C：** 从全文分析注入，总是触发。
- **内容：** 文章标题、主题、当前章节、标题链、目标读者

##### 6.3.6 结构说明（第二部分）
- 链路 A 不触发；B / C 总是触发。
- 来源：全文分析的 `structure_summary`

##### 6.3.7 章节角色（第三部分）
- 仅 B / C 触发（需要 section role 分析结果）。
- 内容：角色、与上一章节关系、核心论点、翻译注意事项。
- 当前统一限额：核心论点最多 4 条，翻译注意事项最多 4 条。

##### 6.3.8 风格约束（第四部分）
- B / C 总是触发（`style.translation_voice`）；A 不触发。
- 当前统一限额：附加 style notes 最多 4 条。

##### 6.3.9 翻译风险（第五部分）
- 仅 B / C 触发（全文分析 `challenges`）。
- 当前统一限额：高风险挑战最多 4 条。

##### 6.3.10 前文已确认译文（第六部分）
- **链路 A / B：** 当前段落不是 section 第一段时触发。C 不走此区块。
- 取最近 **1 段**，按句子截断（上限 120 字符）。

##### 6.3.11 下文预览（第七部分）
- **链路 A / B：** 当前段落不是 section 最后一段时触发。C 不走此区块。
- 取 **1 段**，按句子截断（上限 160 字符）。

**截断规则（`_truncate_by_sentence`）：** 超限时按句末标点切分，固定保留最后一句，从第一句开始向后累加，中间用 ` …… ` 连接。

**修改记录：**
- 2026-03-12：模板英文转中文；builder 动态区块全部中文化；句子截断；`prompt_style` 改为 config 读取

---

### 7. section_batch_translate.v2.txt — 确认流批量翻译

**文件：** `src/prompts/longform/translation/section_batch_translate.v2.txt`

**语言：** 中文（JSON key 英文，translation 值中文） · **模型：** preview · **链路：** 仅 C

**调用点：** `gemini.py` (`translate_section`)

**输入占位符：**

| 占位符 | 来源 |
|---|---|
| `{section_title}` / `{section_position}` | section 信息 |
| `{previous_section}` / `{next_section}` | 前后 section 标题 |
| `{target_audience}` / `{translation_voice}` | 全文分析 style |
| `{article_theme}` / `{article_challenges}` | 全文分析 |
| `{glossary}` / `{guidelines}` | 合并术语表 / 翻译指南 |
| `{section_text}` / `{paragraph_ids}` | 带 `[p001]` 标记的段落原文 |

**输出 JSON：** `{"translations": [{"id": "p001", "translation": "中文译文"}]}`

**与 #6 的区别：** #6 逐段、走 builder 动态拼装；#7 整 section 一次发、上下文写在模板占位符里。

**当前统一预算：** section batch translate 现在和段落级 prompt 共用同一组上下文裁剪规则，定义在：
- `src/core/constants.py`
- `src/core/longform_context.py`

其中术语、guidelines、translation notes、article challenges 都会先经过统一裁剪，再进入 `gemini.py` 的 `section_batch_translate` prompt。

---

### 8. paragraph_retranslate.v2.txt — 段落重译

**文件：** `src/prompts/longform/translation/paragraph_retranslate.v2.txt`

**语言：** 中文 · **模型：** preview · **链路：** A / B / C（用户手动触发）

**调用点：** `prompt_builder.py` (`build_retranslation_prompt`) → `gemini.py` (`retranslate`)

**输入占位符：** `{source}` / `{current}` / `{instruction}` / `{dynamic_sections}`

**与 #6 的关系：** #6 用于首次翻译（无旧译文）；#8 用于重译（有旧译文 + 修订要求）。两者共享 builder 动态区块。

---

## 审校阶段（Phase 3）

### 9. section_critique.v2.txt — 四步法 critique

**文件：** `src/prompts/longform/review/section_critique.v2.txt`

**语言：** 英文（输出英文 JSON） · **模型：** preview · **链路：** 仅 B

**调用点：** `four_step_translator.py` (`reflect_on_translation`)

**输入占位符：** `{pairs_text}` / `{guidelines_text}` / `{terms_text}`

**审校优先级：** 准确性 > 分析师力度 > 术语一致 > 翻译腔 > 可读性 > 段落衔接

**输出 JSON：** `overall_score` / `readability_score` / `accuracy_score` / `is_excellent` / `issues[]`

**下游：** `is_excellent=true` → 跳过 revision；`false` → 进入 #10；issues 同时触发学习链路 #12。

---

### 10. paragraph_revision.v2.txt — 四步法 revision

**文件：** `src/prompts/longform/review/paragraph_revision.v2.txt`

**语言：** 中文 · **模型：** preview · **链路：** 仅 B

**调用点：** `four_step_translator.py` (`refine_translation`)

**输入占位符：** `{source}` / `{current_translation}` / `{issue_type}` / `{description}` / `{suggestion}`

**触发条件：** critique 返回 `is_excellent=false` 且有 issues。

**规则：** 只修复指定问题，不重写无关部分，无 `{dynamic_sections}`。

---

## 学习阶段

### 11. correction_rule_extraction.v2.txt — 人工纠错规则提取

**文件：** `src/prompts/longform/learning/correction_rule_extraction.v2.txt`

**语言：** 英文（输出中文 bullet list） · **模型：** flash

**调用点：** `memory_service.py` → `process_correction()`

**前置条件：** diff ≥ 5%

**输入占位符：** `{source}` / `{ai_translation}` / `{user_translation}`

**输出：** 最多 5 条规则 bullet list，或 `NONE`

**触发场景：**
- 文档页段落编辑 → `projects_paragraphs.py`
- 确认流段落确认 → `confirmation_service.py`

---

### 12. reflection_rule_extraction.v2.txt — 审校规则提取

**文件：** `src/prompts/longform/learning/reflection_rule_extraction.v2.txt`

**语言：** 英文（输出中文 bullet list） · **模型：** flash

**调用点：** `memory_service.py` → `process_reflection_issues()`

**输入占位符：** `{issues_text}` / `{translations_text}`

**输出：** 最多 5 条规则 bullet list，或 `NONE`

**触发场景：** 链路 B，critique score < 8.0 且有 issues。

---

### 13. retranslation_rule_extraction.v2.txt — 重译偏好提取

**文件：** `src/prompts/longform/learning/retranslation_rule_extraction.v2.txt`

**语言：** 英文（输出中文 bullet list） · **模型：** flash

**调用点：** `memory_service.py` → `process_retranslation_instruction()`

**前置条件：** diff ≥ 5%

**输入占位符：** `{instruction}` / `{source}` / `{before}` / `{after}`

**输出：** 最多 3 条规则 bullet list，或 `NONE`

**触发场景：** 确认流重译，用户提供了 instruction。

---

### 14. rules_consolidation.v2.txt — 规则库梳理

**文件：** `src/prompts/longform/learning/rules_consolidation.v2.txt`

**语言：** 英文（输出中文 bullet list） · **模型：** flash

**调用点：** `memory_service.py` → `_maybe_consolidate()` → `_consolidate_rules()`

**触发条件：** 规则 ≥ 8 条时，每次提取后 5% 概率自动触发。

**输入占位符：** `{rules_text}`（当前规则库完整内容）

**任务：** 合并重复、解决矛盾、删除模糊规则、控制总量 ≤ 30。

**输出：** 梳理后的完整 bullet list，直接替换原规则库。

---

# 五、各链路 Prompt 调用顺序速查

## 链路 A（文档页普通翻译）

```
逐段循环:
  └─ #6 paragraph_translate（preview）
```

## 链路 B（四步法翻译）

```
Phase 0:
  ├─ #1 article_analysis（preview）
  ├─ #2 section_role_map（preview）
  ├─ #3 title_translate（preview）
  └─ #4 section_title_translate × N（preview）

逐 section 循环:
  Phase 1:  #5 section_prescan（flash）
  Phase 2:  #6 paragraph_translate × N（preview）
  Phase 3:  #9 section_critique（preview）
  Phase 4:  #10 paragraph_revision × issues（preview，仅 is_excellent=false 时）

后台异步:
  └─ #12 reflection_rule_extraction（flash，critique 有 issues 时）
```

## 链路 C（确认流批量翻译）

```
Phase 0:
  ├─ #1 article_analysis（preview）
  ├─ #2 section_role_map（preview）
  ├─ #3 title_translate（preview）
  └─ #4 section_title_translate × N（preview）

逐 section 循环:
  Phase 1:  #5 section_prescan（flash）
  Phase 2:  #7 section_batch_translate（preview）
```

## 用户手动触发

```
段落重译:  #8 paragraph_retranslate（preview）
  └─ 后台异步: #13 retranslation_rule_extraction（flash，有 instruction 时）

段落编辑确认:
  └─ 后台异步: #11 correction_rule_extraction（flash，diff ≥ 5% 时）

规则库梳理:
  └─ 后台异步: #14 rules_consolidation（flash，5% 概率）
```

