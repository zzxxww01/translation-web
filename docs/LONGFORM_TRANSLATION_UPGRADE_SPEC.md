# 长文翻译升级系分文档

## 1. 文档目的

本文档用于定义 `translation_agent` 在长文翻译场景下的升级方案、首批落地实现、兼容性边界和后续演进方向。

当前版本只面向一个明确目标场景：

- 输入：`SemiAnalysis` 本地 `HTML`
- 任务：长文翻译
- 主成品：高保真 `Markdown`
- 兼容产物：`output.html`

本文档不是抽象规划，而是当前仓库已经存在的实现基础之上的正式设计说明，后续代码修改应以本文档为主参考。

## 2. 适用范围与非目标

### 2.1 适用范围

- 只处理长文，不讨论短句、交互式单段翻译优化。
- 只处理本地 HTML 输入，不处理 URL 抓取链路。
- 首版优先 `SemiAnalysis` 样本，不追求任意站点通用化。
- 保持现有对外接口和模式命名不变。

### 2.2 非目标

- 本轮不做旧项目自动迁移。
- 本轮不自动重切旧 section。
- 本轮不自动重建旧 paragraph 边界。
- 本轮不把 DOM-first 数据模型替换为唯一真相源。
- 本轮不把 `output.html` 做成第一优先级的高保真目标。

## 3. 当前系统现状

当前项目并非缺少翻译能力，而是缺少一条清晰、可复盘、质量导向的长文主链路。

### 3.1 已有能力

- `DeepAnalyzer`
  - 可做全文主题、结构、术语、风格、section role 分析。
- `FourStepTranslator`
  - 已有 `understand -> translate -> reflect -> refine` 的内部能力。
- `LayeredContextManager`
  - 已有全文、章节、上下文、术语跟踪能力。
- `ConsistencyReviewer`
  - 已有全文一致性审查与 auto-fix。
- `ProjectManager`
  - 已有项目持久化、旧项目读取、`output.md` / `output.html` 导出。
- `TranslationPromptBuilder`
  - 已有单段翻译 prompt 构造能力。
- `GeminiProvider`
  - 已有批量章节翻译、单段翻译、反思、修订、标题翻译等调用点。

### 3.2 升级前的核心问题

#### A. 流程问题

- `/translate-four-step` 路由没有显式传入 `four_step` 模式，导致接口命名与实际行为可能漂移。
- 四步法虽然存在，但长文主链路没有把 `draft / critique / revision` 作为清晰的章节级产物保留下来。
- 一致性审查存在，但 run 级 artifacts 不完整，难以复盘质量问题来自哪一章、哪一步。

#### B. Prompt 问题

- 单段翻译 prompt 之前没有稳定消费 `article_theme / article_structure / section_role / next_preview` 等关键上下文。
- 章节批量翻译 prompt 之前没有明确吸收 section role、translation voice、translation notes。
- 反思与修订 prompt 之前更像通用打分与局部润色，未显式把“准确性、术语一致性、翻译腔”制度化为首要目标。

#### C. 成品与项目问题

- 翻译过程缺少 run 级 artifacts 目录。
- 旧项目已经存在进行中的 section / paragraph / approved 状态，任何自动结构迁移都会破坏历史 review 语义。

## 4. 升级目标

本轮升级的目标不是泛化，而是把现有长文链路正式化。

### 4.1 质量目标

- 准确性优先：不误译、不漏译、不弱化原文判断。
- 术语一致优先：跨章节术语、缩写、首现策略更稳定。
- 去翻译腔：压掉英文句法投影、机械名词串、弱中文句式。
- 篇章感更强：译文带着章节角色和论证推进感，不是孤立段落拼接。

### 4.2 工程目标

- `section` 模式保留，但更强依赖全文分析和章节上下文。
- `four_step` 模式明确走 `analysis -> draft -> critique -> revision -> consistency -> export`。
- 每次 run 落盘关键 artifacts。
- 旧项目可继续打开、继续翻译、继续导出。

## 5. 升级后目标链路

### 5.1 `section` 标准翻链路

1. 全文分析
2. 章节 prompt 上下文构建
3. 章节批量翻译
4. 全文一致性审查
5. 导出 `output.md`
6. 兼容导出 `output.html`

### 5.2 `four_step` 精修翻链路

