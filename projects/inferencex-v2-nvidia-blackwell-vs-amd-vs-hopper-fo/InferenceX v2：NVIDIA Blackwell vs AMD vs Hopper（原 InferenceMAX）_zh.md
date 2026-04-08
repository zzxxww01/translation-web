# InferenceX v2：NVIDIA Blackwell vs AMD vs Hopper（原 InferenceMAX）

### GB300 NVL72、MI355X、B200、H100、分离式服务、宽专家并行、大规模混合专家模型、SGLang、vLLM、TensorRT-LLM（TRTLLM）

作者：[Dylan Patel](https://substack.com/@semianalysis)、[Cam Quilici](https://substack.com/@camjquilici)、[Bryan Shan](https://substack.com/@cheese01) 等 7 人

2026 年 2 月 16 日 · 付费文章

## 引言

InferenceXv2（前身为 InferenceMAX）在 InferenceMAXv1 奠定的基础上构建，后者是[我们开源且持续更新的推理基准测试（benchmark）](https://github.com/SemiAnalysisAI/InferenceX)，为 AI 推理性能与经济性树立了新标杆。InferenceMAXv1 摒弃了静态、特定时间点的基准测试，转而对数百款芯片和主流开源框架进行持续测试。[点击此处查看免费数据看板。](https://inferencemax.ai/)

[我们的基准测试已被几乎所有主要算力买家广泛复现、验证或支持](https://inferencemax.semianalysis.com/quotes)，涵盖从 [Google Cloud](https://cloud.google.com/blog/products/compute/scaling-moe-inference-with-nvidia-dynamo-on-google-cloud-a4x)、[Microsoft Azure](https://blog.aks.azure.com/2025/10/24/dynamo-on-aks#enterprise-scale-inference-experiments--dynamo-with-gb200-running-on-aks) 到 [Oracle、OpenAI](https://inferencemax.semianalysis.com/quotes) 等众多头部企业。

InferenceXv2 正是建立在这一基础之上。它扩大了测试范围，纳入了采用宽专家并行（WideEP）优化的大规模 DeepSeek 混合专家模型（MoE）分离式推理（分离式预填充，简称“分离式”），覆盖了**过去 4 年英伟达面向西方市场推出的全部 6 款 GPU SKU (库存单位/型号)**，以及过去 3 年 AMD 面向西方市场发布的每一款 GPU SKU。总体而言，InferenceXv2 调用了近 1000 张前沿 GPU，以完成跨所有 SKU 的完整基准测试运行。

随着今日发布，InferenceXv2 成为首个跨越整条帕累托前沿曲线对 Blackwell Ultra GB300 NVL72 机架级系统和 B300 进行基准测试的套件；同时，它也是首个测试在 MI355X 上组合使用 FP4 与 FP8、分离式架构以及宽专家并行时多节点性能的第三方基准测试。在 InferenceX 的未来迭代中，我们将继续重兵投入采用宽专家并行的分离式服务，因为这正是 OpenAI、Anthropic、xAI、Google Deepmind、DeepSeek 等前沿 AI 实验室，以及 TogetherAI、Baseten 和 Fireworks 等先进 API 提供商在生产环境中实际部署的方案。在本文中，我们还将深入剖析围绕[最新的 Claude Code 快速模式功能](https://code.claude.com/docs/en/fast-mode)所涉及的系统工程原理与经济学逻辑。

我们的基准测试在 Apache 2.0 协议下完全开源——这意味着我们能够与 AI 软件生态系统的演进保持同样的高速迭代。如果你认可我们的工作并希望提供支持，[请在我们的 GitHub 上点个 Star](https://github.com/SemiAnalysisAI/InferenceX)！我们还在 [https://inferencex.com](https://inferencex.semianalysis.com/) 提供了免费的数据可视化工具，供机器学习社区的所有人自行探索完整数据集。

我们将在首日（day 0）即刻支持并加入 DeepSeekv4 及其他热门的中国前沿模型，因为在过去 6 个月里，我们已经清理了大量技术债，如今能够[在稳定的基础设施上快速迭代](https://www.cnet.com/tech/mobile/zuckerberg-move-fast-and-break-things-isnt-how-we-operate-anymore/)。今年晚些时候，我们还将把 TPUv7 Ironwood 和 Trainium3 纳入 InferenceX！如果你渴望参与这项极具影响力的使命，同时获得极具竞争力的薪酬，[欢迎在此申请加入我们](https://app.dover.com/apply/semianalysis/2a9c8da5-6d59-4ac8-8302-3877345dbce1)。

![](https://substackcdn.com/image/fetch/$s_!CCx-!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1e9a8353-ca83-4bd3-ab4a-3541132f6665_1680x1175.png)

来源：[InferenceMAX GitHub](https://github.com/SemiAnalysisAI/InferenceX)

## 核心观察与重点结果

在对比 AMD 平台上采用 FP8 精度、分离式预填充（disagg prefill）加宽专家并行（WideEP）的 SGLang 与英伟达 B200 上同等配置的 SGLang 时，我们发现 MI355X 展现出了极具竞争力的单位 TCO 性能。然而，一旦与广泛使用的 Dynamo TensorRT-LLM (TRTLLM) B200 FP8 配置相比，TRT 依然呈现降维打击之势。即便如此，AMD 的 SGLang 在 FP8 分离式预填充加 WideEP 配置下能够追平英伟达的 SGLang 性能，这依然是个极其振奋人心的消息。

我们还发现，在单节点集成式服务场景下，AMD 的 SGLang 在 FP8 精度上提供了比英伟达 SGLang 更优的单位 TCO 性能。[令人欣慰的是，AMD 已经废弃了他们那个二流的 vLLM 分支，转而更积极地向上游靠拢，向提供一流体验迈进了一大步。](https://x.com/vllm_project/status/2013928644302033208)敬请期待我们的《AMD 现状》一文，我们将在其中探讨 AMD 进展神速的诸多领域，以及那些差强人意的短板。我们建议英伟达在 TRTLLM 引擎之外，进一步加码对 SGLang 和 vLLM 生态系统的投入。[黄仁勋需要调配更多资源和工程师，为 SGLang 和 vLLM 等开放生态做出贡献](https://www.linkedin.com/in/akbarnurlybayev?trk=feed-detail_main-feed-card_feed-actor-image)。

SemiAnalysis 的 InferenceX 是一款免费开源软件，由读者提供支持。若想接收最新文章并支持我们的工作，请考虑成为免费或付费订阅者。

当谈及最顶尖的前沿大规模推理服务所采用的最新推理技术（如分离式预填充+WideEP+FP4）时，英伟达凭借 B200、B300 以及堪称“ASU 兄弟会老大”（译注：形容其极具统治力）的 GB200/GB300 NVL72 机架级系统，在 SGLang 和 TRTLLM 上均实现了全面的降维打击。英伟达 GPU 在能效方面同样占据统治地位，在所有工作负载下，每个 token 的综合配置能耗（皮焦耳级别）都要低得多。

反观 AMD，我们发现其系统与软件在推理上面临的最大问题在于*[可组合性](https://en.wikipedia.org/wiki/Composability)*。也就是说，AMD 的许多推理优化方案在单独运行时表现良好，但与其他优化手段组合使用时，结果却远不如预期那般具备竞争力。具体而言，分离式预填充、WideEP 以及 FP4 推理优化之间的可组合性亟待大幅提升。

虽然在仅开启部分业界领先的推理优化时，AMD 的性能尚具竞争力，但一旦同时开启前沿实验室常用的这三大核心优化，AMD 目前的性能便无法与英伟达抗衡。我们强烈建议 AMD 将重心放在不同推理优化的可组合性上。有消息称，AMD 将开始在整个软件栈层面发力解决 FP4 加分布式推理的软件可组合性问题。这项工作将在农历新年后展开，因为他们大部分负责分离式预填充加 WideEP 的“10 倍速”推理工程师都常驻中国。

英伟达的 GB300 NVL72 机架级系统 没有让人失望。即便与强悍的 H100 分离式预填充+WideEP+MTP（多 Token 预测）基准相比，它在 FP4 精度下相比 H100 的 FP8 精度实现了高达 100 倍的性能飞跃，而在同等 FP8 精度对比中也达到了 65 倍。在 H100 与 GB200 NVL72 机架级系统 的较量中，我们观察到在每秒每用户 75 个 token（tok/s/user）的吞吐量下，实际性能差距高达 55 倍。Blackwell NVL72 机架级系统 正在对 Hopper 架构实施降维打击，衬托得 Hopper 简直像个纯纯小丑。正如黄仁勋在 GTC 2025 大会上所言，[他是首席营收毁灭者。](https://newsletter.semianalysis.com/i/174558496/ai-total-cost-of-ownership-cost-declines)

在 GTC 2024 大会上，黄仁勋宣称 Blackwell 的推理性能将比 H100 提升高达 30 倍，而他在 Blackwell 推理性能上显然是低调承诺、超额交付。这应该能让分析师们在未来一段时间内少拿“黄氏数学”开玩笑了。

![](https://substackcdn.com/image/fetch/$s_!HfJD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2ed3fe4a-93e9-4c47-8fb2-91f17da1b7c5_2392x1418.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## 致谢与 InferenceX™（原 InferenceMAX）倡议支持者

我们在此感谢黄仁勋和 Ian Buck 对这项开源工作的鼎力支持，他们不仅为我们开放了最新 GB300 NVL72 机架级系统的访问权限，还提供了涵盖其过去四年生产的所有 GPU SKU 的服务器。我们要感谢英伟达团队允许我们在这近 1000 张 GPU 上开展独立基准测试。感谢 Jatin Gangani、Kedar Potdar、Sridhar Ramaswamy、Ishan Dhanani、Sahithi Chigurupati 以及众多其他英伟达推理工程师，协助我们验证并优化 Blackwell 与 Hopper (架构) 的配置。

我们同样感谢苏姿丰和 Anush Elangovan 对 InferenceMAX 的大力支持，并促成了我们与 Chun、Andy、Bill、Ramine、Theresa、Parth 等数十位 AMD 工程师的合作。这些工程师不仅为 InferenceMAX 及上游 vLLM/SGLang 的 Bug 修复贡献了力量，还在协助调试与分类排查 AMD 平台特有的 Bug 时展现了极高的响应速度，切实助力优化了 AMD 的性能。

我们还要特别鸣谢 SGLang、vLLM 和 TensorRT-LLM 的维护者，他们构建了世界级软件栈并将其全面开源。您可以在此查看他们关于 InferenceX 的文章：

- [SemiAnalysis InferenceMAX：vLLM 维护者与英伟达加速 Blackwell 推理](https://blog.vllm.ai/2025/10/09/blackwell-inferencemax.html)

- [GPT-开源软件 (OSS) 性能优化：推高帕累托前沿](https://blog.vllm.ai/2026/02/01/gpt-oss-optimizations.html)

- [SGLang 与英伟达携手加速 SemiAnalysis InferenceMAX 与 GB200](https://lmsys.org/blog/2025-10-14-sa-inference-max/)

InferenceX 计划还得到了众多核心算力买家及机器学习 (ML) 社区重量级成员的支持，包括来自 OpenAI、微软、vLLM、PyTorch 基金会、甲骨文等机构的专家，以及 Tri Dao 等个人。[点击此处查看完整名单](https://inferencemax.semianalysis.com/quotes)。

SemiAnalysis InferenceX 是一款免费开源软件，依靠读者支持运营。欢迎成为免费或付费订阅者，以获取最新文章并支持我们的工作。

## 核心技术概念解析

在本节中，我们将提供一份简短的技术概念入门指南，帮助读者更好地解读结果。部分读者可能不需要这部分内容，可以直接跳到我们的结果分析。在结果分析之后，我们将对其中一些主题进行深度探讨。

## 交互性与吞吐量的权衡

LLM 推理的根本权衡在于吞吐量与延迟。*交互性* (tok/s/user) 衡量系统向每位用户返回 token 的快慢，它是每个输出 Token 的时间 (TPOT) 的倒数。*吞吐量* (tok/s) 则衡量系统在所有用户中总共能产出多少 token。通过批处理请求可以实现更高的总吞吐量，但分配给每个请求的 FLOPS 会减少，导致完成速度变慢。这就像是在乘坐公交车和赛车之间做选择。公交车能服务众多乘客，但频繁停靠会耗费时间，不过其成本可以分摊到众多乘客身上。 赛车只能搭载一两名乘客，但几乎中途不停，整体行程更快，不过单客乘坐成本要高得多。周末去公园游玩的人可能更适合坐公交车，而护送名人前往目的地则更适合用赛车。这里没有放之四海而皆准的解决方案。

![](https://substackcdn.com/image/fetch/$s_!M543!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F18c9a3dd-3777-44d5-a3e2-b4d28140df38_2106x1380.png)

来源：SemiAnalysis

本文展示的大多数 InferenceX 基准测试结果都呈一条曲线。必须分析不同交互性/延迟水平下的吞吐量，而非仅仅盯着最高吞吐量（通常只能在单一的低交互性下实现）。推理领域不存在万能的用例。所需的交互性和吞吐量水平取决于具体应用场景。例如，实时语音模型要求极低的延迟，确保最终用户能与 LLM 保持自然的“对话”；而基础的问答聊天机器人则可以容忍较高的延迟。读者可以自行查看曲线，并运用这一原则来确定自己的用例在吞吐量-交互性曲线上的具体位置。

单位 TCO 性价比与交互性/端到端延迟曲线，基本与吞吐量与交互性/端到端延迟曲线走势一致：每小时生成的 token 越多，分摊到每个 token 上的固定小时成本就越低，从而降低了单 token 成本。

### 预填充与解码阶段

推理包含两个主要阶段：预填充和解码。*预填充*发生在请求生命周期的首次前向传播期间。由于请求中的所有 token 都在并行处理，该阶段属于计算密集型。此阶段负责为序列“填满”KV 缓存。预填充结束后，系统会逐个 token 地生成（或*解码*）响应。每次前向传播都会从 HBM 加载该序列的完整 KV 缓存，却只执行单个 token 的计算，这使得解码成为内存（带宽）密集型操作。

若预填充与解码在同一引擎上执行，预填充会频繁打断解码批次，拖累整体性能。

### 分离式预填充

分离式预填充（又称 PD 分离 (预填充-解码分离)，或简称“分离”）是指将预填充与解码阶段拆分，分别交由独立的 GPU 资源池或集群来处理。这些相互独立的预填充池与解码池可进行独立调优，并弹性缩放以适配工作负载需求。

## 张量并行、专家并行与数据并行（TP、EP、DP）

张量并行（TP）能在小批次下实现交互性 (tok/s/user) 最大化，但必须在每一层执行全量归约。专家并行（EP）通过专家分片来利用混合专家（MoE）的稀疏性。其缺点在于，MoE 层需要执行全对全集合通信（成本高于全量归约等简单集合通信），且在小批次下容易出现负载不均。数据并行（DP）将整个模型（或注意力机制等部分模型）复制到多组 GPU（Rank）上，随后在各 Rank 之间对请求进行负载均衡。这种方式扩展最简单，但会重复加载权重，在规模扩大时容易造成资源浪费。

## 性能演进追踪

InferenceX 的主要目标之一，是直观呈现性能随时间推移的提升轨迹。尽管新芯片按 O(年)级别周期发布，但软件的发布却遵循 O(周)级别周期。我们的目标是，持续将最新、最优的软件改进融入配置方案 (Recipes) 中，并对这些配置进行基准测试。

## DeepSeek R1

AMD 团队已大幅提升了 SGLang DeepSeek R1 FP4 所有配置的性能。在同等交互性下，AMD 仅用不到两个月的时间，就将吞吐量几乎翻了一番。此外，我们还敦促 AMD 将其魔改版 SGLang 镜像中提升性能的改动合入上游官方 SGLang 镜像。从 2025 年 12 月到 2026 年 1 月，AMD 的软件性能实现了高达 2 倍的提升。

![](https://substackcdn.com/image/fetch/$s_!Jjej!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd0bd5df8-c675-4dce-a853-dfa6f4d381af_1498x1102.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?g_model=DeepSeek-R1-0528&g_rundate=2026-02-02&g_runid=21577661184&i_seq=8k%2F1k&i_prec=fp4%2Cfp8&i_gpus=mi355x_sglang&i_dstart=2025-12-14&i_dend=2026-01-29&i_hc=1#inference)

为了不断逼近一流的使用体验，AMD 必须加大对 vLLM 和 SGLang 维护者的支持力度，不仅要贡献算力与代码，还要安排更多 AMD 内部审查人员，加速将 AMD 的 PR (Pull Request) 审核并合入上游。

![](https://substackcdn.com/image/fetch/$s_!lFtH!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff7fc9e49-b04b-41b0-b0ec-df0d912c0a3c_800x434.jpeg)

来源：SemiAnalysis

另一方面，英伟达的测试结果则更为稳定，在同期内 B200 SGLang 的性能仅有小幅提升。

![](https://substackcdn.com/image/fetch/$s_!nuP1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F19e48a4c-0c1b-4681-b180-03ef0c8c2ce3_2346x1340.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

许多成熟的 SKU 性能提升微乎其微。例如，自 10 月以来的四个月里，H200 TRT 单节点的性能毫无变化。这是因为 Hopper 从发布首日起就获得了极佳的软件支持，其在该工作负载下的性能一直逼近理论峰值，因此很难再挤出额外的性能提升。

![](https://substackcdn.com/image/fetch/$s_!_wVx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fca0fbb96-36c4-4040-a022-49f2185b661a_2074x1224.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

MI300X 和 MI325X 取得了一些性能提升，这主要归功于最新发布的 SGLang 版本。需要注意的是，在 InferenceX 的大部分历史测试中，AMD 使用的都是未推送到上游的“私有” ROCm 镜像，因此 2026 年 1 月左右之前的测试结果，无法与近期的结果直接对比。

![](https://substackcdn.com/image/fetch/$s_!-eGZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4b8c3b9b-7536-4cba-8b85-854d25169864_1922x1726.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?g_model=DeepSeek-R1-0528&g_rundate=2026-02-13&g_runid=21976393587&i_seq=8k%2F1k&i_prec=fp8&i_gpus=mi325x_sglang%2Cmi300x_sglang&i_dstart=2026-01-23&i_dend=2026-02-13&i_hc=1#inference)

GB200 Dynamo TRT-LLM Disagg (分离) 架构同样取得了显著提升，在短短一个多月的时间里，最大吞吐量飙升了 20%。在部署了宽专家并行（WideEP）的中等交互性场景下，我们也看到了性能改善。这很可能得益于 GB200 上宽专家并行内核的日益成熟。

![](https://substackcdn.com/image/fetch/$s_!7v-Z!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdb4fa8dc-176c-4224-9ab5-6ebfe8f6af9c_1493x1280.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-01-31&g_runid=21538687343&i_gpus=gb200_dynamo-trt&i_dstart=2025-12-19&i_dend=2026-01-31#inference)

自我们首次发布以来，B200 SGLang 在 FP4 和 FP8 场景下均实现了稳步且持续的提升。自去年十月以来，在特定的交互性水平下，单 GPU 吞吐量已经翻番。

![](https://substackcdn.com/image/fetch/$s_!a06J!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1d5636b8-69d8-4676-9c3c-823da8d03514_2638x1840.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-01-13&g_runid=20972034325&i_gpus=b200_sglang&i_dstart=2025-10-05&i_dend=2026-01-13&i_prec=fp4%2Cfp8&i_dates=2025-10-30%2C2025-12-14#inference)

对于 MI355X 分离式推理服务，AMD 推荐搭配 MoRI 使用 SGLang。[MoRI 是 AMD 的 MoE (混合专家) 分发/合并集合通信与 KV Cache 传输库](https://github.com/ROCm/mori/tree/main)，由 AMD 位于中国的一支实力爆表的“十倍工程师”团队基于第一性原理打造。尽管 MoRI 还需要更开放的 CI（持续集成）与测试，但我们极度看好它的发展方向。原因在于，AMD 以往的常规操作是直接把英伟达的 NCCL 分支出来魔改为 RCCL，但这次 MoRI 摒弃了这种做法。它汲取了 RCCL/NCCL 的经验教训，完全基于第一性原理从零构建了一个全新的代码包。在短短一个多月的时间里，MoRI 的应用带来了可观的加速效果：在 20-45 tok/s/user 的交互性区间内，单 GPU 吞吐量提升了 20% 以上。

![](https://substackcdn.com/image/fetch/$s_!J5Il!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6b0d71aa-e6aa-425f-bbcc-25e2c1de2f4d_1900x1744.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-01-13&g_runid=20972034325&i_gpus=b200_sglang&i_dstart=2025-10-05&i_dend=2026-01-13&i_prec=fp4%2Cfp8&i_dates=2025-10-30%2C2025-12-14#inference)

## GPT-OSS 120B

针对 MI300X 和 MI325X，我们观察到整体性能实现了全面小幅提升。部分 AITER 优化改善了 MI300X 在所有交互性下的性能，而切换到上游 vLLM ROCm 镜像也带来了进一步提升。

SemiAnalysis InferenceX 是一款由读者支持的免费开源软件。想要接收最新文章并支持我们的工作，欢迎成为免费或付费订阅者。

![](https://substackcdn.com/image/fetch/$s_!jygf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F10e95c72-6372-415e-8e51-d8021815182c_2142x1784.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

至于 MI325X，似乎并非所有存在于下游 ROCm fork 镜像（在 2025 年 10 月 5 日测试中使用）中的性能增强，都已合入官方 vLLM ROCm 镜像。更离谱的是，MI355X 居然还在用 vLLM 0.10.1 版本的 fork `rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250927_rc1`)。我们本期望现在能看到它更新，但遗憾的是，当前的官方镜像（撰写本文时的 0.15.1 版本）尚未针对 MI355X 进行优化，并且会遇到严重错误。之前我们在 vLLM 0.14 版本的 MI355X 测试中也曾遭遇严重错误导致的崩溃。坊间传闻，vLLM 0.16.0 终于将实装所有必要改动，以提升 MI355X 的性能表现。

![](https://substackcdn.com/image/fetch/$s_!Xx8c!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1755b498-ab4d-4c02-b6fd-152ee538a34d_2126x1788.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/#inference)

将目光转回英伟达的系统，Hopper 和 Blackwell 在 vLLM 0.11.2 到 0.13.0 版本之间均实现了稳步的性能提升。我们很快将更新英伟达 GPU 的配置方案，以适配最新版本的 vLLM，并预计在切换后将获得更显著的性能飞跃。我们同样观察到，最新 1.2.0 版本的 TRT-LLM 也带来了性能提升。

![](https://substackcdn.com/image/fetch/$s_!WD4A!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F53a95093-3d25-4d01-9d64-64ea9e113749_2376x1760.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/#inference)

![](https://substackcdn.com/image/fetch/$s_!ZeZf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F77c591fb-74ef-46ce-bba2-9f82a52f5f6f_2362x1752.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/#inference)

## 分离式推理框架

英伟达在其分离式推理架构中采用了 Dynamo。[Dynamo](https://docs.nvidia.com/dynamo/design-docs/overall-architecture) 是一款专为多节点分布式推理设计的推理框架，集成了 Prefill-Decode 分离、请求路由以及 KV Cache 卸载等技术。该框架不绑定特定的推理引擎，因此我们在基准测试中能够将 SGLang 和 TRTLLM 作为后端。在 AMD 平台方面，我们采用 SGLang 搭配两种不同的 KV Cache 传输框架：MoRI 和 Mooncake。[MoRI](https://github.com/rocm/mori) 是一种专注于 RDMA 与 GPU 深度融合的高性能通信接口，支持网络集合通信操作与专家并行算子等应用。而[最近刚加入 PyTorch 生态系统](https://pytorch.org/blog/mooncake-joins-pytorch-ecosystem/)的 Mooncake，不仅支持 Prefill-Decode 分离，还具备丰富的多节点容错特性。

## DeepSeek 分离式推理与 WideEP 结果深度解析

在几乎所有的交互性下，就单卡总 token 吞吐量而言，Disagg (分离) 架构的表现均超越了聚合式推理（灰线）。多节点分离式预填充对单节点聚合式服务实现了全方位的性能碾压。

![](https://substackcdn.com/image/fetch/$s_!aeCq!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7ace6118-029a-44df-b0ef-2e7595e6f388_2032x1339.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?g_model=DeepSeek-R1-0528&g_rundate=2026-02-14&i_seq=8k%2F1k&g_runid=22013103756#inference)

英伟达仍在持续为 B200/GB200 FP8 推送更新。最新数据对比了 DeepSeek FP8 B200 TRT 单节点（开启/关闭 MTP）与 GB200 Dynamo+TRT Disagg (分离)（开启/关闭 MTP）的性能表现。这表明其在优化机架级推理软件与 WideEP（宽专家并行）算子方面，投入了持之以恒的工程心血。

![](https://substackcdn.com/image/fetch/$s_!s0zP!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F29485790-238d-4e1d-aa48-0559c79c9855_2132x1247.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

在对比 MI355X 的分离式推理与聚合式推理时，我们观察到了类似的规律。只有在低交互性、大 Batch Size 的场景下，分离式推理才能反超聚合式推理。这一现象在 FP4 精度下依然成立，其罪魁祸首很可能是算子优化严重拉胯。

![](https://substackcdn.com/image/fetch/$s_!wwi4!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F25a7c41e-fa99-4117-8e49-ac121a22bf0f_2092x1241.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

在 MI355X 上将 Disagg (分离) 预填充与宽专家并行（WideEP）结合并运行 FP4 时，我们发现其性能表现堪忧。

尽管理论建模表明，MI355X 上的 Disagg 推理性能理应远超单节点，但在要求更高交互性的场景下，Disagg 的实际表现反而更差。究其原因，当叠加使用多种 SOTA (业界领先) 推理优化技术时，ROCm 软件栈缺乏相应的 Kernel 与集合通信优化。

![](https://substackcdn.com/image/fetch/$s_!PqhO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2d82d32f-089b-405d-b4ef-94b4956676ed_2078x1233.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

### 英伟达 TensorRT LLM 与 NVL72

TensorRT LLM 已经在 TogetherAI 等全球先进服务商中，每小时处理着数十亿个 Token。它真正让 GB200 NVL72 和 GB300 NVL72 大放异彩，在高吞吐量场景下实现了两倍以上的性能跃升。MTP 则进一步推高了这一成绩，充分榨取了芯片的全部潜能。

![](https://substackcdn.com/image/fetch/$s_!NgC9!,w_720,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd4628887-37be-4563-ad68-091282e20ddf_2350x1486.png)

来源：SemiAnalysis InferenceX

观察成本图表，NVL72 系列凭借更大的 World Size 带来的优势同样显而易见。在 60 tok/s/user 的固定交互性下，单张 GB200 NVL GPU 产出的 tokens/s 略低于单张 B200 的三倍。

SemiAnalysis InferenceX 是免费开源软件，由读者提供支持。如需接收最新文章并支持我们的工作，请考虑成为免费或付费订阅者。

![](https://substackcdn.com/image/fetch/$s_!_KKs!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F36087d46-94e1-4629-90cb-4b0dfad1a8c1_1856x827.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

随着交互性的提升，这一差距不断缩小。在 130 tok/s/user 时，GB200 NVL72 几乎毫无优势，按每百万 Token 成本计算甚至更为昂贵。在低 Batch Size 下，推理工作负载大幅缩减，足以塞进单个 HGX 节点的 NVLink 域（即 8 张 GPU）内，此时 GB200 NVL72 更大的横向扩展 (Scale-out) 优势便开始消退。

![](https://substackcdn.com/image/fetch/$s_!RyLb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3e287d0e-947f-4fd7-9dc8-d697fad9ac7d_1781x822.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## 英伟达与 AMD 分离式 Prefill 对比

随着今日 InferenceXv2 的发布，ML (机器学习) 社区首次得以一览开源 MI355X 分布式推理的完整帕累托前沿。我们展示了 B200 与 MI355X 在开启和关闭 MTP 时的帕累托曲线。

在 FP8 分离式 Prefill 方面，MI355X（MoRI SGLang）展现出了足以与 B200（Dynamo SGLang）相匹敌的竞争力。这两种配置均未使用宽专家并行 (WideEP)，因为所有预填充/解码实例最高仅在 EP8 下运行。在吞吐量与交互性帕累托前沿的两端，MI355X 均略微落后于 B200。但在曲线中段的特定交互性下，MI355X 分离式配置略占优势。B200 与 MI355X 都能从 MTP 中获益，且在开启 MTP 时，两款芯片实现了相同的相对性能提升。

![](https://substackcdn.com/image/fetch/$s_!_OWw!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F99728443-e697-49cc-8416-7a380c60ad12_2147x1249.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

然而，若仅衡量输出（解码）Token 吞吐量，就会发现在较低的交互性下，B200 的输出 Token 吞吐量远高于 MI355X。需要注意的是，在考察分离式推理配置的纯输出 Token 吞吐量时，我们始终按解码 GPU 数量（而非 GPU 总数）进行归一化处理。在 B200 与 MI355X 上运行推理任务时，用于输出的 GPU 数量可能存在差异，但核心结论不变：无论解码跑在什么配置上，B200 完成解码任务的速度都更快。

SemiAnalysis 是免费开源软件，由读者提供支持。如需接收最新文章并支持我们的工作，请考虑成为免费或付费订阅者。

![](https://substackcdn.com/image/fetch/$s_!RrVb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff67a92c3-b159-4b2a-bf87-ecbb7002b23c_2118x1306.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

尽管 MI355X 在 FP8 Disagg (分离) 场景下具备竞争力，但其 FP4 性能却饱受可组合性问题困扰。AMD 单节点 FP4 性能尚可，但若将 AMD 的 FP4 Disagg (分离) 预填充与英伟达对比，其性能表现就显得差强人意，MI355X 更是被英伟达的 B200 全方位碾压。在 1k1k 场景下，开启 MTP 的 MI355X（MoRI SGLang）才勉强击败未开启 MTP 的 B200（Dynamo SGLang）。

![](https://substackcdn.com/image/fetch/$s_!pdWn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa5b9e7bc-c484-4400-9ffe-96ed4bbfb70f_2138x1236.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

一旦将 Dynamo TRTLLM 纳入考量，B200 的性能会进一步飙升，以至于即使开启 MTP，MI355X 也无法匹敌同样开启 MTP 且搭配 Dynamo TRTLLM 的 B200。MI355X 只有在开启 MTP 的情况下，才能在性能上追平未开启 MTP 的 B200，且这仅限于交互性在约 60 Token/秒/用户到约 120 Token/秒/用户之间的区间。

![](https://substackcdn.com/image/fetch/$s_!BIqJ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0be8b8f5-b627-4dc9-938b-4a407ef19c34_2103x1233.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

在对比 Dynamo TRTLLM B200 与 SGLang MoRI MI355 的 Disagg (分离) 预填充时，由于 TRTLLM 对 Disagg (分离) 预填充的实现更为成熟，AMD 遭遇了全方位的性能碾压。

![](https://substackcdn.com/image/fetch/$s_!V0OR!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F89827e17-6cfd-42f1-b250-d7f07cbe6a09_2120x1242.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!qzCm!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc53a37b8-dd9f-4142-b114-60e6e2c7f3e7_3446x1946.png)

来源：Dwarkesh Podcast 和 SemiAnalysis

下图展示了构成 MI355X（MoRI SGLang）帕累托前沿的各种并行配置。需要注意，目前没有任何数据点采用宽专家并行 (WideEP)（即 EP 为 16、32 等配置）。

![](https://substackcdn.com/image/fetch/$s_!IcWw!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe1b62a52-bd6a-4cd1-82e7-65b6903d82ac_2996x1774.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## 拆解推理服务商的单位经济效益

下表列出了 OpenRouter 上所有提供 DeepSeek R1 0528 FP8 服务的推理提供商，并附上了其每百万输入/输出 Token 的成本及平均交互性。撇开 Chutes 不谈，中游提供商的交互性大约在 35 Token/秒/用户。

![](https://substackcdn.com/image/fetch/$s_!b5bS!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fce79108c-8341-4100-86de-943d8ca3c34e_916x1190.png)

来源：[OpenRouter](https://openrouter.ai/deepseek/deepseek-r1-0528/performance)

基于上述数据，35 Token/秒/用户是一个合理的交互性水平。据此，我们可以利用真实的 InferenceX 数据进行插值计算，得出在该交互性下每百万输入/输出 Token 的成本。

正如后文所述，这最好被视作*基准*数据，无法完全代表真实的生产环境推理。原因在于 InferenceX 采用随机数据进行基准测试，并且禁用了前缀缓存。换言之，实际的性能/成本比*至少*会达到这个水平。另外需要强调的是，并非*每款 GPU* 在*每一个*交互性下都有对应的数据点，因此我们无法在所有交互性维度上进行*绝对精确*的对比。尽管如此，在缺乏精确数据点的情况下，我们依然认为下方的条形图对比提供了（非常）合理的插值参考。

在该交互性下对比 Disagg (分离) + WideEP 配置，我们能清晰看到分布式推理技术在提升性能/TCO 与整体吞吐量方面的显著成效。同时，大规模 Scale-up 架构（如 GB300 和 GB200 NVL72）在单 GPU 总吞吐量上展现出了绝对的统治力。

值得注意的是，在该交互性下（针对 8k1k 工作负载类型），B200 在启用 MTP 时能够实现最佳的性能/TCO。下方我们还列出了各款 GPU 的 TCO（自购模式 —— 超大规模云厂商）：

![](https://substackcdn.com/image/fetch/$s_!ZFIh!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff200bfa6-02b5-464f-a4ea-ffe88cb6ed49_2520x81.png)

来源：[SemiAnalysis TCO 模型](https://semianalysis.com/ai-cloud-tco-model/)

![](https://substackcdn.com/image/fetch/$s_!WB-s!,w_474,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffd2a22ee-c300-4fbd-a782-bdf5ac918c02_1882x1776.png)

来源：SemiAnalysis InferenceX

基于上述发现，我们来深挖大规模部署 LLM 的单位经济效益。从上文的 OpenRouter 数据可以看出，Crusoe 提供的交互性为 36 Token/秒/用户，定价为每百万输入 Token 1.35 美元、每百万输出 Token 5.40 美元。假设在没有缓存命中的情况下，且 Crusoe 至少使用了 H200 GPU，并结合了 MTP、Disagg 以及 WideEP 等 SOTA (业界领先) 推理技术。那么上述数据表明，其成本*绝不超过*每百万输入 Token 0.226 美元与每百万输出 Token 2.955 美元。这意味着，其输入 Token 的毛利率最高可达 83%（折旧已计入销货成本），输出 Token 的毛利率可达 45%。

SemiAnalysis InferenceX 是一款免费的开源软件，离不开广大读者的支持。如需获取最新文章并支持我们的工作，欢迎考虑成为免费或付费订阅者。

当然，这些假设未必*完全*准确，上述计算也未将停机时间或利用率不足的情况纳入考量。但这足以展示，利用 InferenceX 数据能推演出多么精妙的测算。关于推理经济学的更多分析，详见 [SemiAnalysis Tokenomics 模型](https://semianalysis.com/tokenomics-model/)。

OpenRouter 数据还显示，Nebius AI Studio (Fast) 提供 DeepSeek FP4 服务的交互性为 167 Token/秒/用户，定价为每百万输入 Token 2 美元、每百万输出 Token 6 美元。在 InferenceX 中对交互性进行相应调整后，我们得到了以下数据。

![](https://substackcdn.com/image/fetch/$s_!28az!,w_474,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff41d237c-16c2-4a9d-b681-a6668b01f62b_2398x1526.png)

来源：SemiAnalysis InferenceX

在如此高的交互性下，必须采用 MTP 等投机解码技术来实现足够高的吞吐量，从而使推理具备经济效益。幸运的是，MTP 能够提升吞吐量，且对模型整体准确率的风险相对较低。在本文后续章节中，我们将进一步探讨 MTP，并分析如何应用该技术来提升吞吐量并降低成本。

最后，我们再展示一张图表，呈现交互性为 125 Token/秒/用户的 FP8 DeepSeek 工作负载。这是另一个低延迟工作负载，其中 MTP 大幅提升了经济可行性。与前一个例子类似，我们注意到，在这些较高的交互性区间内，成本最低的配置均采用了 MTP。

![](https://substackcdn.com/image/fetch/$s_!E0-S!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fccabb1a5-220a-4623-a615-245053808f24_2086x1738.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

### 英伟达分离式 Prefill 与 WideEP

EP 需要全对全 (All-to-all) 通信，即每张 GPU 都需要向其他所有 GPU 发送 Token。这对带宽的消耗极大。回顾一下，英伟达服务器拥有两个独立的网络域：纵向扩展的 NVLink 域，以及通常采用 InfiniBand 或以太网协议的横向扩展 (Scale-out) 域。

- NVLink 域（NVL72 机架内）：72 张 GPU 通过 NVLink 连接，每张 GPU 的单向带宽高达 900 GB/s。这大约是基于 InfiniBand 或以太网的横向扩展 (Scale-out) 网络带宽的七到十倍。

- InfiniBand/RoCEv2 以太网（NVL72 机架外）：每张 GPU 单向带宽通常为 400-800 Gbit/s（50-100 GB/s）。需要注意的是，我们针对英伟达的所有测试均在基于 InfiniBand 的集群上进行。

TP 将每一层的权重矩阵分片至多张 GPU。这意味着在每一层，每个 token 最多需要两次全归约 (All-reduce) 通信（一次在列并行 GEMM (通用矩阵乘法) 后，一次在行并行 GEMM 后）。而 EP 仅在 MoE (混合专家) 层执行全对全 (All-to-all)。每张 GPU 只发送路由至各专家的 token。因此，与 TP 相比，EP 在所有层面的通信成本都更低。

EP 的全对全 (All-to-all) 通信带宽需求随参与节点数成比例增长。因此，在被迫跨越较慢的 IB/以太网架构前，将通信维持在高带宽的 NVLink 域内显然更优。借助 NVL72，系统无需离开 NVLink 即可跨 72 张 GPU 实现 EP；相比之下，前代产品（仅具备 8 卡 NVLink 域）只能在 8 张 GPU 范围内维持 NVLink 速度的 EP，随后便会撞上较慢的 IB/以太网瓶颈。

SemiAnalysis InferenceX 是免费的开源软件，依靠读者支持运营。欢迎成为免费或付费订阅者，获取最新文章并支持我们的工作。

WideEP 在权重加载效率上也具备重大优势。对于 DeepSeek R1 这类模型，解码阶段受限于内存带宽瓶颈：核心制约因素是 GPU 从 HBM 加载权重的速度。采用 WideEP（如 DEP32）时，32 张 GPU 共同承载并一次性加载 670B 权重，每张卡仅需加载专属分片（约 21B）。这 32 颗芯片的 HBM 总带宽被全部用于加载单份模型副本。相比之下，若采用较窄的 EP 配合更多 DP（数据并行）副本（如 5xDEP8），5 个副本各自都需要一份完整的 670B 权重，导致系统层面出现 5×670B = 3.35T 的冗余权重加载。EP 在多芯片间分摊权重，而 DP 则是复制权重。正因如此，在 NVLink 等高带宽互连技术的加持下，更宽的 EP 能够带来单 GPU 吞吐量的显著跃升。

![](https://substackcdn.com/image/fetch/$s_!7EhO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7ed2a472-3511-4b29-afbd-0c593795085a_2434x1430.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

通常情况下，由于负载均衡的考量，低并发场景下更倾向于使用 TP。在小 Batch Size 时，EP 容易陷入 token 到专家路由不均的困境，导致部分 GPU 闲置吃灰，而另一部分则严重超载。TP 则巧妙避开了这一问题，因为每张 GPU 都持有每个专家的一块切片，始终能分到同等的工作量。在低并发场景下，这种负载不均带来的性能损耗，远超 TP 增加的通信开销。

在更高并发下，这种权衡会发生反转。随着 Batch Size 增大，专家激活分布变得更加均匀，此时 EP 在通信和权重加载上的优势，便全面压倒了 TP 昂贵的逐层全归约 (All-reduce)。在曲线中段，TP+EP 混合配置能兼顾双重考量：在每个专家内部划定小规模 TP 组以确保负载均衡，同时在更广泛的 GPU 集群上拉满 EP，从而充分分摊权重并削减通信开销。

对于追求更高交互性（低 Batch Size）的场景，一味做大向上扩展 (Scale-up) 规模往往无法带来更强的性能。基于 IB 网络的 B300 Disagg (分离) 架构与采用 NVL72 的 GB300 性能相当，因为此时的工作负载受限于延迟瓶颈，而非带宽瓶颈。NVL72 庞大的 NVLink 带宽优势毫无用武之地——毕竟传输中那点微小的 token 批次，连慢得多的 IB 链路都塞不满。

预填充与解码分离同样发挥着关键作用。预填充阶段计算密集且呈突发性；解码阶段则处于内存带宽瓶颈且呈稳态。当两者共享同一批 GPU 时，势必相互干扰，进而导致延迟抖动与算力浪费。将它们剥离到专属的 GPU 资源池中，能让各自运行与其特性相匹配的工作负载，从而提升有效利用率。正因如此，在吞吐量-交互性曲线的中段，采用 Disagg (分离) 配置的 B200 击败了单节点 B200。相比于把两个阶段硬塞进单个 8-GPU 节点，预填充与解码分离结合跨越更多 IB 互联 GPU 的更宽泛 EP，能更高效地分摊权重。

[补充说明：TogetherAI 的 10x 推理工程师们在多轮对话流量中发现了一个规律——首轮预填充的需求与后续轮次截然不同。他们顺势将其分离，从而实现了更优的 TTFT (首个 Token 延迟) 性能。](https://www.together.ai/blog/cache-aware-disaggregated-inference)

![](https://substackcdn.com/image/fetch/$s_!_Tls!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbfdcb99e-dc02-4468-bd72-b25a7be6c15d_2380x1386.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## 黄仁勋的低承诺与超预期交付：Hopper、Blackwell 与机架级 NVL72 对比

在 GTC 2024 上，黄仁勋在台上承诺从 H100 到 GB200 NVL72 将带来高达 30 倍的性能提升，[所有人都觉得这不过是经典的营销拉满，在现实世界中根本无法实现。](https://newsletter.semianalysis.com/p/nvidia-blackwell-perf-tco-analysis)许多人试图给这种看似施展了现实扭曲力场的行为贴上标签，好让他们能讲更多黄氏数学的段子。的确——[我们当时也曾指出，这 30 倍的性能差距，实际上是将](https://newsletter.semianalysis.com/i/175661150/benchmarking-the-h200-on-its-bad-hair-day) H200 在 FP8 下的最差情况与 GB200 在 FP4 下的合理情况进行对比得出的。

- [英伟达 Blackwell 性能与 TCO 分析——B100 对比 B200 对比 GB200 NVL72](https://newsletter.semianalysis.com/p/nvidia-blackwell-perf-tco-analysis) - Dylan Patel 与 Daniel Nishball · 2024 年 4 月 10 日

![](https://substackcdn.com/image/fetch/$s_!9ywW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4fec3378-2cf4-4c1c-a40d-bcbd788c9a70_3022x1964.jpeg)

来源：[英伟达（NVIDIA）GTC 2024](https://newsletter.semianalysis.com/p/nvidia-blackwell-perf-tco-analysis)

但事实证明，小丑竟是他们自己。时间快进到将近两年后，我们现在可以看到，这终究不是什么营销炒作拉满，黄仁勋实际上一直对 Blackwell 的性能作了保守承诺。根据我们的测试，在大规模 MoE (混合专家) 推理方面，即使与强大的 H100 Disagg (分离) 结合宽专家并行 (WideEP) 的 FP8 基准相比，Blackwell 的表现也极其出色。在 116 Token/秒/用户的交互性下，GB200 NVL72 FP4 的性能提升高达 98 倍，而 GB300 NVL72 FP4 的性能提升更是高达 100 倍！也许黄氏数学的新法则是：在 token 吞吐量方面，他交付的实际结果永远是承诺的两倍。买得越多，省得越多，诚不欺我！

![](https://substackcdn.com/image/fetch/$s_!rxr1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F70638c7e-69a6-43f2-96a4-23766bcabbd2_2121x1248.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

即使将 Blackwell 和 Blackwell Ultra 增加的 TCO 考虑在内，与 Hopper 相比，每美元 token 数依然实现了 9.7 倍（40 Token/秒/用户）到 65 倍（116 Token/秒/用户）的提升。[您可以在我们的免费网站上详细探索 Hopper 与 Blackwell 的性能对比](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_prec=fp4%2Cfp8&i_metric=y_costh&i_log=1#inference)。与 Hopper 相比，Blackwell 的性能实在太强了，以至于我们必须在数据大盘中使用对数坐标轴才能将其可视化。

![](https://substackcdn.com/image/fetch/$s_!7m9y!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F402b23af-7ad6-46e4-97af-a5698ea2bd87_2176x1416.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

正如前文所述，B300 服务器仅通过 900GByte/s/GPU 的 NVLink 纵向扩展网络 (Scale-up 网络) 最多连接 8 个 GPU，而 GB300 NVL72 服务器则通过 NVLink 纵向扩展网络 (Scale-up 网络) 连接 72 个 GPU。因此，当我们的推理配置需要 8 个以上（但少于 72 个）GPU 时，就必须引入多个 B300 服务器节点来构建推理系统。这意味着通信将降级至速率较低的 InfiniBand XDR 横向扩展 (Scale-out) 网络，其每 GPU 带宽仅为 800Gbit/s 单向 (Uni-directional)。 相比之下，机架级 GB300 NVL72 通过 NVLink 连接 72 个 GPU，提供高达 900GByte/s 单向 (Uni-directional) 的每 GPU 带宽。由此可见，与多节点 B300 服务器方案相比，这种机架级服务器能让推理配置中的 GPU 以超过 9 倍的带宽进行互联通信。

SemiAnalysis 是免费开源软件，由读者提供支持。要接收最新文章并支持我们的工作，请考虑成为免费或付费订阅者。

![](https://substackcdn.com/image/fetch/$s_!x_1H!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8664f48c-037c-45cc-b6f8-1999ed0cee0e_2298x1430.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

诚然，GB300 NVL72 的单 GPU 综合成本更高，但这仅仅是将其单位 TCO 带宽优势降至 8 倍。这种机架级架构的带宽优势直接大幅降低了每 token 成本。目前，谷歌 TPU（张量处理器 (Tensor Processing Unit)）、AWS Trainium 和英伟达是仅有的已部署机架级系统设计的 AI 芯片。AMD 首款机架级 MI455X UALoE72 系统将于 2026 年下半年推出工程样机并进行小批量生产。而受制于制造延期，其量产爬坡以及在 MI455X UALoE72 上生成的首批生产级 token，要等到 2027 年第二季度才能实现。

![](https://substackcdn.com/image/fetch/$s_!UGuH!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F58c7b664-76a7-454b-ac99-036b0b6f4abb_2132x1456.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## Blackwell 与 Blackwell Ultra 对比

纸面参数上，新发布的 Blackwell Ultra 与 Blackwell 内存带宽相同、FP8 性能持平，FP4 性能仅为后者的 1.5 倍。但在实测中，我们却发现 Blackwell Ultra 的 FP8 性能最高达到了 1.5 倍，而 FP4 性能仅为 1.1 倍。这可能是因为 Blackwell Ultra 作为全新发布的 GPU，软件优化尚未完全到位。

![](https://substackcdn.com/image/fetch/$s_!hX_E!,w_720,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa7625f0e-7e35-4170-8986-4fe0d66f7925_2125x1247.png)

来源：SemiAnalysis InferenceX

## MI355X、MI325X 与 MI300X 对比

在 AMD 的各款芯片中，我们看到 MI355X 的性能最高可达 MI300X 的 10 倍。目前，AMD 仅在 MI355X 上成功跑通了 DeepSeek SGLang 的分离式推理。他们尚未提交 MI300X 或 MI325X 的分离式推理测试结果，这可能是因为旧款芯片上仍有悬而未决的软件问题。

![](https://substackcdn.com/image/fetch/$s_!vT9R!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd6dd3138-e228-4121-a061-4aa92c84d6a4_2334x1390.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_seq=8k%2F1k&i_metric=y_outputTputPerGpu&i_prec=fp8%2Cfp4&i_legend=0#inference)

![](https://substackcdn.com/image/fetch/$s_!rvyB!,w_720,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F101c2a16-c861-40f5-8079-3f2e38038980_2491x1123.png)

来源：SemiAnalysis InferenceX

再看成本方面，在 FP8 精度下运行 DeepSeek-R1 时，若交互性设定为 24 Token/秒/用户，MI355X 的推理成本比 MI325X 便宜了将近 3 倍。其单卡吞吐量略低于 MI325X 的 4 倍。

![](https://substackcdn.com/image/fetch/$s_!SaQ4!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fab1ad749-fe92-4209-9347-4456d22b0cfd_2088x1432.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## AMD 在 FP4、分布式推理与宽专家并行上的可组合性问题

尽管 AMD 在单节点 FP4 上的表现还算过得去，在 FP8 分布式推理上也与运行 SGLang 的 B200 有一战之力，但目前 AMD 开源推理软件栈的症结在于：虽然各项独立的推理优化跑起来不错，但真实客户在部署时往往会将多种优化组合使用。顶尖 AI 实验室都在同时启用 FP4**、**分离式推理**以及**宽专家并行，而这正是 AMD 翻车的地方。

SemiAnalysis 是一款免费开源软件且由读者支持。为了接收新文章并支持我们的工作，请考虑成为免费或付费订阅者。

AMD 的软件依然不达标。SemiAnalysis 和 AMD 内部的理论极限性能建模 (Speed of Light) 均表明，在 FP4 精度下，结合宽专家并行的分离式推理，其性能理应优于 MI355X 的单节点推理。遗憾的是，软件依然是掣肘 AMD GPU 的巨大瓶颈。AMD 管理层必须进一步优化工程人才的资源配置，例如，把工程资源从 ATOM 这种根本没人用的单节点自嗨项目中撤出，转而集中精力解决上述分离式推理、宽专家并行与 FP4 之间推理优化的可组合性问题。 目前软件表现拉胯，归咎于缺乏重点，以及未能准确把握行业现状而导致优先级错乱。所有顶尖实验室都已用上了分离式推理和宽专家并行；AMD 必须停止死磕单节点，将核心精力重仓投入到开源解决方案的多节点推理上。

在开源分布式推理、宽专家并行以及 FP4 的可组合性方面，AMD 已经落后了半年多。这点从[英伟达和 SGLang 团队在六个月前就已大秀其在 DeepSeek 上的 NVFP4 性能](https://lmsys.org/blog/2025-09-25-gb200-part-2/)中便可见一斑。

![](https://substackcdn.com/image/fetch/$s_!IGhQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Feddd9541-ed5a-4e49-aab2-291d49fd7e68_2132x1252.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## AMD ATOM 引擎

AMD 推出了一款名为 ATOM 的新推理引擎。ATOM 能提供稍好一点的单节点性能，但严重缺失大量关键特性，导致其根本无法用于实际工作负载。例如，它不支持 NVMe 或 CPU KVCache 卸载、工具解析、宽专家并行以及分离式服务。这导致目前在生产环境中根本没有客户使用它。英伟达的 TRTLLM 在 TogetherAI 等公司全球每小时生成数十亿个 token，并且[确实支持工具解析等特性](https://nvidia.github.io/TensorRT-LLM/commands/trtllm-serve/trtllm-serve.html#cmdoption-trtllm-serve-serve-tool_parser)；相比之下，由于缺乏上述特性，目前没有任何 Token 工厂在使用 ATOM。

此外，由于 AMD 提供的工程和 GPU 资源匮乏，vLLM 等开源推理引擎的维护者对 AMD 感到失望。例如，vLLM 首席维护者 Simon Mo 在 GitHub 的一份 RFC 中表示，目前仍然没有可用的 MI355X 供他添加到 vLLM 的 CI (持续集成) 中，这直接导致了糟糕的用户体验。目前 vLLM 上针对 MI355X 的测试数量为零，而英伟达的 B200 在 vLLM 上已有大量测试。同样，vLLM 上的 MI300X CI 机器数量依然不足。上游 vLLM 至少还需要 20 台 MI300、20 台 MI325 和 20 台 MI355X 机器，才能达到与 CUDA 同等的易用性水平。

我们 SemiAnalysis 一直在敦促 AMD 为 vLLM 贡献更多算力，并在过去几周取得了一些进展。vLLM 将开始获得几台 MI355X 机器，从而将 CI 测试对等度从 0% 提升至非零。在即将发布的《AMD 现状》（State of AMD）文章中，我们将深入探讨 AMD 此前在 vLLM、SGLang、PyTorch CI 机器贡献上的拉胯表现，以及 Anush 是如何着手解决这一问题的。在 SemiAnalysis，我们将建立内部仪表盘，专门追踪 AMD 和英伟达在 vLLM、SGLang、PyTorch 和 JAX 上运行的测试数量及质量。

此外，vLLM 维护者表示，正是由于机器资源匮乏，他们无法为 ROCm 提供 vLLM 的首发 (Day 0) 支持。这种上市时间上的巨大差距导致 ROCm 持续落后，也给英伟达留下了巨大的市场空档，使其得以继续攫取高达 75% 的疯狂毛利率（相当于成本的 4 倍加价）。

![](https://substackcdn.com/image/fetch/$s_!1hBL!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F96fd0617-347d-49a1-a971-19e42faeab25_1435x1289.png)

来源：[Github](https://github.com/vllm-project/vllm/issues/33478#issuecomment-3844103561)

最后，AMD 缺乏足够多“通过特性护航和代码所有权展现出持续参与上游建设”的代码提交者，同时也缺乏能够审查自家代码的审核员。这就是为什么 ROCm vLLM 的开发节奏远比 CUDA vLLM 慢得多的原因。

AMD 内部有许多才华横溢的 10 倍工程师在开发 ATOM，我们敦促 AMD 管理层考虑重新部署这些 10 倍工程师，让他们去开发人们真正使用的库和框架，比如 vLLM 和 SGLang。

正如前文所述，AMD 也必须优先解决 FP4、WideEP 以及分离式服务 的可组合性问题，而非过度执迷于单节点的 FP4 优化。

![](https://substackcdn.com/image/fetch/$s_!XDqu!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fda3b4a10-0f65-403d-a9f6-093b86753c02_2120x1258.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## 多 Token 预测（MTP）

投机解码通过使用一个小巧且成本低廉的草稿模型提前预测几个 token，从而降低自回归生成的成本。随后，大模型在一次类似预填充计算的前向传播中，对这些预测的 token 进行校验。对于给定的输入序列长度，当输入增加 N 个 token 时，单次前向传播的耗时基本不变。投机解码正是利用了这一特性，先在较小的模型上运行推理，为大模型起草多个 token，大模型只需一次前向传播即可完成校验，从而在相近的时间预算内最多额外生成 N 个 token。

![](https://substackcdn.com/image/fetch/$s_!V6f0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb2b2aa12-c308-4f4b-84f7-969228600ce5_2296x1126.png)

来源：[Brendan Bycroft](https://bbycroft.net/llm)

这种“在相同时间预算内生成额外 token”的假设在稠密模型中最为成立，因为批处理校验可以在多个位置复用同一权重流。而对于混合专家（MoE）模型，不同的 token 可能会被路由到不同的专家，因此校验多个草稿 token 激活的专家数量会多于单 token 解码，迫使系统从内存中读取更多专家权重。正如 EAGLE 论文中 Mixtral 8x7B Instruct 模型的结果所示，这种额外的内存流量吞噬了省下的带宽红利，甚至可能导致校验阶段的耗时与标准解码步骤相差无几。

多 Token 预测（MTP）追求类似的收益，但无需单独的草稿模型。通过在模型架构中加入辅助预测头，单一模型就能基于相同的底层表示预测未来几个 token。这改善了分布对齐，因为预测结果和最终评分均出自同一模型。MTP 还能在支持多 token 生成策略的同时，避免部署额外模型带来的运维复杂性，不过它要求 MTP 预测头必须与主模型一起进行预训练。

![](https://substackcdn.com/image/fetch/$s_!KL8_!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F27ee5a46-78b5-40dd-b76d-1f096e0ae06d_1755x1154.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

在所有 SKU 上，启用 MTP 都能带来性能提升。通过利用通常闲置的 Logits 来校验额外的 token，该方法仅引入微乎其微的计算开销，却能在解码期间省下昂贵的额外权重加载成本。

![](https://substackcdn.com/image/fetch/$s_!HkQ0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffb5fc8fa-d129-475c-bb87-664e08bc6179_1773x1151.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

在大 Batch Size 下，推理过程受内存带宽的限制弱于低 Batch Size 场景。投机解码（包含 MTP）的本质是用冗余算力换取更少的访存受限解码步数。因此，投机 Token 带来的额外校验工作可能无法完美填补算力空隙（slack）。这导致在大 Batch Size 下的性能提升幅度较小。

成本方面，MTP 能带来巨幅节省。下表显示，使用 Dynamo TRT 以 FP4 精度运行 DeepSeek-R1-0528 时，每百万总 Token 成本为 0.251 美元。一旦启用 MTP，该成本便一路陡降至仅 0.057 美元。

![](https://substackcdn.com/image/fetch/$s_!_ljZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdcf44984-9cb9-49ae-b35a-aeb5b5d14244_1566x1778.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

在所有配置下，只要控制其他变量不变，搭配 DeepSeek R1 使用 MTP 均能提升交互性。且该操作对模型精度并无显著影响。这与 DeepSeek V3 技术报告的结论高度吻合。

![](https://substackcdn.com/image/fetch/$s_!MXVB!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1143164c-b38f-4ca9-888a-e9e270d6ef48_1757x1187.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

关于 MTP 性能数据的有效性，有人可能会质疑合成数据集的分布偏离真实数据。然而，对比 MTBench 与我们的 1k1k 基准测试中的 MTP 接受情况，我们发现两者分布高度一致。这印证了 InferenceX 基准测试是衡量真实生产环境性能的可靠参照。话虽如此，InferenceX 仍非完美，我们始终在持续迭代。如果你想参与这项使命，[欢迎在此申请加入我们的特别项目团队](https://app.dover.com/apply/semianalysis/2a9c8da5-6d59-4ac8-8302-3877345dbce1)。

![](https://substackcdn.com/image/fetch/$s_!d8l8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6c4a7c01-3d56-486d-b959-cb4b6468f56f_2408x1390.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## 准确率评估

吞吐量优化有时会暗中牺牲准确性（例如激进放宽接受率、微调解码、使用数值不稳定的算子，或错误配置端点）。若缺乏评测，配置错误的服务器（如发生截断、解码错误、端点参数错误）依然能跑出华丽的吞吐量数据，但输出的纯属垃圾回答。例如，正是借助这层额外的检查，我们才揪出了 GPT-OSS 中某些 DP 注意力机制实现存在的缺陷。

如今，每种典型的吞吐量配置都已绑定相应的数值准确性检查。目前我们仅使用 GSM8k。但该基准测试过于简单，数值计算差异未必会引起评测分数的明显波动；而在更高难度的基准测试中，数值计算精度不同所带来的评测分数落差可能会更大。因此，我们计划未来引入更高难度的基准测试，如 GPQA、HLE、MATH-500 以及 SWE-Bench verified。

量化是性能与准确性博弈的另一种体现。降低模型服务精度往往会导致输出质量下降。在 DeepSeek R1 的测试中，FP8 版本的评测分数微幅领先于 FP4。需要注意的是，GSM8k 评测指标现已饱和。在进行量化感知训练 (QAT)/PAT 时，模型通常会针对主流的 GSM8k、MATH-500 等数据集进行专门校准。这就导致跑分数据看起来光鲜亮丽，而真实终端用户的实际体验却大打折扣。如果你想加入团队，共同探索如何正确评估推理引擎的准确性，[请在此申请加入这项任务](https://app.dover.com/apply/semianalysis/2a9c8da5-6d59-4ac8-8302-3877345dbce1)。

![](https://substackcdn.com/image/fetch/$s_!UHSQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe58e6323-b5d1-4221-9c51-ff39b44d1f98_1779x1180.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## Anthropic 快速模式推理详解

Anthropic 最近在发布 Opus 4.6 的同时推出了“[快速模式](https://code.claude.com/docs/en/fast-mode)”。其核心卖点是：在保持模型质量不变的前提下，速度提升约 2.5 倍，但价格也涨了约 6 到 12 倍。这两个数字可能令人咋舌，一些用户甚至猜测[这肯定需要新硬件](https://x.com/Yuchenj_UW/status/2020214926133063705)。其实不然。这本质上只是基本的权衡博弈。任何模型都可以提供多种交互性（每用户每秒 Token 数），而每百万 Token 成本 (CPMT) 也会随之变化。顺着我们之前的比喻来说，梅赛德斯既造公交车，也造赛车。这就像是乘坐公交车与驾驶赛车的区别。公交车能服务众多乘客，但频繁停靠会增加时间（分摊成本）；而赛车速度极快，但只服务单人。

精打细算的财务人员可能觉得快速模式更贵，但如果从总体拥有成本的视角来看，在某些场景下快速模式实际上要便宜得多。举个例子，一个 GB200 NVL72 机架的成本可达 330 万美元。因此，如果 Claude Code 的智能体循环（在生产环境中运行于 Trainium）通过工具调用 NVL72 机架，而这些机架的推理速度慢了 2.5 倍，你就需要 2.5 倍数量的机架来提供推理能力。这意味着，如果不开启快速模式，将多出近 500 万美元的额外开销。

![](https://substackcdn.com/image/fetch/$s_!sIVI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcad37655-7b9a-4c86-81a8-3314ad0526fe_1694x348.png)

来源：[Anthropic](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!7boM!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4bb71482-fe77-4e33-b5cb-b7db512b61c1_1700x439.png)

来源：[Anthropic](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

以在 B200 上使用 TRT-LLM 部署 DeepSeek R1 0528 FP4 的编程工作流为例。当交互性为 50 tok/s/user 时，推理成本约为 0.56 美元/百万输出 Token。当交互性达到 125 tok/s/user 时，成本升至约 4 美元/百万输出 Token。速度提升 2.5 倍，价格上涨约 7 倍，这与我们在 Anthropic 快速模式中看到的情况高度吻合。需要注意的是，这里假设 DeepSeek R1 与 Opus 4.6 类似，但实际并非如此。尽管如此，这一基本原则依然成立。

![](https://substackcdn.com/image/fetch/$s_!7SFd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F66509f21-d3e5-435f-9163-50d9be56c789_1930x1162.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!CjTZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6621150f-7da2-44ae-9695-493374487825_1972x1122.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

这背后的根本原因在于 LLM 推理中固有的延迟与吞吐量权衡。在高批处理规模下，GPU 的利用率更高，总 token 吞吐量也更大，这意味着可以同时服务更多用户，每个 token 的成本也更低。而在低批处理规模下，虽然每个请求的并行度更高，能为单个用户带来更快的响应速度，但总 token 吞吐量会随之下降。由于无论如何使用，[加速器的小时成本](https://semianalysis.com/ai-cloud-tco-model/) 都是固定的，因此吞吐量降低就意味着可用于分摊成本的 token 数量减少，从而导致每个 token 的价格更高。

简而言之，所谓的快速模式本质上与硬件关系不大，它只是在同一批 GPU 上牺牲吞吐量换取延迟的必然结果。

![](https://substackcdn.com/image/fetch/$s_!pPy0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F132f55e4-43c7-4df3-bb4e-1408d85c2782_2718x1796.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

此外我们发现，正如前文所述，像投机解码这类推理优化技术可以直接降低推理成本，完全无需更换新芯片。

以 8k/1k 负载下的 DeepSeek R1 FP4 为例。在 150 tok/sec/user 的交互性下，基准 GB300 Dynamo TRT 的每百万 Token 成本（CPMT）约为 2.35 美元，而启用 MTP 后该成本降至约 0.11 美元。仅仅应用一项推理优化技术，就能在该交互性下实现约 21 倍的成本下降。

![](https://substackcdn.com/image/fetch/$s_!8RyG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff88b30b6-aa73-4ad2-a008-b2e8f940cfd0_1958x1104.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!YpDx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff6dfa226-93d7-4596-9dc5-feebd5ef1dce_1966x1098.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!rSgJ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8742f134-05d4-4a07-9257-8c93b4730cd7_2704x1790.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

将交互性固定在 50 tok/sec/user，我们可以进一步观察 MTP 能在多大程度上有效降低各类芯片的 CPMT。

![](https://substackcdn.com/image/fetch/$s_!BIXI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbc992849-b42d-4899-81a3-77105c86886b_1950x1250.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## 宽专家并行（WideEP）与分离式 Prefill

在本节中，我们将深入剖析专家并行，并进一步解释何谓*宽*专家并行。随后，我们将阐述分离式 Prefill（Disaggregated Prefill）的核心理念，剖析它与 WideEP 的区别，并探讨两者如何协同发力，最终实现 SOTA (业界领先) 性能。

## 宽专家并行（WideEP）

如今，大多数前沿 AI 实验室均采用混合专家 (MoE) 模型架构，而非稠密模型。在 MoE 架构中，每个 token 仅激活一小部分“专家”。例如，DeepSeek R1 的总参数量为 671B，但激活参数仅有 37B。具体而言，DeepSeek R1 拥有 256 个路由专家（以及 1 个共享专家），每个 token 会被路由至 8 个不同的专家。这种架构天然契合专家并行 (EP)，可将专家权重均匀分布在多张 GPU 上。

假设在单台 8 卡 GPU 服务器上部署 DeepSeek R1。面对 671B 的参数规模，必须引入某种并行策略，才能将模型装入现有的 HBM 中。最简单粗暴的方法是张量并行 (TP)，即将每个权重矩阵切分至所有 GPU。该策略在稠密模型上表现优异，却完全无视了 MoE 的稀疏激活模式。在 TP=8 的配置下，每个专家的权重被切分到全部 8 张 GPU 上。这意味着，尽管每个 token 仅激活 256 个专家中的 8 个，但每次专家激活都必须在所有 GPU 间执行一次全归约 (All-reduce)。此外，通用矩阵乘法 (GEMM) 的归约维度随之缩小，进而拉低了算术强度。TP 将每个专家等同于稠密层处理，不仅承担了全额的跨 GPU 通信开销，还白白浪费了模型的稀疏性优势。

专家并行 (EP) 采取了更契合的方案，将完整的专家分配给独立的 GPU。在 EP=8 时，我们将每层的 256 个专家划分至 8 张 GPU，即每张 GPU 承载 32 个专家/层。每张 GPU 容纳约 1/8 的专家权重，并保留一份完整的非专家权重副本（包含注意力投影、嵌入层、归一化层及共享专家）。由于 DeepSeek R1 中 90% 以上的参数均为路由专家权重，EP 实现了最大程度的内存节省；而在全部 8 张 GPU 上复制剩余不足 30B 的非专家参数，其成本完全可以承受。

每层的前向传播分为两个阶段。在注意力计算阶段，每张 GPU 作为独立的数据并行 (DP) Rank，利用其非专家权重副本处理专属的请求子集，全程无需跨 GPU 通信。进入 MoE 阶段后，轻量级路由器会判定每个 token 所需的专家，随后通过全对全 (All-to-all) 通信将 token 分发至对应的 GPU。每张 GPU 仅对路由至本地的 token 执行本地专家计算，计算结果再由第二次全对全 (All-to-all) 通信传回。

![](https://substackcdn.com/image/fetch/$s_!_wHq!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2f923fd4-57c0-418e-8b01-49025b9c48d5_8236x3544.png)

**DeepSeek R1 的 EP8 DP8 部署架构。每层全部 256 个专家被均匀划分至 8 张 GPU，而注意力层及其他非专家权重（共享专家、门控网络、RMSNorm、LM Head 等）则在所有 8 个 DP Rank 上保留完整副本。* 来源：SemiAnalysis*

最直观的扩展方式是直接复制：在 N 个节点上部署 N 个独立的 EP8 实例。各实例独立处理请求，全程无跨节点通信。这种做法能使吞吐量呈线性扩展，但每张 GPU 依然承载每层 32 个专家，且每个 token 至多激活这 32 个本地专家中的 8 个。高达 75% 的专家权重在 HBM 中处于闲置冷冻状态。

**宽专家并行 (WideEP)** 采取了截然不同的策略，它选择*跨*节点扩展 EP，而非简单复制独立实例。在包含 64 张卡的 GPU 集群（8 个节点）中，DP64/EP64 架构将每层分配给单张 GPU 的专家数量降至 256/64 = 4 个，同时每张 GPU 依然保留完整的非专家权重副本。进入 MoE 阶段后，来自全部 64 个 DP Rank 的 token 会通过全对全 (All-to-all) 通信，精准分发至承载其路由专家的目标 GPU 上。

与单节点 EP8 基线相比，这种方法能带来三重叠加优势。首先，将每张 GPU 承载的专家数量从 32 个减少到 4 个，为 KV 缓存释放了大量 HBM 空间，从而直接提升了单 GPU 的批处理容量。其次，64 个数据并行 (DP) Rank 将 token 集中输送给更少的专家，提升了“每专家处理的 token 数”，这不仅提高了算术强度（每加载一字节权重所执行的浮点运算次数），也改善了计算利用率。同样的专家权重，在每个步骤中能服务多达 8 倍的 token。第三，总 HBM 带宽随 GPU 数量线性增长；64 张 GPU 同时加载专家权重，提供了单节点 8 倍的显存带宽，缓解了显存瓶颈。

![](https://substackcdn.com/image/fetch/$s_!Hv_Z!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1ae2668e-28ef-4a1f-8ab1-0b5f1373a1d1_8476x3546.png)

DeepSeek R1 的 WideEP EP64 DP64 部署架构。每层全部 256 个专家被均匀划分至 64 张 GPU（8 个节点），而注意力计算及其他非专家权重（共享专家、门控网络、RMSNorm、LM Head 等）则在所有 64 个 DP Rank 间完全复制。*来源：SemiAnalysis*

上述配置仅使用了数据并行 (DP) 和专家并行 (EP) 的组合（也称 DEP），每张 GPU 都持有所有非专家权重的完整副本。随着 GPU 数量增长，这种复制方式的冗余和浪费问题也愈发突出。在一个 64-GPU 的 DP64/EP64 部署中，每张 GPU 都存储着一份完全相同的、约 400 亿参数的非专家权重。

在 GPU 组内增加张量并行 (TP) 可以解决这个问题。在 EP64/DP8/TP8 配置下，64 张 GPU 被组织成 8 个数据并行 (DP) 组，每组包含 8 张 GPU。在每个张量并行 (TP) 组内部，注意力投影、共享专家、归一化层和 LM Head 都被 8 路分片，因此每张 GPU 只需持有 1/8 的非专家权重。在整个集群层面，256 个专家仍然像之前一样，以每张 GPU 分配 4 个专家的形式分布。

纯粹的 DEP 模式只有一种通信模式：用于专家路由的全对全 (All-to-all) 通信。引入张量并行 (TP) 后，则增加第二种通信模式：在每个 TP 组内部，为处理注意力和非专家计算，需要进行全归约 (All-reduce) 通信。其关键设计原则是：将 TP 组置于单个节点内，利用 NVLink 或 MNNVL 提供的高带宽互连；而将专家并行 (EP) 和数据并行 (DP) 扩展到跨节点运行，因为其全对全 (All-to-all) 通信模式更能容忍较高的延迟。

与往常一样，这需要在吞吐量和延迟之间做出权衡。在一个组内实现 TP=8 意味着这 8 张 GPU 现在共享一个批处理任务，并且必须在每个解码步骤同步，这使得有效的数据并行 (DP) 度从 64 降至 8。在注意力计算方面，GPU 之间独立的批处理能力不复存在。但好处是，由于矩阵乘法在 TP 组内被 8 路拆分，每个 DP 组处理注意力计算的单步速度提升了 8 倍。最终结果是，单 token 延迟降低，但峰值并发度也随之下降，这使得该配置相较于纯 DEP 模式，在延迟-吞吐量的帕累托前沿曲线上发生了移动。

## 分离式 Prefill

分离式 Prefill（Disaggregated Prefill），有时也称为预填充-解码 (PD) 分离，是指在不同节点上分别执行 LLM 推理的预填充与解码阶段。预填充发生在请求首次被处理时，系统会一次性对所有 token 计算前向传播，从而为该请求“预填充” KV 缓存。由于所有 token 并行输入前向传播，这是一项计算密集型操作。随后，token 被逐一生成或“解码”，每个解码步骤都会从 HBM 加载 KV 缓存。由于不断增长的 KV 缓存需要被频繁加载，这便成了一个内存密集型过程。

在传统的单节点推理中，推理引擎在同一批 GPU 上交替执行预填充与解码。新涌入的预填充请求会阻塞正在处理的解码批次，导致首个 Token 延迟 (TTFT) 和 Token 间延迟双双飙升。分块 Prefill 通过将长预填充拆分为更小的块来缓解这一问题，但底层的资源争用依然存在。分离式 Prefill 则将这一痛点彻底根除！

![](https://substackcdn.com/image/fetch/$s_!FTlO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0bc87a96-aa31-4b37-99c6-603c98f332f3_1318x733.png)

来源：[DistServe](https://arxiv.org/abs/2401.09670)

分离架构还允许对各个阶段进行独立扩展与优化。借助独立的节点，每个阶段都能独立调优：采用不同的并行策略、不同的批处理大小以及不同的内存分配比例。预填充与解码节点的比例也能与工作负载的输入输出长度比相匹配。例如，以预填充为主的工作负载（长输入、短输出，如摘要生成、RAG、大上下文窗口的智能体编程）可分配更多预填充实例。而以解码为主的工作负载（短输入、长输出，如思维链推理、长文本生成）则可分配更多解码实例。 具有高缓存命中率的工作负载也更倾向于分配更多解码实例，因为来自共享系统提示词或多轮对话历史的复用 KV 缓存条目会完全跳过预填充阶段。

分离架构的核心成本在于 KV 缓存传输。预填充完成后，必须将该请求的完整 KV 缓存从预填充节点传输至解码节点，随后才能生成首个解码 token。对于像 DeepSeek R1 这样拥有 61 层且采用 FP8 KV 缓存的模型，8192 个 token 的预填充会产生约 500MB 必须跨网络传输的 KV 数据，这会直接推高首个 Token 延迟 (TTFT)。此传输通过 RDMA（通常是 RoCE 或 InfiniBand）进行，采用零拷贝的 GPU 到 GPU 数据移动，全程无需 CPU 介入。诸如 NIXL（英伟达推理传输库）等库将数据移动层抽象为一个统一的异步 API，并为 UCX、GPUDirect Storage 等传输协议提供可插拔的后端。 这使得推理引擎与任何特定的传输协议解耦，并实现了跨异构硬件的分离部署，让预填充与解码实例能够横跨不同的设备类型或互连网络。

![](https://substackcdn.com/image/fetch/$s_!knfc!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3b56d901-ef89-43c9-8d11-c18062f1b7b9_1165x1165.png)

来源：[Github](https://github.com/ai-dynamo/nixl/pull/1258)

## 利用 WideEP 与分离式服务优化推理

宽专家并行（WideEP）与分离式 Prefill 是两项独立的技术，但业界常将其组合使用以实现帕累托最优性能。本节我们将剖析 InferenceX 的实际测试结果，帮助大家建立直观认知：在不同的交互性水平下，究竟该如何合理搭配并行策略、宽 EP 与分离式 Prefill。

首先需要厘清，在单节点配置下，不同的并行策略分别落在帕累托前沿的哪个区间。以采用 TRT-LLM 框架、运行在单个 8-GPU B200 节点上的 DeepSeek R1 FP4 8k/1k 为例。随着我们在帕累托前沿上移动，最优策略也会随之切换，这主要由 Batch Size 及其对专家激活密度的影响所驱动。

在最高交互性区间（Batch Size 1-16），纯张量并行 (TP) 的表现全方位碾压任何包含专家并行 (EP) 的配置。在小 Batch Size 下，每步仅有极小比例的专家被激活。若采用 EP，这些激活负载在各 GPU 间的分布极不均衡：当 Batch Size 为 4 时，256 个专家中仅有 32 个被激活，在任意给定层中，单块 GPU 接收不到任何路由 token 的概率高达 10% 出头。TP 则通过将每个专家切分至所有 GPU 来规避此问题，因此无论路由器选中哪些专家，8 块 GPU 都能均等参与每一次专家计算。我们在对 DeepSeek R1 进行性能分析时，收集了专家激活率与 Batch Size 的对比数据，结果印证了当 Batch Size 在 16 及以下时，单层专家激活率确实极低。

![](https://substackcdn.com/image/fetch/$s_!M1tW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5ca10b5a-f80e-45b4-8d22-e3134d30b54d_2232x1446.png)

来源：SemiAnalysis

随着我们下探至交互性稍降的区间，Batch Size 依然偏小，专家权重仍通过 TP 而非 EP 进行切分。真正的转折点出现在 Batch Size 32 附近，此时单层约有 50-60% 的专家被激活。达到该密度后，EP 的负载不均衡已在可容忍范围内，且其 token 路由开销要低于 TP 强制要求的单专家全归约 (All-reduce) 成本。这一区间的配置开始采用张量-专家并行 (TEP)：注意力机制走张量并行（所有 GPU 协同完成每次注意力计算），混合专家 (MoE) 层走专家并行（专家被分配至特定 GPU，并辅以全对全 (All-to-all) 路由）。 在帕累托前沿上吞吐量最高、交互性最低的区间，Batch Size 极大（128+），配置全面转向完整的数据-专家并行 (DEP)：注意力权重作为独立的数据并行 Rank 在所有 GPU 上被完全复制，专家则通过 EP 进行分布式部署。系统以牺牲单 token 延迟为代价，将批处理容量压榨到极限；注意力权重在所有 DP Rank 上的完全复制，最终实现了吞吐量的最大化。

![](https://substackcdn.com/image/fetch/$s_!Qbqv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd13280a5-ddc2-4610-84bb-bf470301cc8e_2086x1233.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

当我们将分离式 Prefill 扩展到宽专家并行 (WideEP) 场景时，也观察到同样的通用模式。Prefill 和 decode 阶段采用各自独立的并行策略和节点数量，两者都针对具体的工作负载和目标交互性进行精细调优。以帕累托前沿上高吞吐、低交互性的一端为例，处理一个 8k/1k 工作负载（预填充任务繁重）。此时，Prefill 阶段是瓶颈，因为每个请求都需要对 8192 个输入 token 进行前向传播，计算开销极大。因此，该区间的方案会分配比 decode 节点更多的 prefill 节点（如 4P1D (4 个 Prefill 节点，1 个 Decode 节点)、7P2D、4P3D），以维持高 prefill 吞吐量。这些 prefill 节点运行数据-专家并行 (DEP) 配置，将注意力权重复制到各个独立的数据并行 Rank 上，从而实现对多个长上下文 prefill 请求的并行处理。 Decode 节点的数量较少，但其运行原理与单节点配置相同，即采用宽数据-专家并行 (wide DEP) 模式来处理大批量请求。

在帕累托前沿上追求高交互性的一端，并发请求数量较少，因此单个 prefill 实例就能跟上输入需求。然而，每个请求仍需要 1024 个 decode 步骤，而要实现高交互性，这些步骤就必须快。因此，该区间的方案转向分配比 prefill 节点更多的 decode 节点（如 1P3D、1P4D），每个 decode 实例都以小批量 (low batch size) 方式运行张量-专家并行 (TEP)。注意力计算上的张量并行通过将计算分片到实例内的所有 GPU 上，最大限度地降低了每一步的延迟；与此同时，在中等 Batch Size 这一负载均衡已足够高效的区间，专家并行 (EP) 负责处理混合专家 (MoE) 的路由。最终，通过采用多个小批量 decode 实例，而非少数几个大批量实例，既保持了较低的单 token 延迟，又提供了足够的并发服务能力。

![](https://substackcdn.com/image/fetch/$s_!LpAb!,w_474,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F61e2a61e-1b95-4ecb-a03d-061d15615c40_2086x1214.png)

来源：SemiAnalysis InferenceX

## DeepSeek R1 单节点结果深度解析

在 DeepSeek R1 FP8 1k1k 负载下，我们发现 MI355X 在单节点场景中与竞品 B200 旗鼓相当，尽管其在 FP4 多节点场景下被全方位碾压。在较低的交互性下，MI355X (SGLang) 的吞吐量性能甚至反超了 B200 (SGLang)。此外，从性能与 TCO 的维度来看，MI355X (SGLang) 在大多数情况下都击败了 B200（无论是运行 TRT 还是 SGLang）。

遗憾的是，现在已经是 2026 年了，大多数前沿实验室和推理服务提供商既不运行 FP8，也不搞单节点推理。

这一结果充分说明，AMD 的芯片非常出色，只要他们在软件层面能迭代得更快，就完全具备与英伟达一较高下的绝对实力。速度就是护城河。

![](https://substackcdn.com/image/fetch/$s_!F-j0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa4e8da6f-c4ee-4d39-96ae-9143459d3ea9_2102x1236.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!w0x6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7ce2b96f-840d-411b-9c6c-2f821219fba5_2130x1444.png)

来源：[SemiAnalysis InferenceMAX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

正因如此，我们看到 MI355X 在 FP4 性能上被 B200 远远甩在身后：

![](https://substackcdn.com/image/fetch/$s_!O75w!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdbc1dd2c-e15c-45b7-acf7-508d38ad1913_2406x1430.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

在对比 H200（SGLang）与 MI325X（SGLang）运行 DeepSeek R1 FP8 的性能时，我们发现，自去年 10 月首次发布 InferenceXv1 以来，整体格局并无太大变化。MI325X 的数据采集于 2026 年 2 月 12 日（使用 SGLang 0.5.8），而 B200 的数据采集于 2026 年 1 月 23 日（使用 SGLang 0.5.7）。

值得注意的是，MI325X 的交互性区间比 H200 窄得多：H200 的交互性在 30 到 90 tok/s/user 之间，而 MI325X 仅有 13 到 35 tok/s/user。对于希望在更宽泛的交互性区间内为用户提供服务的供应商而言，这无疑是个棘手的难题。

![](https://substackcdn.com/image/fetch/$s_!SI_q!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff3ba43db-8f65-4b28-a4a2-66282670449f_2117x1236.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21957492333&i_seq=8k%2F1k&i_prec=fp8#inference)

## GPT-OSS 120B 单节点

MI300X、MI325X、H200 和 H100 扎堆在吞吐量-交互性曲线图的左下方，表明它们的性能取舍大同小异，英伟达总体上占据微弱优势。再上一个台阶是 MI355X，在同等交互性下，其单 GPU 的 token 吞吐量比第一梯队高出两倍有余。在 MI355X 阵营中，ATOM 将曲线向低交互性、高吞吐量的方向拉扯，这表明它重保峰值吞吐量，而非单用户响应速度。

凌驾于该梯队之上的是英伟达的 B200 和 GB200，它们在整条曲线上全方位碾压 MI355X。尽管 B200 和 GB200 搭载相同的 Blackwell 计算裸片，但 GB200 推高了吞吐量-交互性曲线。这是因为其平台与 Serving 栈在集群规模下削减了非计算瓶颈（互连/拓扑、CPU-GPU 耦合以及运行时调度），进而转化为高效的横向扩展 (Scale-out)，并摊薄了单 token 的运行开销。

![](https://substackcdn.com/image/fetch/$s_!euhc!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F478b3a9a-c57d-4766-bde1-c3ee1fef550a_2068x1178.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

如果把成本因素纳入考量，MI355X 的竞争力便凸显出来：它在高吞吐量区间反超了 B200。然而，GB200 依然稳坐成本最低的头把交椅。

![](https://substackcdn.com/image/fetch/$s_!wliK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F028672d5-2c24-4dbd-974d-9f50d163df27_1796x1182.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

目光转回 B200 与 GB200 NVL72 的对决，NVL72 的威力显而易见。前文我们已经探讨过，GB200 NVL72 具备 72 块 GPU 的超大纵向扩展 World Size，而 B200 仅为 8 块 GPU。在约 100 tok/s/user 的交互性区间内，前者的单块 GPU 输出 token 吞吐量实现翻倍有余，这充分印证了 NVL72 更大纵向扩展域的强悍实力。

![](https://substackcdn.com/image/fetch/$s_!J3Ls!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0186cfbc-1b42-46ae-ae1a-0d7791afcb20_2081x1306.png)

来源：[SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

## InferenceX 核心代码库更新

我们对 InferenceX 代码仓库做了几处核心架构改动，让基准测试的理解与复现更加直观便捷。此外，我们已全面拥抱 AI 辅助，将生产力拉满，并大幅提升研发效能。

## InferenceXv1 以来的核心变更

自 v1 版本以来，我们做出的主要改动之一，是调整了执行遍历测试的节奏。以前我们纯属瞎折腾，每晚都会对每种配置进行一次完整的遍历测试。然而，随着我们加入了更多芯片、分离式 Prefill、宽专家并行 (EP) 等功能，我们意识到每晚都跑一遍测试实在是太耗时、太浪费了。更何况，这完全没必要——基准测试只在方案（recipe）变更或新版软件发布时才有必要重跑。

现在，我们改为根据代码仓库根目录下[更新日志](https://github.com/InferenceMAX/InferenceMAX/blob/main/perf-changelog.yaml)的新增内容来触发遍历测试。当开发者对特定配置做出影响性能的改动时，他们会在更新日志中添加一条记录，写明受影响的配置和改动简述。所有配置都定义在一个[主 YAML 配置文件](https://github.com/InferenceMAX/InferenceMAX/blob/main/.github/configs/nvidia-master.yaml)中，该文件是所有待测数据点的权威状态定义源，涵盖了输入序列长度 (ISL)、输出序列长度 (OSL)、专家并行 (EP)、张量并行 (TP)、数据并行 (DP)、多 Token 预测 (MTP) 等核心设置。当包含更新日志的 PR 被合并后，一个工作流会自动解析其中引用的配置项，从主配置文件中拉取相应的遍历测试定义，然后将其拆分为独立的 GitHub Actions 任务并分发执行。这些任务会为完整的遍历测试收集所有数据点，并将结果作为构建产物上传。

下图是 InferenceX 启动任务的流程示意图。

![](https://substackcdn.com/image/fetch/$s_!qJ_B!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F74936db5-88cb-418e-932a-e7a8693a6857_2904x2845.png)

## Klaud Cold AI 使用情况

InferenceX v1 发布后不久，我们意识到，由于在 InferenceX 开发中没有充分利用 AI，我们白白流失了多少开发者吞吐量。于是，我们撸起袖子，决定全面拥抱 Claude Code，开始逐个 token 地汲取智能，以至于目前的年化支出率已经飙到了每天 6000 美元。如果你想为我们“每年汲取价值 300 万美元 Claude 智能”的关键绩效指标 (KPI) 添砖加瓦，[请点击这里申请加入我们的征途。](https://app.dover.com/apply/semianalysis/2a9c8da5-6d59-4ac8-8302-3877345dbce1)我们的“开悟之旅”始于发现 GitHub Copilot 智能体竟然免费——起初我们简直不敢相信这功能居然不要钱！但我们很快就发现 Copilot 烂得一塌糊涂，GitHub 免费倒贴的原因自然也就不言而喻了。 估计你得*倒贴钱*，我们才肯继续用它。

自 Claude Code 发布以来，我们一直在本地使用它。但最近，我们已将 Claude Code 整合到 InferenceX 的开发中。除了让它处理审查 PR (Pull Request) 等常规任务外，我们还赋予了它在集群上执行遍历测试的能力。借助我们搭建的工作流，Claude 可以手动启动测试、查看结果并进行迭代。这让我们能够随时随地通过 GitHub 应用轻松部署快速修复。

另一个很酷的用例是让 Claude 为新的 vLLM/SGLang 镜像寻找配置方案。当新镜像发布时，配置方案有时也需要同步更新才能实现最佳性能（例如新增环境变量、修改引擎参数等）。整合 Claude Code 后，我们只需开一个 Issue，让 Claude 翻阅镜像变更日志中的所有提交记录，找出需要添加到配置方案中的必要改动。这招相当好使，虽然算不上*完美*，但通常能提供一个不错的起点。

## GitHub Actions

本着开源精神，所有运行均在 GitHub Actions 上进行，因此基准测试结果是可验证、透明且可复现的。然而，近期 GitHub 的频繁宕机成了我们实现目标的拦路虎。[最近我们看到（GitHub 宕机时的）独角兽的次数比什么动物都多](https://github.com/503.html)！或许我们真该下线去碰碰草（接触下大自然）了。

微软和 GitHub 官方自己也意识到了这一点。他们已经停止在状态页面上更新总体正常运行时间数据，而过去 90 天的数据更是跌到了单 9：97.36%。看来，掩耳盗铃并不能让问题凭空消失……

![](https://substackcdn.com/image/fetch/$s_!0uH0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3b921859-49f3-4b0b-b02e-dd0bf7a36e2e_3000x975.png)

来源：[Outages项目](https://github.com/outages/github-outages)

![](https://substackcdn.com/image/fetch/$s_!mh4e!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdd7aad58-ba30-4364-9565-980ae6464534_3000x975.png)

来源：[Outages项目](https://github.com/outages/github-outages)

总而言之，GitHub Actions 也就那么回事。它给开发者带来的体验平庸得让人抓狂，显然也不是为了在数百张 GPU 组成的集群上并发启动数千个任务而设计的。尽管如此，自发布以来，为了更好地满足 InferenceX 的需求，我们与几位 GitHub Actions 工程师展开了密切合作；我们可以由衷地说，与他们共事非常愉快。此外，我们的一个直接诉求是，在点击工作流运行时为任务实现懒加载。虽然确实花了不少时间，但[他们最终还是上线了这一功能。](http://github.blog/changelog/2025-12-22-improved-performance-for-github-actions-workflows-page/)

## InferenceX 的未来

自 2025 年 10 月初 InferenceX 首次发布以来，我们一直致力于持续改进。发布后，我们花时间重构了代码库，提升其可扩展性，现在已经可以“即插即用”地添加新模型和推理技术。正是基于这些改进，我们才得以无缝集成了针对 H100、H200、B200、B300、GB200、GB300 和 MI355X 的 PD-disagg 基准测试。此外，我们还在默认的基准测试流水线中加入了准确性评估，以确保模型在所有配置下的性能表现都清晰可见。

虽然发布至今我们已取得诸多改进，但要实现我们的北极星目标——提供最贴近真实世界的推理基准测试——仍然任重道远。为此，我们计划在真实数据集上进行基准测试、新增智能体编程性能基准测试、集成更多 SOTA (最先进) 的推理优化、测试更多模型，未来工作远不止于此。

## 向真实多轮对话与智能体编程数据集迁移

目前，InferenceX 使用完全随机的 token 作为基准测试的输入。随后，我们均匀调整输入序列长度（ISL），使其服从 [ISL*0.8, ISL] 的分布，输出序列长度（OSL）亦是如此。由于数据纯属随机，我们在所有基准测试中都禁用了前缀缓存，毕竟完全随机数据的前缀缓存命中率期望值为 0%。此外，所有随机数据均为单轮，即每次对话仅包含一次提示词和一次回复。虽然这勾勒出了不错的基准帕累托前沿，但它无法模拟真实生产环境的推理工作负载，并非实用的基准测试方案。

短期内，我们将利用类似 [allenai/WildChat-4.8M](https://huggingface.co/datasets/allenai/WildChat-4.8M) 这样的数据集，构建一个基础的多轮基准测试，以还原真实用户的多轮对话。除了在所有场景下启用前缀缓存，我们还将开启 KV Cache CPU 卸载，毕竟这正是实际生产环境中的常规操作。这将更精准地评估各款芯片的优劣。例如，MI355X 搭载 288GB HBM3e，而 B200 仅有 192GB。因此，我们预计 MI355X 在高并发多轮场景下性能更佳，因为它能为 KV Cache 分配更多显存。 另一方面，当 GPU KV Cache 承压、数据块被迫卸载至 CPU 时，我们预计 GB 系列芯片将大放异彩。这些芯片拥有高达 900GB/s 的双向 CPU-GPU 带宽，而配备 PCIe 5.0 和 6.0 的 HGX 带宽分别仅为 128GB/s 和 256GB/s。此外，目前我们观察到 AMD 在 CPU 卸载方面的软件表现相当糟糕，这可能会在此类场景下拖累性能。

核心逻辑在于：真实世界的多轮数据集能检验更多 SOTA 推理引擎特性，并能在所有芯片上捕获更细致、更扎实的性能数据。

随着 Claude Code、Codex 和 Kimi 的强势崛起，在智能体编程场景下进行性能基准测试变得愈发关键。与前文类似，这些场景不仅是多轮的，还包含超长上下文对话以及工具调用。在未来几个月内，我们计划打造一套基准测试套件，力求最精准地反映开源模型在各款芯片上运行此类智能体编程场景的真实性能。

## 新增 TPU、Trainium 及更多模型支持

目前，我们持续对 DeepSeek R1 和 GPT OSS 120B（此前也涵盖 Llama 3.1 70B）进行基准测试。为了紧跟最新模型架构，我们计划在未来几个月内，陆续引入 DeepSeek V3.2（带 DSA）、首发 (Day 0) 支持 DeepSeek V4，以及 Kimi K2.5、Qwen3、GLM5 等众多模型。我们最终还将加入多模态模型，并采用 EPD 与 CFD（由 TogetherAI 发明）优化技术。

除了新模型，我们正积极推进 TPU 与 Trainium 的适配工作。

## 总拥有成本（NVL72、Blackwell、Blackwell Ultra、MI355、Hopper、MI325、MI300）

横向对比同代产品，英伟达系统的资本成本通常高于 AMD 系统。这主要是因为其计算托盘的组件成本更高，而这又源于更高的 GPU 定价——众所周知，从财报来看，英伟达 GPU 的利润率远高于其他厂商。举例来说，MI300X 计算托盘的组件成本约为 13.8 万美元，而 H100 SXM 则约为 17 万美元，到了后几代产品，这一差距进一步拉大。MI355X 约为 19.7 万美元，B200 增至约 26.4 万美元，B300 则高达约 34.4 万美元。这些增加的芯片组件成本直接推高了服务器成本，并最终导致每台服务器的集群总资本支出水涨船高。

这一动态在 Blackwell 这一代产品中得以延续：GPU 组件成本的增加推高了服务器总成本，进而抬高了单台服务器的前期集群资本支出，最终导致了更高的资本拥有成本。

![](https://substackcdn.com/image/fetch/$s_!L152!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9d3c7c27-27ab-4a12-a1ac-b22996a4df53_2145x971.png)

来源：[SemiAnalysis AI TCO 模型](https://semianalysis.com/ai-cloud-tco-model/)

在同代产品中，每块 GPU 的运营成本大致相当，因为芯片的 TDP (热设计功耗) 是决定 TCO 中运营成本的主导因素。从 H100 升级到 GB300，这一成本随之上升，因为芯片 TDP 翻了一番，从而推高了每块 GPU 的每小时运营成本。

![](https://substackcdn.com/image/fetch/$s_!tU5P!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0679819d-cf11-4a22-bd5c-cf95554b77e8_2145x971.png)

来源：[SemiAnalysis AI TCO 模型](https://semianalysis.com/ai-cloud-tco-model/)
