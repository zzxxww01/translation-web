# 格式处理链路说明

更新时间：2026-03-11

这份文档说明当前代码如何处理“从 HTML 导入，到英文 Markdown 归一化、分段翻译，再到中文 Markdown 导出”的格式问题。重点不是泛泛描述流程，而是说明现在的实现怎样避免链接、加粗、斜体、行内代码、标题层级、列表和引用在翻译过程中被破坏。

## 先看结论

当前实现有四个核心约束：

1. `source.md` 是导出的唯一骨架来源，不再直接从 HTML 导出中文。
2. UI 里的 `Paragraph` 只是“工作分段”，不是最终导出块；多个段落可能共享同一个父 block。
3. 行内格式不是直接交给 LLM 保管，而是先转成隐藏 token，再在导出时恢复成 Markdown。
4. 中文导出是严格校验的：只要某个格式化 block 无法安全重建，就直接抛 `FormatRecoveryError`，而不是静默导出坏格式。

可以把这条链路理解成：

```text
source.html
  -> 清洗 DOM，提取正文
  -> 英文 source.md（canonical source）
  -> 解析成 block
  -> block 按需要切成多个 Paragraph
  -> 行内格式转 hidden tokens 后送给 LLM
  -> 保存 text + tokenized_text + format_issues
  -> 导出时按 parent block 重组
  -> token 校验通过后恢复成中文 Markdown
```

## 1. HTML -> 英文 Markdown

入口在 `src/core/project.py` 的 `ProjectManager.create()`：

- 先把原始文件复制为项目内的 `source.html`
- 再调用 `src/html2md/converter.py` 的 `convert_html_to_markdown_text()`
- 最终把英文 Markdown 保存为项目内的 `source.md`

`convert_html_to_markdown_text()` 做了三件事：

1. `extract_article()` 从 HTML 中定位文章正文，并做 DOM 清洗。
2. `render_markdown()` 把正文渲染为标准 Markdown。
3. `copy_and_rewrite_images()` 复制或改写图片路径，保证 Markdown 里的图片引用可用。

这里有一个很重要的设计点：后续所有翻译、分段、导出，都建立在 `source.md` 上，而不是直接在 HTML 上做增量修改。

### 1.1 HTML 清洗

`src/html2md/extractor.py` 的 `extract_article()` 会：

- 定位文章容器和正文节点
- 提取元数据，如标题、作者、日期、原始链接
- 在必要时从 `window._preloads` 里回捞正文 HTML
- 把正文交给 `prepare_body()` 做清洗

这一步的目标是得到一个稳定、可转 Markdown 的正文 DOM，而不是保留原始页面所有展示细节。

### 1.2 Markdown 归一化

`src/html2md/markdown.py` 的 `render_markdown()` 用 `SemiAnalysisMarkdownConverter` 把 HTML 转成英文 Markdown。这里会主动做一些格式归一化：

- 标题统一成 ATX 形式，例如 `#` / `##`
- 图片统一成 `![alt](src "title")`
- `figcaption` 转成普通段落或斜体说明
- 裸链接补成 Markdown link
- 无意义的纯标点强调会被去掉

最终得到的是一份“语义稳定”的英文 Markdown，而不是对原 HTML 样式的 1:1 复刻。

## 2. 英文 Markdown -> canonical blocks

这一步在 `src/core/markdown_project_parser.py` 的 `MarkdownProjectParser.parse()`。

解析器会先做几件事：

- 读取文档级标题 `# ...` 作为项目标题
- 跳过开头的 front matter 风格信息
- 识别正文中的 block
- 把 block 组织成 section 和 paragraph

### 2.1 block 类型

当前 parser 能识别这些 block：

- fenced code block
- table
- `##`、`###`、`####`
- blockquote
- 无序列表项 `-` / `*` / `+`
- 图片 `![...]`
- 普通段落

其中有两个关键约定：