1. 全文分析
2. 章节上下文构建
3. 章节 draft
4. 章节 critique
5. 章节 revision
6. 全文一致性审查
7. 导出 `output.md`
8. 兼容导出 `output.html`

### 5.3 各阶段职责

#### Phase 0：全文分析

输出：

- `theme`
- `structure_summary`
- `terminology`
- `style.translation_voice`
- `guidelines`
- `section_roles`

用途：

- 统一全篇翻译策略。
- 为后续 draft / critique / revision / consistency 提供共享上下文。

#### Phase 1：章节 draft

目标：

- 先生成高质量初稿，而不是直接把第一版当最终结果。

依赖上下文：

- article theme
- structure summary
- section role
- translation notes
- translation voice
- glossary
- previous paragraphs
- next preview

#### Phase 2：章节 critique

目标：

- 只诊断问题，不直接改文。

主优先级：

1. 准确性
2. 术语一致性
3. 翻译腔
4. 篇章衔接
5. 标题 / 图注 / 数据密集段失真

#### Phase 3：章节 revision

目标：

- 仅针对 critique 指出的问题定向修订，不自由重写整章。

约束：

- 保留问题外的稳定句子。
- 服从 glossary 和 critique 建议。
- 修翻译腔时不能删技术信息。

#### Phase 4：全文 consistency

目标：

- 把章节级优化抬升到全文层。

检查重点：

- 术语统一
- 标题系统统一
- 数字与单位统一
- 图表命名统一
- 重复概念表述统一

#### Phase 5：导出

当前导出策略：

- 主导出：`output.md`
- 兼容导出：`output.html`

### 5.4 用户交互链路

这一节回答的是“用户在前端到底怎么操作，系统又会在什么时机进入四步法”。

#### 5.4.1 启动全文翻译

当前前端交互保持不变，用户仍然通过左侧栏触发全文翻译：

1. 选择一个项目。
2. 在左侧 `DocumentSidebar` 点击“全文一键翻译”。
3. 如需修改模型或方法，展开“高级选项”。
4. 当前默认方法已经改为“四步法翻译”，只有用户手动切回“普通翻译”时，才会走旧的标准链路。
5. 点击后，前端会弹出确认框：
   - 若选择四步法，会明确提示“会进行深度分析、反思和润色，质量更高但耗时更长”。
   - 若选择普通翻译，则提示普通全文翻译确认。

#### 5.4.2 翻译进行中

点击确认后，前端不会要求用户手动逐步触发“理解 / 反思 / 润色”。这些步骤全部由后台自动串联。

前端会持续展示两类信息：

- 总进度：当前已处理段落数 / 全部段落数。
- 当前步骤：例如“深度分析全文”“翻译章节 2/8”“某章节 - 反思”“某章节 - 润色”。

也就是说，四步法对用户来说仍然是一次“全文一键翻译”，只是后台链路更重。

#### 5.4.3 翻译完成后的人工审核

这是当前产品交互中最重要的一点：

- 四步法完成后，不会直接替代人工确认。
- 系统只是把每个 paragraph 的机器候选译文预先写好。
- 用户仍然像现在一样按章节查看、按段落打开编辑面板、人工修改、人工确认。

机器四步法负责的是“把待审稿先做得更好”，不是“取消人工逐段定稿”。

#### 5.4.4 推荐的人机协作方式

首版推荐工作方式如下：

1. 导入 `SemiAnalysis` HTML，生成项目。
2. 直接用默认的“四步法翻译”跑完整篇。
3. 翻译完成后，按章节进入 `SectionView`。
4. 对可疑章节优先看重点段落。
5. 打开 `EditPanel` 或沉浸式编辑器，对段落做人工修改。
6. 对人工确认后的段落执行确认，进入 `approved` 状态。
7. 最后导出 `output.md`，必要时导出兼容 `output.html`。

因此，用户交互视角下的完整链路应理解为：

`一键机器四步法预翻 -> 章节浏览 -> 段落人工修订 -> 段落确认 -> 导出`

### 5.5 前端到后端的调用链路

这一节描述“用户点一下之后，系统各层是怎么串起来的”。

#### 5.5.1 前端触发层

前端调用顺序如下：

