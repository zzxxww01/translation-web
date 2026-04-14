# Claude Code 是转折点

## 引言

### 产品解读，我们如何使用，行业影响，微软的困境，Anthropic 为何取胜

作者：[Doug O'Laughlin](https://substack.com/@mule)、[Jeremie Eliahou Ontiveros](https://substack.com/@jeremieeliahouontiveros)、[Jordan Nanos](https://substack.com/@jnanos) 等 5 人

2026 年 2 月 5 日 · 付费文章

眼下，GitHub 上 4% 的公开提交正由 Claude Code 编写。按照当前轨迹，我们认为到 2026 年底，Claude Code 将包揽每日超 20% 的代码提交量。就在你眨眼之间，AI 已经吞噬了整个软件开发行业。

我们的姊妹刊 Fabricated Knowledge 曾将当下的软件比作[互联网崛起时的传统电视](https://www.fabricatedknowledge.com/p/ai-is-creating-peak-software-media)，并认为[Claude Code 势必将在软件之上构建全新的智能层，其颠覆性堪比 DRAM 之于 NAND](https://www.fabricatedknowledge.com/p/the-death-of-software-20-a-better)。今天，SemiAnalysis 将深入剖析 Claude Code 引发的行业震荡、其核心本质，以及 Claude 为何如此强大。

![](https://substackcdn.com/image/fetch/$s_!MG5m!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6ec41954-9498-4c2f-b23a-81e2bae29f82_2761x1579.png)

来源：[Tokenomics 团队](http://semianalysis.com/tokenomics-model/)，Github，由 Claude Code 生成

我们认为，Claude Code 正是 AI“智能体（指能够自主规划并执行复杂任务的 AI）”的破局拐点，预示了 AI 未来的运作范式。它注定将在 2026 年为 Anthropic 带来惊人的营收增长，助力这家实验室的增速将 OpenAI 远远甩在身后。

我们为 Anthropic 构建了一套详尽的经济模型，精准量化了其对 AWS、Google Cloud、Azure 等云合作伙伴，以及 Trainium2/3、TPU 和 GPU 等相关供应链在营收与资本支出（capex）方面的影响。这正是 [Tokenomics 模型的核心目的](https://semianalysis.com/tokenomics-model/)。

未来三年，Anthropic 的新增算力规模势必追平 OpenAI。您可以参考我们的 [数据中心行业模型](https://semianalysis.com/datacenter-industry-model/)，其中对 Anthropic 和 OpenAI 进行了逐栋数据中心的追踪。值得注意的是，Sam 的 AI 实验室正饱受多个数据中心项目延期的困扰——我们在媒体大肆报道的数月前就已发出预警，最典型的一次是在我们的 CoreWeave 2025 年第三季度财报前瞻中，明确指出了其资本支出指引大幅不及预期。

![](https://substackcdn.com/image/fetch/$s_!P1XQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc04de5e0-5ec5-4c11-a6d3-c3dab116d665_927x585.png)

来源：SemiAnalysis [Datacenter 模型](https://semianalysis.com/datacenter-industry-model/)

既然算力越多意味着营收越高，我们便可预测其年度经常性收入 (ARR) 的增长，并将 Anthropic 与 OpenAI 进行直观对比。

![](https://substackcdn.com/image/fetch/$s_!7xxX!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7572d353-1443-483a-a286-4cb33d1413f9_927x585.png)

*来源：SemiAnalysis [Tokenomics 模型](https://semianalysis.com/tokenomics-model/)*

值得注意的是，我们的预测显示，Anthropic 的季度 ARR 增量已经反超 OpenAI。**Anthropic 每月的新增营收均高于 OpenAI。** 我们认为，Anthropic 未来的增长将受制于算力。

接下来，让我们深入剖析 Anthropic 皇冠上的明珠：Claude Code。

## Claude Code 与智能体未来

智能体（指能够自主规划并执行复杂任务的 AI）必将成为有机智能（人类）与 AI 交互的核心路径。但 Claude Code 同样演示了这一过程的镜像反转：即智能体如何反向与人类交互。

我们笃定，AI 的未来在于 token 编排，而非仅仅按基础成本售卖 token。以史为鉴，我们将 OpenAI 的 ChatGPT API 视为 token 的调用与响应。这犹如 Web 1.0 时代，TCP/IP 协议将用户与互联网上的静态网站相连。尽管 TCP/IP 是底层基石，但在 Web 2.0 时代，这一通信协议已退居幕后，成为支撑互联网运转与动态网页转型的基础手段。如今，互联网利用 TCP/IP 数据包编排的信息量，已远超当年的静态网站。底层协议固然重要，但真正创造数万亿美元商业价值的，是构建于协议之上的繁荣应用。

正因如此，SemiAnalysis 认为我们再次站在了 AI 发展的历史性十字路口。这一时刻的意义即便不超越，也绝对足以媲美 2023 年初的 ChatGPT 时刻。

![](https://substackcdn.com/image/fetch/$s_!vndH!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc1640e14-9bd1-4646-8592-097fcfcd5c4d_3180x1779.png)

来源：[SemiAnalysis Tokenomics 模型，](https://semianalysis.com/tokenomics-model/)由 Claude Code 生成

每一个历史节点都在拓宽 AI 的能力边界：
- GPT-3 验证了规模法则行之有效。
- Stable Diffusion 展现了 AI 的图像生成能力。
- ChatGPT 证实了市场对智能的庞大需求。
- DeepSeek 证明了小参数规模同样大有可为。
- o1 表明持续扩展模型能够带来更卓越的性能。

吉卜力画风（译注：指 AI 生成吉卜力风格图像）爆红全网的现象级时刻仅仅是技术的普及节点，但 Claude Code 截然不同——它是智能体层的根本性突破，能够将模型输出编排为更高阶的形态。

## 什么是 Claude Code？

Claude Code 是一款终端原生 AI 智能体（指能够自主规划并执行复杂任务的 AI），其重心并非 IDE (集成开发环境) 或类似 Cursor 的聊天机器人侧边栏。Claude Code 是一款 CLI (命令行界面) 工具，能够读取代码库、规划多步任务并予以执行。如果仅仅把 Claude Code 视为聚焦于代码的工具，或许有失偏颇，它更像是克劳德计算机（Claude Computer）。在获得计算机的完全访问权限后，Claude 能够理解所处环境、制定计划并迭代完成该计划，且全程听从用户指令。

Claude Code 的能力远不止于编写代码，它是 AI 智能体的最佳范例。你可以用自然语言与计算机交互，描述目标和预期结果，而非具体的实现细节。只需为 Claude（即这款 CLI 工具）提供电子表格、代码库或网页链接等输入内容，并设定目标，它随即会制定计划、核实细节并执行操作。

这是对未来的一瞥，但在当今的软件领域，未来已然降临。你最欣赏的工程师们正在进行氛围感编程（Vibe coding）：

- **Andrej Karpathy**（[他在一年前创造了“氛围感编程”一词](https://x.com/karpathy/status/1886192184808149383?s=20)）[正公开探讨这一范式转变](https://x.com/karpathy/status/2015883857489522876?s=20)，他明确表示：“我已经注意到，自己手动编写代码的能力正慢慢退化。生成（写代码）和辨别（读代码）是大脑中截然不同的两种能力。”

- **Vercel 首席技术官 Malte Ubl** 声称，他的“新主业”是“告诉 AI 它哪里做错了”。

[￰4￰

Malte Ubl@cramforce

今年，我对 bash、文件系统、Postgres 传输协议以及 sqlite 的理解达到了前所未有的深度；如果我的新主业不是去告诉 AI 它哪里做错了，我绝不可能有如此深刻的认知。

￰5￰

Anthropic @AnthropicAI

AI 能让工作更高效，但人们也担忧：过度依赖 AI 或将阻碍员工在工作中学习新技能。为一探究竟，我们针对软件工程师开展了一项实验。结果显示，使用 AI 编程确实会导致技能熟练度下降——但这取决于人们的具体使用方式。https://t.co/lbxgP11I4I

下午 4:10 · 2026 年 1 月 31 日 · 7.43 万次查看

21 条回复 · 14 次转发 · 558 次点赞](https://x.com/cramforce/status/2017631686142644691?s=20)

- **NodeJS 创始人 Ryan Dahl** 表示，“人类手写代码的时代已经终结”

[￰6￰

Ryan Dahl@rough\*\*sea

这话已经被说过无数次了，但请允许我再强调一遍：人类手写代码的时代已经终结。对于我们这些自诩为 SWE (软件工程师) 的人来说，这固然令人不安，但却是不争的事实。这并不是说 SWE 以后就无事可做了，只是直接手敲语法代码不再是我们的工作。

下午 4:02 · 2026 年 1 月 19 日 · 725 万次查看

970 条回复 · 2740 次转发 · 2.01 万次点赞](https://x.com/rough__sea/status/2013280952370573666?s=20)

- Ruby on Rails 的创始人 **David Heinemeier Hansson** 正经历着某种提前到来的怀旧情绪，一边手写代码，一边缅怀手写代码的时光：

[￰7￰

DHH@dhh

在文本编辑器里手写 Ruby 代码感觉就像是一种奢侈。也许这很快就会成为一门失传的艺术，但正因如此，我们才更应该在还能拥有这项特权时，尽情去享受它。

￰8￰

下午 2:11 · 2025 年 12 月 2 日 · 5.26 万次查看

54 条回复 · 44 次转发 · 968 次点赞](https://x.com/dhh/status/1995858288710476080?s=20)

- Claude Code 的创始人 **Boris Cherny** 表示：“我们几乎 100% 的代码都是由 Claude Code 配合 Opus 4.5 编写的。”

[￰9￰

Boris Cherny@bcherny

@karpathy 一如既往，你的见解非常深刻且论证严密。我一直读到了最后。我认为 Claude Code 团队本身可能就是行业发展方向的风向标。对于你提出的一些（并非全部）问题，我们有方向性的答案：1. 我们主要招聘通才。我们既有资深

凌晨 2:44 · 2026 年 1 月 27 日 · 129 万次查看

162 条回复 · 411 次转发 · 6850 次点赞](https://x.com/bcherny/status/2015979257038831967?s=20)

- 甚至连 **Linus Torvalds** 都在尝试氛围感编程：[https://github.com/torvalds/AudioNoise](https://github.com/torvalds/AudioNoise)

但这绝不仅限于程序员。在 SemiAnalysis，我们的分析师和技术人员分工明确，各司其职。数据中心模型团队每周需审查数百份文档。AI 供应链团队需核查包含数千个条目的 BOM（物料清单）。随着现货市场价格一路狂飙，存储模型团队需近乎实时地构建预测。技术人员则需维护 [InferenceMAX](https://inferencemax.semianalysis.com/) 的实时仪表板，包括每晚在 9 种不同系统类型/集群上运行最新软件配置。从监管文件到许可证，从规格书到说明文档，从配置到代码——我们与计算机的交互方式已然发生巨变。

举例而言，我们的行业模型分析师如今正使用 Claude Code 生成大量实用图表与分析，借此解析并传达海量数据集中的关键趋势：

以下是输入内容：

![](https://substackcdn.com/image/fetch/$s_!ds_u!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F456e53bb-cf1f-4e16-94cf-7ad23cb32e08_900x936.png)

来源：SemiAnalysis，Claude Code

以下是输出结果：

![](https://substackcdn.com/image/fetch/$s_!1CW1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F29cab5bf-fe5d-46e0-b93b-9caaf5a7d1ea_1043x585.png)

来源：SemiAnalysis，Claude Code

程序员将不再亲自敲代码，而是直接派发任务让 AI 代劳。Claude Code 的魔力就在于*它就是好用*。许多知名程序员终于顺应了这股“氛围感编程”的新浪潮；他们开始意识到，编程几乎已成一个被攻克的难题，交由智能体来承担，远胜于人类亲力亲为。

竞争焦点正在转移。痴迷于用线性基准测试来评判哪个模型“最强”将显得十分老派，这就好比还在比较拨号上网与 DSL (数字用户线路) 的速度差异。速度与性能固然重要，模型也确实是驱动智能体的引擎，但未来的性能衡量标准将是构建一个网站所需输出的数据包净总量，而非数据包本身的质量。未来的网站功能将依赖工具、记忆、子智能体以及验证循环的协同编排；其核心在于交付最终成果，而非仅仅生成回复。最终，所有信息工作都将被模型彻底接管。

Opus 4.5 正是让这一切成为可能的引擎。在线性基准测试中至关重要的指标，对于智能体长时程任务而言可能毫无意义。我们将在后文详细探讨这一点。

## 超越编程：是滩头阵地，而非终点

编程曾是最具价值的工作，在 2020 年代的软件工程热潮中，程序员可谓炙手可热。如今，面对智能体化信息处理掀起的颠覆狂潮，编程仅仅是一个抢滩阵地，规模高达 15 万亿美元的庞大信息工作经济已然岌岌可危。根据国际劳工组织（ILO）的数据，全球 36 亿劳动力中，信息工作者超过 10 亿，占比约达三分之一。

信息工作领域的各项工作流往往高度相似，均遵循一套已被 Claude Code 在软件领域验证行之有效的工作流：阅读（摄取非结构化信息）、思考（运用领域知识）、输出（生成结构化结果），最后验证（对照标准核查）。这构成了绝大多数信息工作者（甚至包括研究人员！）的核心工作内容。如果智能体（指能够自主规划并执行复杂任务的 AI）能够吞噬软件行业，还有哪个劳动力市场能独善其身？

我们认为，智能体必将席卷众多领域。随着 Claude Code（以及 Cowork）的强势崛起，智能体的总潜在市场（TAM）远超单纯的大语言模型（LLM）。客户支持和软件开发等垂直领域仅仅是起点，智能体必将大举进军金融服务、法律、咨询等更为庞大的行业。这正是 [SemiAnalysis Tokenomics 模型](https://semianalysis.com/tokenomics-model/)（译注：此处指作者为 AI 公司建立的专属财务分析模型，而非加密货币领域的代币经济学）的核心关注点。

![](https://substackcdn.com/image/fetch/$s_!UO8Q!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F322aa44f-6be7-4182-9a2a-d8845c6a81c5_1430x818.png)

来源：McKinsey，Mordor Intelligence，Grand View Research，Precedence Research。由 Claude Code 生成。

鉴于编程领域已跑出“杀手级用例”，且 Claude Code 与 Cowork 展现出清晰的通用性，我们必须采用一套截然不同的估值逻辑。将绝大多数问答交互和信息检索实现自动化已具备可行性，这将彻底打开商业变现的绝对天花板。随着智能体化 AI 全面渗透商业的各个角落，[Tokenomics 模型的核心目标](https://semianalysis.com/tokenomics-model/)便是持续追踪不断涌现的杀手级用例及其总潜在市场（TAM）。

### 落地瓶颈：任务视界

真正能让这块庞大蛋糕被全面颠覆的关键，在于更长的任务视界——即智能体在任务失败前，究竟能持续自主工作多久？METR 数据显示，自主任务视界每 4 到 7 个月就会翻一番（在 2024 至 2025 年间，这一翻倍周期将加速缩短至 4 个月左右）。

![](https://substackcdn.com/image/fetch/$s_!v-bP!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa27e004c-72b7-4058-a24e-f1c6c6c9266f_1430x880.png)

来源：METR，[SemiAnalysis Tokenomics 团队](https://semianalysis.com/tokenomics-model/)

任务视界每翻一倍，就能解锁更大份额的蛋糕。在 30 分钟的任务视界下，你可以自动补全代码片段；达到 4.8 小时，你就能重构一个模块。对于长达数日的任务，你甚至可以实现整个审计流程的自动化。显然，Anthropic 也看到了这一点。

2026 年 1 月 12 日，Anthropic 推出了 Cowork——“面向通用计算的 Claude Code”。4 名工程师仅用 10 天便完成了开发，其中绝大多数代码由 Claude Code 自主编写。它沿用了相同的架构：Claude 智能体 SDK、MCP 以及子智能体。它能根据收据生成电子表格，按内容对文件进行分类，并从零散笔记中起草报告。简而言之，它就是去掉了终端界面、加上了桌面环境的 Claude Code。

![](https://substackcdn.com/image/fetch/$s_!9b5Y!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff50e715d-28e1-4397-9514-ece12ddd3632_1049x664.png)

![](https://substackcdn.com/image/fetch/$s_!3fbT!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4d386d33-e530-49fd-9619-a8d72cbbc10d_1049x655.png)

这是未来图景的惊鸿一瞥。这套工作台能够理解你日常工作的上下文，并根据需要构建和生成信息处理流程。你不再需要从数据库下载数据再手动制作图表，智能体（指能够自主规划并执行复杂任务的 AI）会为你生成一份排版远超你手动操作 Excel 的报告。每当你需要收集诸如销售配额之类的信息时，你的智能体就会从 UI 或 API 中提取数据，并代你生成报告。信息工作本身必将走向自动化，就像 Claude Code 自动化软件工程一样。

![](https://substackcdn.com/image/fetch/$s_!qljZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6321004f-cff8-45ec-abcd-dddbc20b1d6f_936x474.png)

来源：SemiAnalysis – 由 Claude Code 根据我们的[Co-Packaged Optics 文章](https://newsletter.semianalysis.com/p/co-packaged-optics-cpo-book-scaling)生成。

尽管目前的系统尚未尽善尽美，但它在处理、整合与格式化数据方面的速度，显然已全面超越大多数人类。在某些场景下，其准确度不仅高于普通员工，成本也更为低廉。诚然，AI 幻觉依然存在，但现有的多数业务流程中本就充斥着大量人为错误。只要信息能以达标的准确度完成处理并流转至下一环节，单凭这一点就能大幅拉升工作产出供给。毫不夸张地说，我们已经到了这样一个节点：任何人都可以在这些智能体工作流中输入指令，轻松运行多变量回归分析——而在 21 世纪初，这往往需要长年的专业训练才能掌握。

[Stack Overflow 2025 年开发者调查](https://survey.stackoverflow.co/2025)显示，已有 84% 的程序员在使用 AI，这代表着技术普及的最前沿。然而，仅有 31% 的受访者在使用编程智能体，这意味着面对更广泛的信息工作浪潮，当前的渗透率曲线仍处于起步阶段。正如编程智能体在“眨眼之间”完成渗透一样，更广泛的信息工作领域也将迅速迎来 AI 的全面普及。

## 智能成本正在暴跌

软件工程过去是、未来也必将是信息工作的黄金标准。然而，随着模型质量终于跨越临界点，程序员与工具的从属关系已然反转。如今，程序员本质上只是在驾驭一个黑盒工具来交付结果。这一局面的出现，不仅得益于模型质量的跃升，更因为 token 智能的成本已呈断崖式下跌。现在，单凭一名借助 Claude Code 的开发者，就能完成过去一个团队耗时一个月的任务。

Claude Pro 或 ChatGPT 的订阅成本仅为每月 20 美元，高级 (Max) 订阅也只需 200 美元。相比之下，美国知识工作者的综合用工成本中位数高达每天 350 至 500 美元。如果一个智能体（指能够自主规划并执行复杂任务的 AI）每天能以 6 至 7 美元的成本处理哪怕一小部分工作流，就能创造 10 至 30 倍的投资回报率 (ROI)——这甚至还未将智能水平跃升带来的额外红利计算在内。

**企业已经开始行动**

智能成本的大规模通缩，必将重塑所有信息公司在重复性工作上的利润空间。[埃森哲刚刚签署协议，将对 3 万名专业人员进行 Claude 培训](https://newsroom.accenture.com/news/2025/accenture-and-anthropic-launch-multi-year-partnership-to-drive-enterprise-ai-innovation-and-value-across-industries)，创下迄今为止最大规模的 Claude Code 部署纪录。埃森哲将战略重心锁定在金融服务、生命科学、医疗保健以及公共部门，这些均是信息自动化领域亟待开发的庞大蓝海。与此同时，[OpenAI 刚刚发布了专注于企业级落地的 Frontier](https://openai.com/index/introducing-openai-frontier/)。

企业软件无疑已成为这场智能成本大跌的首个牺牲品。SaaS (软件即服务) 的本质，仅仅是将工作流的信息处理过程固化为代码。SaaS 赖以生存的三大护城河——数据切换成本（数据孤岛效应）、工作流锁定（用户对 UI 的学习成本），以及集成复杂度（例如 Slack 与 Jira 的协同）——均已从边缘开始逐渐瓦解。SaaS 高达 75% 的毛利率如今看来更像是一块巨大的肥肉：智能体能够在系统间低成本迁移数据，其自身运行完全不依赖面向人类的工作流，而 MCP (模型上下文协议) 的出现更是让系统集成易如反掌。SaaS 的各个环节都在迅速贬值，其丰厚的利润空间已然成为 AI 攻城略地的首个突破口。

举个最直白的例子：智能体现在可以直接代你查询 Postgres 数据库、生成图表，并将其邮件发送给利益相关方。这在过去本质上就是购买 CRM (客户关系管理) 等 SaaS 工作流所要付出的成本；而现在，你既不需要为了 UI 变更去培训员工，也不需要费心更新软件。它就是“开箱即用”。BI (商业智能) 与数据分析（智能体查询数据库）、数据录入、ITSM (IT 服务管理)（L1/L2 工单分发）以及后台对账，这些环节已经全面步入自动化进程！它们正强势叩响软件行业最坚不可摧的护城河大门。

我们认为，任何依赖人工点击按钮的操作，或是收集信息并将其重组为其他媒介（如邮件、图表、Excel、PPT）的工作，都正面临被淘汰的巨大风险。大语言模型 (LLM) 天生就是处理此类数据转换的绝佳好手，能够毫不费力地将文本转为音频、将英文译为中文、将文字生成图像。在我们看来，这必将对全球最大的公司之一构成巨大威胁：微软。

## 竞争格局（微软的困境）

成本暴跌正在摧毁按席位付费的软件模式。随着 SemiAnalysis 内部大规模采用 Claude Code，受份额转移冲击最严重的，莫过于微软按席位付费的 Office 365。微软堪称“人工点击按钮”模式的代名词，推而广之，它也代表了所有按席位付费的软件。值得关注的高危阵地，正是那些专为人类操作而设计、应用于跨行业工作流的软件。

如果智能体（指能够自主规划并执行复杂任务的 AI）能直接代你查询潜在客户数据，企业为何还要统一部署 Salesforce？Salesforce 本质上只是一个表单与工作流的封装外壳，而 AI 完全可以将这些表单与工作流直接构建为底层数据库，并按需执行查询。任何细枝末节的 UX（用户体验）或操作偏好都已岌岌可危。Tableau 的核心概念已经过时；Figma（专供人类绘制线框图的工具）也面临危机。人机交互的核心方式即将发生根本性变革，而微软正处于旧范式的中心。

## 夹在两项业务之间

我们最近（错误地）预测微软营收将加速增长，这主要归因于其庞大的算力租赁集群以及向外部晶圆代工厂（foundry）产能的转移。但我们认为，在最近的财报电话会议上，他们决定进行战略性收缩。以下是原话：

> “我认为，大家近期看到我们在产品端的大幅加速，很大程度上是因为我们正将 GPU 和算力分配给过去几年招募的大批顶尖 AI 人才。最终的结果是，只有剩余的算力才被用于满足 Azure 持续增长的需求。我有时会被问到这个问题，大家可以这样想：如果我把第一季度和第二季度刚刚上线的 GPU 全部划拨给 Azure，那么关键绩效指标 (KPI) 早就超过 40 了。”

这里的关键背景在于：

> “我们确实在做长期决策。**我们的首要任务是应对销售端使用量的激增，以及 M365 Copilot、GitHub Copilot 或第一方应用加速普及的趋势**。随后，我们要确保对**具有长期属性的研发和产品创新**进行投资。”

微软内部盘踞着两头巨兽：一是迎合公开市场投资者的 Azure 增长，二是旨在保卫 Office 365 产品矩阵的 Copilot 投资。想要在其中一端大获全胜，大概率就必须牺牲另一端。眼下，对 OpenAI 和 Anthropic 这类公司而言，微软已是全球最大的 AI 云平台之一。然而，他们实际上是在将 GPU 租给那些注定会摧毁其生产力软件自家城堡的野蛮人。

Claude for Excel 实际上呈现了 Copilot for Excel 理想中的终极形态，**但这却是由外部公司在微软自家的第一方产品上实现的**。如今，微软的大部分现金流依然仰仗 Office，但其大部分终值却寄托于 Azure 的营收增长。想要为 Azure 提速，就势必会任由兵临城下的野蛮人更快地推倒城墙。微软固然已与这些 AI 新贵结盟，但随着 OpenAI 和 Anthropic 逐渐壮大为成熟平台，微软的护城河还能否将其拒之门外，已成未知数。

讽刺的是，微软在 AI 领域的支出*必须继续加码*，否则 O365 产品矩阵的终值必将一路陡降。他们确实手握渠道分发优势，但这主要依附于一款定位正被 AI 新贵们日渐蚕食的产品。与此同时，作为微软在 AI 领域的核心盟友，OpenAI 自身也正遭受 Claude Code 在企业级市场的颠覆性冲击。面对 Claude Code 在智能体化应用上的强势崛起，OpenAI 必须迅速予以反击，否则他们自己也会沦为一家基础设施公司（卖 token），而非解决方案公司（卖智能体）。被颠覆的风险正在急剧攀升，而这一切正真真切切地发生在史上最赚钱的巨头之一身上。

GitHub Copilot 和 Office Copilot 虽抢占了一年的先发优势，但在产品层面却几乎未见实质性突破。与此同时，Satya 甚至亲自下场担任[微软 AI 的产品经理](https://www.businessinsider.com/microsoft-ceo-satya-nadella-ai-revolution-2025-12?utm_source=reddit&utm_medium=social&utm_campaign=insider-artificial-sub-post)，暂缓了作为首席执行官 (CEO) 的日常管理事务。局势已然明朗：这一款单兵产品的成败，押上的很可能是整个公司的命运。

## Anthropic 的融资与崛起：为什么赢的是 Anthropic？

这场争论中最引人深思的问题之一在于：过去一年里，GPT-5.2 High 一直在狂卷基准测试（Benchmark-maxxing，即极度追求跑分数据），并在自 ChatGPT 崛起以来的两年间稳居霸主地位。两者的 SWE-bench 验证结果基本持平，GPT-5.2 在 MMLU-pro 和 AIME 2025 上的得分甚至更高，但所有人却都对 Opus 趋之若鹜。那么，为什么 Claude Code 能够占据统治地位？

![](https://substackcdn.com/image/fetch/$s_!Emov!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0a2d6df3-68a8-4a9b-bb3d-5cab6dbb3db1_1430x1486.png)

来源：[SemiAnalysis Tokenomics 团队](https://semianalysis.com/tokenomics-model/)，Artificial Analysis，Chatbot Arena，由 Claude Code 生成

答案在于 Token 效率。Opus 4.5 的 Token 效率远超 GPT-5.2 High，这对完成长周期任务至关重要。

![](https://substackcdn.com/image/fetch/$s_!huRl!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff13013ab-dc6a-4355-9261-68aa478cf6ea_2025x1453.png)

来源：Artificial Analysis，[SemiAnalysis Tokenomics 团队](https://semianalysis.com/tokenomics-model/)，由 Claude Code 生成

长周期性能的本质，是在跨越多个上下文窗口的多步操作中持续叠加有效信号。尽管 ChatGPT 拥有大得多的上下文窗口，但“任务-token”效率曲线却揭示了截然不同的真相。唯基准至上 / 卷基准的 ChatGPT 或许在评估中得分更高，但完成实际任务所需的 token 数量却高出一个数量级，这直接摧毁了任何长周期规划的可行性。

我们认为，这是 Anthropic 筹谋已久的战略选择。关键不在于堆砌海量 token（这会在产生部分有效信号的同时引入大量噪声），而在追求极致纯净的信噪比。在跨上下文窗口的规划中，这一点至关重要，因为任何误差的不断累积都会导致长周期任务彻底失败。

![](https://substackcdn.com/image/fetch/$s_!Y25K!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc7b2dbfa-6b85-4d08-b665-1fdeaebe9b95_2105x1299.png)

来源：[SemiAnalysis Tokenomics 团队](https://semianalysis.com/tokenomics-model/)，由 Claude Code 生成

如果单次上下文窗口需要达到 90% 的成功率，在跨越 X 个步骤进行连乘叠加后，哪怕单步错误率极小，也注定会导致最终任务失败。

![](https://substackcdn.com/image/fetch/$s_!W7M1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7da088ff-4352-4681-9baa-df566ac3dbee_787x443.png)

来源：Weka

Anthropic 显然极度重视 Token 效率。据传，全新的 Sonnet 5 模型体积大幅缩小，上下文窗口更大，且性能与 Opus 4.5 旗鼓相当。这在扩大上下文窗口的同时，有效推高了高效 token 曲线的绝对上限。对于编程智能体（指能够自主规划并执行复杂任务的 AI）而言，其实际性能的差异将是天壤之别。这正是 Anthropic 领先于 OpenAI 的身位优势。

OpenAI 必将反击，也必须反击。全新的预训练是先决条件，因为更大规模似乎能改善长上下文任务的表现。去年 OpenAI 模型之所以如此强大，全凭极长的思维链 token 上下文来完成任务。然而，在处理跨越多个上下文窗口的问题时，这种优势却沦为累赘，因为它会不断叠加噪声。破局之法很直接：重新进行预训练。我们预计未来几个月内会有新动作，但在此之前，Anthropic 依然稳占鳌头。OpenAI 代码生成模型的实际采用率，远比乍看之下要低得多。

![](https://substackcdn.com/image/fetch/$s_!rsVn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9feb4401-1aee-4794-9742-058453165cb3_2009x1260.png)

*SemiAnalysis Tokenomics 团队，NPM*

尽管 VSCode 上的数据表现要亮眼得多，但考虑到 GitHub 坐拥“数百万”开发者，单看 VSCode 的安装量往往无法精准反映其实际使用情况。

![](https://substackcdn.com/image/fetch/$s_!fQeQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5d00375f-d5c5-46ea-a6ed-1b5b49bec853_1050x522.png)

来源：[Bloomberry.com](https://bloomberry.com/coding-tools.html)

2025 年一家独大的竞争格局，到 2026 年看起来更像是一场三足鼎立的角逐：Gemini 凭借图像模型，在 ChatGPT 曾经称霸的 C 端市场领跑；而 Anthropic 则在 B 端落地与智能体领域拔得头筹。

## 预训练还重要吗？

一个更有趣的问题是：预训练本身还重要吗？如果将智能体比作 TCP/IP 协议，那么优化协议中的数据包（packets），其重要性可能远不如优化协同功能。Kimi 2.5 就是一个例证。该版本发布中最引人注目的信息，并非其顶尖的基准测试性能，而是其智能体编排能力。

今年发布的每一个增量模型，都将更侧重于智能体编排及性能，这与去年业界对推理能力的追逐如出一辙。随着 Anthropic 超越了单纯的基准测试，仅仅比较模型间的性能已无意义，未来的关键在于智能体协同能达成何种成就。OpenAI 可能因此被打了个措手不及，错失了这一战略拐点。正如 Anthropic 和 Gemini 最初未能完全理解或推动 RL 和思维链的变革一样，现在看来，Anthropic 正引领着智能体化的拐点。

月之暗面 (Moonshot AI) 的 Kimi 2.5 完美展示了未来模型的形态。Kimi 将全部精力集中在编排层上。在 Kimi 2.5 的发布中，除了智能体编排层，其他所有部分都已开源。其并行智能体强化学习 (PARL) 技术预示了未来的发展方向。根据内部基准测试，通过运用智能体，Kimi 的性能表现已超越 Opus 4.5。例如，Sonnet 5 的设计显然也面向智能体集群，其工作方式与 Kimi 2.5 的 PARL 技术颇为相似。

Kimi 2.5 全新的编排引擎（未开源）

![](https://substackcdn.com/image/fetch/$s_!fOEe!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffce483cf-4a0a-4291-b937-6650a5ed848c_1191x646.png)

来源：[Kimi 论文](https://www.kimi.com/blog/kimi-k2-5.html)

![](https://substackcdn.com/image/fetch/$s_!psG2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2260d62d-0cce-4be8-9cb6-e50fdf9dae6f_1183x627.png)

*来源：Kimi 2.5*

智能体编排就是新的 CoT。智能体（指能够自主规划并执行复杂任务的 AI）的大规模并行化将成为下一代核心能力，其作用逻辑与更长的思维链 Token 带来更优结果如出一辙。很快，系统将大规模生成成群结队的智能体大军，以完成各项任务！

![](https://substackcdn.com/image/fetch/$s_!kH7c!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F67c9c93f-d03a-4dd6-8d5a-30b0c61bb846_1191x688.png)

*来源：Kimi 2.5*

这一前沿阵地潜力巨大，堪比最初 o1 模型实现的性能飞跃。但这是第一次，领跑者不再是 OpenAI。

然而，在为智能体无限扩展感到兴奋之前，有一个问题必将成为今年真正的竞争焦点。Anthropic 在[近期研究](https://alignment.anthropic.com/2026/hot-mess-of-ai/)中发现：“**在所有任务和模型中，模型花费在推理和执行动作上的时间越长，其表现就越语无伦次。无论我们衡量的是推理 Token、智能体动作还是优化器步数，这一结论都成立**。”

[模型的重度用户也反馈了同样的情况](https://x.com/NathanFlurry/status/2014876907247149251)，本文作者也基本认同这一观点：更长的上下文窗口最终会退化为语无伦次的输出。

![](https://substackcdn.com/image/fetch/$s_!YQxQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcbc120a1-eddc-42f4-b5ef-100791815e28_997x633.png)

来源：Anthropic

这凸显了 Anthropic 在 token 效率方面的优势。这也解释了为什么我们认为，用最少的 token 完成任务将成为核心的质量基准之一。单一上下文窗口内的连贯性越强，智能体（指能够自主规划并执行复杂任务的 AI）的扩展空间就越大。模型层面的 token 效率很可能将揭示谁才是真正的领跑者。

然而，在 Claude Code 强势崛起之际，制约 Anthropic 的是 FLOPS 和电力（MW），而非模型能力。这种非消费者驱动的新一轮需求爆发，是 2026 年值得关注的关键拐点。用户增长加速必然带来计算需求飙升。我们认为，Anthropic 即将达成的 3500 亿美元估值，将为其大规模进军吉瓦（GW）级电力博弈提供充裕资金。下图展示了 Anthropic 正在推进的电力追赶态势。

![](https://substackcdn.com/image/fetch/$s_!7xxX!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7572d353-1443-483a-a286-4cb33d1413f9_927x585.png)

*来源：SemiAnalysis [Tokenomics 模型](https://semianalysis.com/tokenomics-model/)*

Anthropic 正是凭此制胜。但现在轮到 OpenAI 向世界证明，他们能够预训练出新模型，并有望重夺领跑地位。这场竞赛似乎比去年更具悬念，我们对持续变革的步伐感到兴奋。

在文章最后，我们将分享 SemiAnalysis 团队与我们的新晋霸主 Claude Code 共同完成的一些信息处理工作。眼见为实。我们笃定自己正处于一个全新时代：在这个时代，创建软件和处理信息的边际成本已降至零。从此刻起，事物变革的速度将不断加快。

## SemiAnalysis Vibe Coding 展示与讲解

这是一份 API 延迟测试，通过对比 ISO/OSL 来计算 24 小时内的延迟情况。

![](https://substackcdn.com/image/fetch/$s_!yHky!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1cded36f-1f27-48a0-b7c9-b355b892b219_624x386.png)

来源：SemiAnalysis，Doug 的 Claude Code

这是一个[由 Jordan 通过“氛围感编程”（vibe coding，指主要依靠 AI 辅助而非手写代码的开发方式）构建](https://www.learntheworld.ai/)的网站，旨在了解世界。

![](https://substackcdn.com/image/fetch/$s_!K968!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4f9d3c95-7b19-4034-b339-9b0eee5826d8_624x474.png)

来源：SemiAnalysis，Jordan 的 Claude Code

这是一份对比 Token 效率的 CLI (命令行界面) 基准测试。Kimi 的 2.5 版本表现相当不错，但会消耗大量 token。这正是 Token 效率的直观体现；即便每秒 token 数较低，实际达到的速度也可能快得多。

![](https://substackcdn.com/image/fetch/$s_!_63p!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe3cb2e9c-243f-4694-87a3-1ab0cbc26c15_624x264.png)

来源：SemiAnalysis，Doug 的 Claude Code

这是 Doug 为未婚妻通过“直觉编程”构建的一款电子游戏。

![](https://substackcdn.com/image/fetch/$s_!kmZX!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1588d70f-987e-4a15-98cc-abddaf449ed5_1045x662.png)

来源：SemiAnalysis，Doug 的 Claude Code。你可以从底部的小游戏中赚钱，哈哈。

这是一张对比台积电（TSMC）与恩特格里斯毛利率的图表。此处的毛利率已包含针对收购的备考调整。

![](https://substackcdn.com/image/fetch/$s_!Ibgr!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff18504c8-f5aa-4e9d-969b-785d90646866_1056x526.png)

来源：SemiAnalysis，Doug 的 Claude Code

各位，知识工作的世界已被彻底颠覆。这势必重创几乎所有的现有巨头。绝不要相信那些声称“这对软件公司是利好，能让他们卖出更多软件”的论调。就像“互联网广播”根本是个伪命题一样（译注：指新技术会诞生全新的业态，而非简单地将旧模式搬上新平台）。

**结论：模型即新的 TCP/IP**

在 20 世纪 70 和 80 年代，TCP/IP 面临着激烈的竞争。OSI 模型、IBM 的 SNA (系统网络架构)、Novell IPX/SPX 以及其他协议都曾参与角逐。但正如你现在所知，没人再关心这些底层协议，真正重要的是构建在互联网数据包之上的优质信息。我们目前正处于同样关键的历史节点，而 Claude Code 就是首个证明。如今，GitHub 上每天有 4% 且仍在不断攀升的代码量，仅由 Claude Code 一己之力生成。

未来的核心在于智能体（指能够自主规划并执行复杂任务的 AI）如何驾驭海量 token，从而构建规模更庞大、质量更卓越的项目。Claude Code 犹如初代网站，为我们提供了窥探更深远智能体化未来的最佳窗口。信息工作即将迎来实质性的加速，竞争必将呈指数级飙升。

***分析师认证与研究独立性。** 本报告署名的每位分析师特此证明，本报告中表达的所有观点均准确反映了我们对任何及所有标的证券或发行人的个人看法，且我们的薪酬中没有任何部分曾经、现在或将来会直接或间接与本报告中的具体建议或观点相关。SemiAnalysis LLC（以下简称“本公司”）是一家独立的股票研究机构。本公司并非美国金融业监管局 (FINRA) 或美国证券投资者保护公司 (SIPC) 的成员，亦非注册的经纪交易商或投资顾问。SemiAnalysis 没有任何其他受监管或不受监管的业务活动会与其提供独立研究产生冲突。*

***研究与信息限制。** 本报告仅供分发给 SemiAnalysis LLC 的合格机构或专业客户。本报告的内容代表其作者的观点、意见和分析。本文包含的信息不构成金融、法律、税务或任何其他建议。本文提供的所有第三方数据均来自被认为可靠的公开来源；然而，本公司不对该等信息的准确性或完整性作出任何明示或暗示的保证。在任何情况下，本公司均不对任何此类材料的正确性或更新负责，亦不对因使用这些数据而导致的任何损害或错失的机会承担责任。 本报告或本公司分发的任何内容均不应被解释为出售任何证券或投资的要约，或购买任何证券或投资的要约邀请。收到的任何研究或其他材料均不应被视为个性化的投资建议。投资决策应作为整体投资组合战略的一部分来制定，在做出任何投资决策之前，您应咨询专业的财务顾问、法律和税务顾问。对于基于从 SemiAnalysis LLC 获得的信息或研究而做出的任何投资决策所引起的任何直接或间接、附带或后果性的损失或损害（包括利润、营收或商誉的损失），SemiAnalysis LLC 概不负责。*

***严禁复制与分发。** 本报告的任何用户均不得复制、修改、复印、分发、出售、转售、传输、转让、许可、让与或出版报告本身或其中包含的任何信息。尽管有上述规定，获准访问工作模型的客户可以更改或修改其中包含的信息，前提是仅供该客户自行使用。本报告无意为任何被当地、州、国家或国际法律法规视为非法或以其他方式禁止的目的而提供或分发，亦无意使本公司在此类司法管辖区内接受任何形式的注册或监管。*

***版权、商标与知识产权。** SemiAnalysis LLC 以及本报告中包含的任何徽标或标志均为专有材料。未经 SemiAnalysis LLC 明确书面同意，严禁使用此类术语、徽标和标志。除非另有说明，本报告页面或屏幕以及其中的信息和材料的版权，均为 SemiAnalysis LLC 拥有的专有材料。未经授权使用本报告上的任何材料可能违反众多法规和法律，包括但不限于版权、商标、商业机密或专利法。*