- `H2` 用来切 section，本身不会进入 section 的 paragraph 列表。
- `H3` / `H4` 会作为可翻译 block 保留下来，并在导出时重新补回 `###` / `####`。

### 2.2 行内格式提取

对于文本类 block，parser 不直接把 `**...**`、`[...](...)` 原样塞给后续流程，而是先执行 `_extract_inline_elements()`：

- 把链接、粗体、斜体、行内代码识别出来
- 生成 `InlineElement`
- 同时把 block 的 `plain_text` 提取出来

例如：

```markdown
**TSMC Transformation:** Apple used [TSMC](https://www.tsmc.com).
```

会被拆成两部分：

- `plain_text`: `TSMC Transformation: Apple used TSMC.`
- `inline_elements`: 记录粗体 span 和 link span 的位置、文本、href 等信息

随后 `assign_span_ids()` 会给这些 span 分配稳定 id，例如：

- `STRONG_1`
- `LINK_1`

这些 id 是整个后续格式恢复链路的锚点。

## 3. block -> 工作分段 Paragraph

当前系统里，`Paragraph` 是“翻译工作单元”，不是“最终导出单元”。这一层非常关键。

### 3.1 为什么要有 parent block

长段落需要拆开翻译，但最终导出时又必须恢复成原始 block 结构。所以 parser 在 `_build_segment()` 里会把每个工作段落都挂回它所属的父 block。

每个 `Paragraph` 会保存这些关键字段：

- `parent_block_id`
- `parent_block_index`
- `parent_block_type`
- `parent_block_markdown`
- `parent_block_plain_text`
- `parent_inline_elements`
- `segment_start`
- `segment_end`
- `expected_tokens`

这意味着：

- 一个 block 可以拆成多个 `Paragraph`
- 但这些 `Paragraph` 仍然知道自己来自哪一个原始 block
- 导出时可以重新拼回去

### 3.2 分段规则

`_segments_from_block()` 的规则是：

- `IMAGE` / `TABLE` / `CODE` 不拆
- `H3` / `H4` / `LI` 这类非普通正文 block 不拆
- 只有 `P` 和 `BLOCKQUOTE` 在超过 `max_paragraph_length` 时才尝试拆分

拆分时用 `_split_block_ranges()` 按句子切，但有一个重要保护：

- 如果切分边界会落在某个 inline span 中间，`_boundary_breaks_inline()` 会阻止拆分
- 如果某个 chunk 无法完整包含本地 inline span，`_slice_inline_elements()` 会返回 `None`
- 这两种情况都会退回“整块不拆”

也就是说，系统宁可少拆，也不允许把一个链接或粗体 span 从中间切断。

### 3.3 短段合并

`_merge_short_segments()` 会把同一个父 block 下的短段重新合并，但不会跨这些结构化 block：

- `IMAGE`
- `TABLE`
- `CODE`
- `H3`
- `H4`
- `LI`

因此最终 UI 里看到的 `Paragraph`，本质上是“在不破坏格式边界前提下，为翻译效率做过切分/合并的工作单元”。

## 4. 翻译前：把格式变成 hidden tokens

这一步集中在 `src/core/format_tokens.py`。

### 4.1 token 化输入

`build_translation_input(paragraph)` 会调用 `tokenize_text()`，把段落里的行内格式改写成隐藏 token。

例如原文：

```text
TSMC Transformation: Apple used TSMC.
```

结合 inline 元素后，送给模型的可能是：

```text
[[[STRONG_1|TSMC Transformation:]]] Apple used [[[LINK_1|TSMC]]].
```

这样做有几个目的：

- LLM 不需要自己重建 Markdown 语法
- 链接 URL、title 等元数据不暴露给模型去“自由改写”
- 导出时可以只依赖 token id 恢复格式

### 4.2 prompt 里怎么提醒模型

当前所有主要翻译入口都走同一套 token 协议：