1. `DocumentSidebar` 收集 `selectedModel` 和 `selectedMethod`。
2. 点击“全文一键翻译”后，调用 `DocumentFeature.handleFullTranslate(...)`。
3. `handleFullTranslate(...)` 根据方法选择内部 method type：
   - `four-step`：四步法精修链路
   - `normal`：普通全文翻译链路
4. 然后进入 `useFullTranslate.startTranslation(...)`。
5. `useFullTranslate` 调用 `fullTranslationService.startTranslation(...)`，通过 SSE 订阅后台进度。

#### 5.5.2 路由分流层

后端根据方法进入不同 API：

- 普通翻译：`POST /projects/{project_id}/translate-stream`
- 四步法翻译：`POST /projects/{project_id}/translate-four-step`

当前默认配置已经让前端优先选择四步法，因此在不手动切换的情况下，用户点击全文翻译默认进入 `/translate-four-step`。

#### 5.5.3 SSE 进度回传层

后端在翻译过程中会持续回传事件，前端按事件更新状态：

- `start`：初始化总段落数
- `progress`：更新当前步骤与当前位置
- `translated` / `skip` / `error`：更新进度条与局部状态
- `complete` / `incomplete`：结束本次 run

前端收到 `translated` 事件时，会即时把段落译文写入前端 store，因此用户不需要等全部结束后才能看到机器结果。

### 5.6 四步法的 agent / 服务内部链路

这一节是系统内部的正式执行链，用于指导后续代码维护和优化。

#### 5.6.1 Run 初始化

当 `/translate-four-step` 被调用后，系统会：

1. 读取项目和全部 sections。
2. 实例化 `BatchTranslationService`，并明确指定 `translation_mode = four_step`。
3. 创建 `artifacts/runs/<run_id>/` 目录。
4. 先写入：
   - `source-manifest.json`
   - `structure-map.json`

此时 run 已经具备可复盘基础，即使中途失败，也能保留上下文和失败现场。

#### 5.6.2 Phase 0：全文分析

`BatchTranslationService.translate_project(...)` 首先执行：

1. `DeepAnalyzer.analyze(project.sections)`
2. 将结果写入 `analysis.json`
3. 基于 analysis 生成：
   - `section-plan.json`
   - `prompt-context.json`
4. 将 analysis 注入 `LayeredContextManager`

这一阶段的目标不是生成译文，而是先建立整篇文章的共享翻译语境，包括：

- 文章主题
- 结构摘要
- 术语表
- 风格与 voice
- 章节角色
- 翻译指导项

#### 5.6.3 标题与章节标题处理

在进入正文翻译前，服务还会：

1. 翻译文章标题和元信息。
2. 翻译各 section 标题。
3. 将这些结果保存回项目元数据。

这样做的目的是在正文翻译时，让章节标题也成为已经稳定可用的上下文。

#### 5.6.4 逐章节准备

对每个 section，系统依次执行：

1. 生成章节级 prompt context。
2. 写入 `section-context/<section_id>.json`。
3. 执行 `prescan_section(...)`：
   - 快速抽取新术语
   - 检测与既有术语表的冲突
4. 写入 `section-prescan/<section_id>.json`。

这一阶段的重点不是直接翻译，而是先把“本章在全文中的位置”和“本章的新术语风险”准备好。

#### 5.6.5 FourStepTranslator 章节内链路

每一章进入 `FourStepTranslator.translate_section(...)` 后，正式按四步法执行：

1. `understand`
   - 获取章节角色、与前后章节关系、关键点、translation notes。
   - 若全文分析里已有 section role，则优先复用，减少重复 LLM 调用。
2. `draft`
   - 为每个段落构建分层上下文。
   - 上下文包含：article theme、article structure、terminology、guidelines、section role、前文段落、后文预览。
   - 逐段生成初稿。
   - 对长章节按批次翻译，但对用户仍表现为一个章节任务。
3. `critique`
   - 用整章 source + draft 做集中反思。
   - 重点查准确性、术语一致性、翻译腔、章节衔接、标题/图注/数据段失真。
   - 输出结构化问题列表。
4. `revision`
   - 按 critique 的问题逐段定向修订。
   - 不把整章重新自由改写。
5. `quality gate`
   - 评估是否通过。
   - 若质量不足且允许重试，可触发重译。

执行完后，系统会保留三类核心章节结果：

- `draft_translations`
- `revised_translations`
- `translations`

其中 `translations` 代表最终写回 paragraph 的机器候选译文。

#### 5.6.6 写回项目与章节 artifacts

四步法章节完成后，服务会：

1. 把最终 `translations` 写回各 paragraph。
2. 将 paragraph 状态更新为 `TRANSLATED`。
3. 保存章节。
4. 落盘：
   - `section-draft/<section_id>.json`
   - `section-critique/<section_id>.json`
   - `section-revision/<section_id>.json`

注意，这里只会把段落置为 `TRANSLATED`，不会自动置为 `APPROVED`。

这是机器流程与人工审核能够兼容的关键。

#### 5.6.7 全文一致性审校与导出

全部章节完成后，服务继续执行：

1. `ConsistencyReviewer` 做全文一致性检查。
2. 生成 `consistency.json`。
3. 自动导出：
   - `output.md`
   - 兼容 `output.html`
4. 生成：
   - `markdown-export-report.json`
   - `run-summary.json`

至此，一次完整的四步法 run 结束。

### 5.7 机器四步法与人工逐段确认的衔接

这是当前工作流中必须明确写死的产品约束。

#### 5.7.1 四步法不会替代人工确认

四步法的职责是：

- 给每个段落生成更高质量的候选译文
- 降低人工逐段修改的成本
- 提前发现术语、一致性、翻译腔问题

四步法不负责：

- 自动批准段落
- 自动替用户做最终定稿
- 自动覆盖已有人工确认结果

#### 5.7.2 当前人工确认链路保持不变

机器翻译结束后，用户仍然沿用现有审核方式：

1. 打开某个 section。
2. 选择某个 paragraph。
3. 在 `EditPanel` 或 `ImmersiveEditor` 中查看机器译文。
4. 人工修改译文。
5. 调用确认动作，把该段落置为 `approved`。

因此，当前系统的真实链路不是“全文翻译完就结束”，而是：

`四步法机器预翻 -> 人工逐段审校 -> 人工逐段确认 -> 成品导出`

#### 5.7.3 为什么必须保留这条人工链路

原因有三点：

- 长文翻译即使经过 critique / revision，仍然可能存在局部误译或风格不合意。
- 你当前项目已经围绕 `paragraph` 级确认机制建立了 review 工作流。
- 旧项目中已有 `approved` 状态和人工历史，不能用“机器一次翻完即定稿”的模式覆盖。

所以，四步法应被视为“增强型机器预处理”，而不是“替代人工的终局翻译器”。

## 6. Prompt 体系设计

### 6.1 全文分析 Prompt

要求模型输出：

- 全文主线
- 章节作用
- 术语策略
- 风格策略
- 读者理解障碍
- 翻译注意事项

Prompt 指令重点：

- 先判断文章主论点，而不是先做段落摘要。
- 明确每一章在整篇论证里的角色。
- 优先识别高频术语、缩写、专有名词及首现策略。
- 标出容易产生翻译腔或误译的章节类型。
- 区分“读者需要解释的概念”和“不需要额外解释的常见术语”。

预期输出用途：

- 作为全文共享上下文，进入后续 draft / critique / revision / consistency。
- 不直接给用户当成最终产品，而是给 agent 作为翻译约束。

### 6.2 单段 / 章节 draft Prompt

升级点：

- 现在显式接入：
  - `article_theme`
  - `article_structure`
  - `section_context`
  - `style_guide`
  - `previous_paragraphs`
  - `next_preview`
- 让模型知道自己在翻译“整篇文章中的这一段”，而不是脱离上下文的孤立文本。

指令重点：

- 译文必须服从章节角色，而不是只做局部字面对译。
- 必须保留原文判断力度，不得无故弱化。
- 术语首现优先采用“中文（English）”。
- 对数据密集段，优先保留数字、比较关系、结论方向。
- 对标题、列表、图注这类高信息密度块，必须短、准、结构清楚。

禁止事项：

- 不得为了流畅擅自删减事实。
- 不得为了中文自然度抹平作者原本的判断强度。
- 不得在没有必要时把明确术语泛化成宽泛表达。

### 6.3 章节批量翻译 Prompt

升级点：

- 新增：
  - `section_role`
  - `translation_voice`
  - `translation_notes`
- 这些内容会被拼进章节级 guidelines，避免章节翻译只依赖术语和泛风格说明。

适用场景：