- `src/agents/translation.py`
- `src/agents/four_step_translator.py`
- `src/services/batch_translation_service.py` 的 section mode

这些入口都会：

- 把 `tokenized_text` 而不是原始 Markdown 文本送给 LLM
- 把 `format_token_context(paragraph)` 塞进 prompt context

`src/prompts/prompt_builder.py` 里会生成明确约束：

- 保留 token wrapper
- 保留 token id
- 只能翻译 `|` 后面的文字
- 不能删除、复制、改序或跨段移动 token
- `CODE_*` token 内部文本默认不得改动

因此，无论是普通翻译、重译，还是四步法里的 refine，处理带格式段落时都不是裸文本流程。

## 5. 翻译后：保存 plain text 和 tokenized text

模型返回后，系统不会直接相信结果，而是先用 `build_translation_payload()` 做标准化。

### 5.1 校验规则

`validate_tokenized_text()` 会检查：

- 所有期望 token 是否都出现
- 每个 token 是否只出现一次
- 是否出现了意外 token
- `CODE_*` token 的内部文本是否被改坏
- token 内容是否为空

### 5.2 保存格式

校验通过时：

- `text` 保存去掉 token wrapper 后的纯文本译文
- `tokenized_text` 保存完整的 token 化译文
- `format_issues = []`

校验失败时：

- `text` 仍然保存可读的纯文本译文
- `tokenized_text = None`
- `format_issues` 记录具体问题

这就是为什么系统同时保留两种“可用性”：

- `has_usable_translation()`：只要有可读译文就算可用，给 UI、进度统计等宽松场景使用
- `has_export_ready_translation()`：必须具备可安全重建的 tokenized 译文，给导出场景使用

### 5.3 Paragraph 当前的格式状态

`Paragraph._update_format_state()` 会把格式恢复状态写进 `format_recovery_status`：

- `not_applicable`：这个段落没有格式 token
- `pending`：有格式 token，但还没有合格的 tokenized 译文
- `ready`：tokenized 译文已就绪
- `invalid`：存在 `format_issues`

这使得前端和服务层可以区分“文字翻完了”和“格式也可导出了”。

## 6. 中文 Markdown 导出时如何恢复格式

导出入口在 `src/core/project.py` 的 `ProjectManager.export_markdown()`。

它不会按 UI 里的 `Paragraph` 顺序直接拼字符串，而是先做 block 级重建。

### 6.1 先按 parent block 分组

`sorted_block_groups()` / `group_paragraphs_by_parent_block()` 会把同一个父 block 下的多个工作段落重新收拢，并按：

- `parent_block_index`
- `segment_start`

排序。

这样导出拿到的是“一个个原始 block”，而不是零散工作段。

### 6.2 再把多个 segment 拼回一个 block

`reconstruct_block_tokenized_text()` 会：

- 取父 block 的 `parent_block_plain_text`
- 按 `segment_start` / `segment_end` 把多个子段译文拼回去
- 对于没拆开的空隙，补回父块中的原始 gap 文本
- 优先使用每个段落的 `best_tokenized_translation_text()`
- 最后再用父块级的 `parent_inline_elements` 做一次整体 token 校验

注意这里是“先段落级保存，再 block 级复核”，不是只校验单段落。

### 6.3 严格失败而不是静默 fallback

`require_valid_reconstruction()` 会在 block 重建失败时直接抛 `FormatRecoveryError`。

当前这是一个有意保留的严格策略：

- 只要某个格式化 block token 缺失、重复、错位或破坏 code span
- 中文 Markdown 导出就直接失败

也就是说，导出阶段不会因为“文本大致可读”就偷偷生成一个格式可能错乱的结果。

### 6.4 恢复回 Markdown 语法

当 block 级 token 校验通过后：

- `restore_markdown_from_tokenized()` 会把 `[[[LINK_1|台积电]]]` 恢复成 `[台积电](...)`
- `STRONG_*` 恢复成 `**...**`
- `EM_*` 恢复成 `*...*`
- `CODE_*` 恢复成 `` `原始代码文本` ``