- `section` 标准翻模式
- 对长章节做分批翻译时的章节级共享约束

目标：

- 让标准翻模式也能吃到“整章角色感”和“全文 voice”，而不是退化成大块文本直译。

### 6.4 Critique Prompt

升级点：

- 现在可以收到：
  - article theme
  - structure summary
  - section title
  - section role
  - relation to previous / next
  - translation notes
  - review priorities
- critique 目标从“泛评估”收紧到“问题定位”。

结构化问题字段：

- `paragraph_index`
- `issue_type`
- `severity`
- `description`
- `why_it_matters`
- `suggestion`

指令重点：

- 不做空泛夸奖，优先报告高严重度问题。
- 先查准确性，再查术语，再查翻译腔，最后才查一般润色问题。
- 每条 critique 必须能支持 revision 执行，不能只给抽象评价。
- 对翻译腔问题，必须指出具体症状，例如英文句法投影、机械名词串、被动句堆叠、逻辑重音错位。
- 对术语问题，必须指出建议统一译法，而不只是说“不一致”。

预期输出：

- 结构化问题列表，供 revision 直接消费。
- 可被 artifact 化，供后续 section-first review 展示。

### 6.5 Revision Prompt

升级点：

- 现在可以收到：
  - section role
  - translation voice
  - guidelines
  - terminology
- 修订不再只依赖单条 issue 文本，而是带着章节约束做 targeted revision。

指令重点：

- 只修 critique 命中的问题，不随意重写稳定句子。
- 术语必须服从 glossary、analysis 和 critique。
- 修正翻译腔时，不得损失技术信息、数字关系或判断逻辑。
- 修订后的译文仍需保持同一章节内的风格统一。

预期输出：

- 比 draft 更准、更统一、更自然的章节版本。
- 仍然适合人工继续逐段审核，而不是直接跳过人工确认。

### 6.6 Prompt 输入输出契约

为了避免实现阶段再次把 prompt 做散，本方案要求后续继续坚持显式字段契约。

建议所有翻译相关 prompt 统一使用以下输入字段命名：

- `article_theme`
- `structure_summary`
- `section_role`
- `section_position`
- `translation_guidelines`
- `translation_voice`
- `translation_notes`
- `glossary_entries`
- `previous_paragraphs`
- `next_preview`
- `review_priorities`

建议结构化输出至少稳定以下 schema：

- analysis schema
  - `theme`
  - `structure_summary`
  - `terminology`
  - `section_roles`
  - `guidelines`
- critique schema
  - `paragraph_index`
  - `issue_type`
  - `severity`
  - `description`
  - `why_it_matters`
  - `suggestion`
- consistency schema
  - `issue_type`
  - `section_id`
  - `paragraph_index`
  - `description`
  - `auto_fixable`

### 6.7 SemiAnalysis 与 baoyu-translate 的混合策略

本项目不会把 prompt 方向改成通用翻译器，也不会把 `SemiAnalysis` 的文章翻成“故事化中文”。

本轮 prompt 升级的总原则是：

- 保留 `SemiAnalysis` 的核心特征：
  - 深度技术分析
  - 鲜明行业判断
  - 数据驱动论证
  - 克制但明确的分析师声线
- 吸收 `baoyu-translate` 更成熟的部分：
  - accuracy first
  - meaning over words
  - natural flow
  - 首现术语策略
  - 读者理解障碍识别
  - critique / revision 分工清晰

因此，本项目的目标中文风格明确设定为：

- 专业
- 锐利
- 克制
- 判断明确
- 不论文腔
- 不自媒体腔
- 不故事化渲染

### 6.8 本轮 Prompt 升级要点

本轮对 prompt 的升级，不是简单“加几条术语规则”，而是补齐下面 6 类能力。

#### 6.8.1 显式目标读者

现在 prompt 明确假定默认读者为：

- 关注半导体、AI基础设施与科技产业的中文读者
- 具备基础行业理解
- 但不默认知道所有英文缩写、美国供应链细节和细分封装术语

这使“要不要解释”“要不要首现括注”不再完全凭模型临场发挥。

#### 6.8.2 首现术语策略

现在 prompt 明确区分：

- `preserve`
  - 保留英文
- `first_annotate`
  - 首次使用 `中文（English）`
- `translate`
  - 直接中文化

并增加一条硬规则：

- 只有真正影响理解时，才允许 `中文（English，极短解释）`
- 不得对常见术语过度括注

#### 6.8.3 判断力度保真

现在 draft / batch / critique / revision 全部强调：

- 不得把强判断翻成中性概述
- 不得加入原文没有的缓冲词
- 不得把批评性表述磨平

这条规则是 `SemiAnalysis` 场景下最重要的风格护栏。

#### 6.8.4 可读性优化不再等于“翻软”

本轮吸收 `baoyu-translate` 的“自然中文优先”原则，但明确限制为：

- 可以拆长句
- 可以重组语序
- 可以按中文习惯先结论后证据
- 但不能改变逻辑方向
- 不能删数字
- 不能删比较基线
- 不能删限定条件

也就是说，允许“更像中文”，但不允许“更像改写”。

#### 6.8.5 critique 输出颗粒度升级

现在 critique 不再只做模糊评分，而要求结构化输出：

- `issue_type`
- `severity`
- `description`
- `why_it_matters`
- `suggestion`

这使 revision 能真正做到“按问题单定向修订”，而不是再次自由发挥。

#### 6.8.6 文档、运行时上下文、模板三层对齐

本轮明确要求三层保持一致：

- 文档层定义目标风格与规则
- 运行时上下文真正传入 `target_audience / translation_voice / article_challenges`
- 模板层真正消费这些字段

这样才能避免“文档里写得很好，但模型实际拿不到这些信息”。

## 7. Artifacts 设计

### 7.1 Run 目录

每次翻译会生成：

`projects/<project_id>/artifacts/runs/<run_id>/`

其中 `<run_id>` 使用时间戳生成，避免覆盖旧 run。

### 7.2 当前已落盘的 artifacts

- `source-manifest.json`
  - 记录项目、源文件、模式、段落数、章节数。
- `structure-map.json`
  - 记录章节、段落、元素类型、heading chain 等结构摘要。
- `analysis.json`
  - 全文分析结果。
- `section-plan.json`
  - 各章节位置、role、translation notes。
- `prompt-context.json`
  - run 级共享 prompt 上下文快照。
- `section-context/<section_id>.json`
  - 每章的 prompt 上下文。
- `section-prescan/<section_id>.json`
  - 每章 prescan 结果。
- `section-draft/<section_id>.json`
  - 标准翻的章节批量结果，或 four-step 的 draft 结果。
- `section-critique/<section_id>.json`
  - four-step 的 critique 结果。
- `section-revision/<section_id>.json`
  - four-step 的 revision 结果。
- `consistency.json`
  - 全文一致性审查结果，或失败原因。
- `markdown-export-report.json`
  - `output.md` / `output.html` 导出结果。
- `run-summary.json`
  - 本次 run 的汇总结果。

## 8. 兼容性评估

### 8.1 现有项目事实

仓库中的旧项目已经依赖以下结构：

- `projects/<id>/meta.json`
- `projects/<id>/sections/<section_id>/meta.json`
- `Paragraph(**p)` 直接反序列化
- 已存在 `approved` 段落

因此本轮升级必须坚持：

- 自动读写兼容
- 不自动结构迁移

### 8.2 首版兼容原则

旧项目必须：

- 可以继续打开
- 可以继续翻译
- 可以继续导出
- 可以保留既有 section 边界
- 可以保留既有 approved 状态

### 8.3 本轮兼容做法

- 不修改旧项目磁盘结构的必填字段。
- 新信息全部落在 `artifacts/runs/` 目录，不污染旧 section 元数据契约。
- `SectionTranslationResult` 只新增可选字段，不影响旧读取逻辑。
- `translate-four-step` 仅修正接口语义，不改项目数据模型。
- 翻译完成后自动导出 `output.md` 和兼容的 `output.html`，不会改变旧 review 数据。

### 8.4 对进行中项目的实际影响

#### 影响 1：`/translate-four-step` 现在真的会走四步法

结果：

- 质量会更高。
- 耗时会更长。
- 模型调用数会上升。
- 以前把它当“普通批量翻译”的调用方，现在会得到更重的链路。

#### 影响 2：旧项目会开始出现 artifacts

结果：

- 旧项目目录下新增 `artifacts/runs/...`
- 不影响原有 `sections/` 与 `meta.json`
- 不需要手动迁移