之后 `ProjectManager._render_block_markdown()` 再根据 block 类型补回外层结构：

- `H3` -> `### ...`
- `H4` -> `#### ...`
- `LI` -> `- ...`
- `BLOCKQUOTE` -> `> ...`

对于这些特殊 block：

- `IMAGE`：直接用 `parent_block_markdown`
- `TABLE`：直接保留原表格 Markdown
- `CODE`：用重建后的文本包回 fenced code block

这也是为什么最终导出的中文 Markdown 能保留原有的标题层级、列表、引用、图片和行内样式。

## 7. 当前实现真正保证了什么

当前系统保证的是“Markdown 语义结构”的稳定，而不是原 HTML 展示样式的完全复刻。

具体来说，当前能稳定保的有：

- section 层级：`#`、`##`、`###`、`####`
- 图片 markdown
- 表格 markdown
- code fence
- 链接
- 粗体、斜体、行内代码
- 列表项
- 引用块

当前不再支持的路径：

- HTML 导出已经移除
- 中文结果不再尝试回写到原始 HTML 里保留 `<head>` / CSS

所以现在的产品定义已经很明确：

- 输入可以是 HTML
- 内部标准形态是英文 Markdown
- 输出是中文 Markdown

## 8. 为什么这套设计比“直接翻 Markdown 文本”更稳

如果把原始 Markdown 直接给模型，常见问题是：

- 模型漏掉一个 `]` 或 `)`
- 把链接 URL 翻译掉
- 把 `**` 改成中文全角符号
- 把行内代码误翻
- 长段分段后无法再拼回原 block

当前实现通过三层保护避免这些问题：

1. parser 先把格式从正文文本里剥离成结构化 span
2. 翻译时只让模型改 token 内的可译文本
3. 导出时再做 block 级重建和硬校验

这三层缺一不可。只有“token 化 + parent block 重建 + 严格导出校验”一起存在，格式才真正可控。

## 9. 结合 `Apple-TSMC_smoke.md` 可以怎么理解

`data/pipeline_smoke/Apple-TSMC_smoke.md` 已经覆盖了这条链路里的多个真实边界：

- 图片
- 链接
- 粗体标签式开头
- `H3` / `H4`
- blockquote
- 列表风格段落
- 长段正文

对应的端到端 smoke 在 `tests/test_pipeline_smoke_e2e.py`，它不是整篇全文翻译，而是从真实文章里抽代表性 section 做 E2E：

- `00-intro`
- `02-key-numbers`
- `03-the-five-phases-of-apple-tsmc`
- `04-the-manufacturing-footprint`

测试会断言导出结果仍然保有这些格式形状：

- 图片 Markdown
- `###` 和 `####`
- 引用块前缀
- Markdown 链接
- 粗体

这份 smoke 的意义是：当前的格式链路不是只在人造小样本上成立，而是在真实长文的子集上已经跑通。

## 10. 调试格式问题时应该看哪里

按问题类型，优先看这些位置：

- HTML 转 Markdown 不对：`src/html2md/extractor.py`、`src/html2md/markdown.py`
- block 识别或分段不对：`src/core/markdown_project_parser.py`
- token 丢失、重复、错位：`src/core/format_tokens.py`
- 段落状态为什么“有译文但不可导出”：`src/core/models/translation.py`
- 导出时报 `FormatRecoveryError`：`src/core/project.py` + `src/core/format_tokens.py`
- section mode / four-step / retranslate 的 prompt 是否带了 token 约束：`src/agents/translation.py`、`src/agents/four_step_translator.py`、`src/prompts/prompt_builder.py`

## 11. 一句话总结

当前格式系统的核心不是“让模型学会写 Markdown”，而是“把 Markdown 结构从模型手里拿回来，模型只负责翻 token 内的文字，导出时由系统按父 block 严格重建”。