#### 影响 3：翻译完成后会自动刷新导出文件

结果：

- `output.md` 会被自动更新
- `output.html` 会尝试同步更新
- 老工作流如果依赖导出文件，将直接受益

#### 影响 4：不会破坏已确认段落

当前边界：

- 不自动重切 section
- 不自动重建 paragraph
- 不自动重写已有人工确认记录

### 8.5 剩余风险

- `output.html` 仍然是兼容导出，不是高保真 DOM 回写方案。
- 旧项目如果章节内部结构本身就切得不理想，本轮不会自动修复。
- 复杂表格、复杂链接语义、DOM 精确保真仍需后续迭代。

## 9. 本轮已落地实现

### 9.1 流程

- 修复 `/translate-four-step` 使用 `four_step` 模式。
- four-step 结果现在保留：
  - `draft_translations`
  - `revised_translations`
- 章节 critique 和 revision artifacts 已落盘。

### 9.2 Prompt

- 单段翻译 prompt 已接入：
  - article theme
  - article structure
  - section role
  - target audience
  - translation voice
  - article challenges
  - translation notes
  - next preview
- critique / revision prompt 已接入章节级上下文和术语约束。
- 批量章节翻译 prompt 已接入 section role / target audience / translation voice / translation notes / article challenges。
- 术语 prompt 已明确区分 preserve / first_annotate / translate，并要求控制首现括注密度。
- reflection prompt 已升级为结构化问题单，要求输出 severity 和 why_it_matters。

### 9.3 Artifacts

- 新增 run 级 artifacts 目录。
- 新增 analysis / section plan / prompt context / draft / critique / revision / consistency / export report / run summary。

### 9.4 术语预检与术语库

- 新增“全文术语预检”链路：
  - 前端点击全文翻译后，先调用术语预检接口。
  - 系统会对整篇文章做一次高优先级新术语预扫。
  - 如果命中待确认术语，先进入单独的术语预检页，再开始全文翻译。
- 高优先级新术语当前按以下规则触发：
  - 出现在标题 / 小标题 / 图表标题
  - 在全文中达到高频阈值
  - 系统识别为存在多种可能译法
- 术语预检页按章节分组展示，并支持：
  - 采用建议译法
  - 自定义译法
  - 跳过
- 跳过的语义已落地为：
  - 本次不写入项目术语库
  - 本次翻译先沿用系统建议
  - 后续再次命中高优先级条件时仍可重新确认
- 新增独立术语管理页：
  - 查看项目术语
  - 查看全局术语
  - 编辑 / 删除 / 禁用术语
  - 查看“推荐提升到全局”的项目术语
  - 手动将项目术语提升到全局
- 术语库当前采用两层结构：
  - 全局术语库
  - 项目术语库
- 运行时优先级当前固定为：
  - 项目术语库 > 全局术语库 > 模型建议
- 为兼容旧项目，项目术语接口在展示时会自动隐藏“与全局术语完全相同的继承项”，避免旧项目因为历史原因显示一整份默认术语表。
- 从本轮开始，新创建项目的项目术语库默认是空的，不再复制整份默认半导体 glossary。

## 10. 下一阶段建议

本轮解决的是“链路清晰、prompt 更强、可复盘、旧项目兼容”。

下一阶段建议按优先级继续：

1. HTML 结构保真升级
   - 以 DOM block map 增强 `section/paragraph`。
   - 为链接、图片、表格建立更稳定的结构元数据。

2. Markdown 导出升级
   - 更稳定保留链接和图片关系。
   - 区分简单表格与复杂表格。

3. section-first review 视图
   - 直接消费 `section-critique` 和 `section-revision` artifacts。

4. 旧项目显式迁移工具
   - 仅在用户明确需要时执行，不纳入自动升级。

## 11. 验收标准

### 11.1 工程验收

- `translate-four-step` 必须真实走 four-step。
- 关键 artifacts 必须可落盘。
- 旧项目无需迁移即可继续运行。

### 11.2 质量验收

- critique 能稳定抓到准确性、术语、一致性、翻译腔问题。
- revision 后的章节比 draft 更自然、更统一。
- Markdown 导出可作为主成品继续人工整理。

### 11.3 兼容验收

- 旧项目可继续打开。
- 旧项目的已确认段落不丢失。
- 旧项目的 section 边界不漂移。
