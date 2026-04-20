# 推理王国的扩张

## 引言

### Groq LP30、LPX 机架、注意力与前馈网络解耦（AFD）、Oberon 与 Kyber 更新、英伟达光电共封装（CPO）路线图、Vera ETL256、CMX 与 STX

作者：[Dylan Patel](https://substack.com/@semianalysis)、[Myron Xie](https://substack.com/@myronxie)、[Daniel Nishball](https://substack.com/@danielnishball730869)及其他 7 人

2026 年 3 月 24 日 · 付费文章

![](https://substackcdn.com/image/fetch/$s_!dC_X!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff5522a45-77c1-40f8-94c0-395f272b8db1_2709x1815.png)

来源：英伟达

在 GTC 2026 上，英伟达带来了一场充满突破性发布的盛会。英伟达的创新步伐没有任何放缓的迹象，今年他们推出了三个全新的系统：Groq LPX、Vera ETL256 和 STX。此外，英伟达还宣布了对其 Kyber 机架架构系统的更新，随着 Rubin Ultra NVL576 和 Feynman NVL1152 多机架系统的亮相，光电共封装技术在纵向扩展（scale-up）网络中首次登场。关于 Feynman 架构的早期线索也是一个关键话题。黄仁勋在主题演讲中特别提及[InferenceX是一大亮点。](https://newsletter.semianalysis.com/p/inferencex-v2-nvidia-blackwell-vs)

这是我们的 GTC 2026 回顾，我们将解答英伟达留下的许多关键疑问。具体而言，我们将详细剖析 LPX 机架和 LP30 芯片，并解释注意力与前馈网络解耦（AFD）的工作原理；深入探讨 NVL144、NVL576 和 NVL1152 背后的各种机架架构细节，阐明其中将引入多少光学器件，以及高密度 Vera ETL256 背后的设计逻辑。下一代 Kyber 机架也迎来了一些重大更新与隐藏细节。

## Groq

首先来看 Groq LPU。近期 AI 基础设施领域最重大的事件之一，莫过于英伟达“收购” Groq。严格来说，英伟达斥资 200 亿美元获得了 Groq 的 IP 授权，并吸纳了其绝大部分团队。此举在实质上无异于收购，但其交易结构在法律层面上并未达到收购的标准，从而简化甚至规避了监管审批。鉴于英伟达的市场份额，如果该交易以全面收购的形式进行并接受反垄断审查，大概率会被否决。这种变相收购的另一大优势在于避免了漫长的交易交割流程，使英伟达得以立即接手 Groq 的知识产权与人才团队。 正因如此，在该交易宣布后不到四个月，英伟达就已经拿出了系统概念设计，并正将其整合至 Vera Rubin 推理堆栈中。

现在我们来回顾一下 LPU 架构，看看 Groq 的 LPU 如何与英伟达的 GPU 形成互补。更多细节[请参阅我们此前关于 Groq 的分析文章。](https://newsletter.semianalysis.com/p/groq-inference-tokenomics-speed-but)该文章的核心前提依然成立：使用独立的 Groq LPU 系统进行大规模 token 推理服务缺乏经济性，但其生成 token 的速度极快，从而能够享有极高的市场溢价。这正是 LPU 能够融入解耦解码系统背后的核心逻辑。

## LPU 芯片

Groq 首个且唯一公开宣布的 LPU 架构在其 ISCA 2020 论文中得到了详细阐述。与连接众多通用核心的典型硬件架构不同，Groq 将架构重新组织为多组单用途单元，这些单元与其他不同用途的单元组相连，他们将这些组命名为“切片（slices）”。在功能单元之间是流式寄存器（streaming registers）和便笺式 SRAM，用于功能单元之间相互传递数据。Groq 选择了单层便笺式 SRAM 而非多层内存层级结构，以确保硬件执行的确定性。

具体而言，LPU 架构包含用于向量运算的 VXM 切片、用于加载/存储数据的 MEM 切片、用于张量形状操作的 SXM 切片，以及用于执行矩阵乘法的 MXM 切片。在空间上，这些切片呈水平布局，允许数据水平流动。在切片内部，指令跨单元垂直泵送。从概念上看，LPU 类似于一个垂直泵送指令、水平泵送数据的脉动阵列（systolic array）。

![](https://substackcdn.com/image/fetch/$s_!0sYb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F83c55dd8-42b5-4f62-9551-6668222d528b_1204x581.png)

来源：Groq，SemiAnalysis

数据流和指令流的设计需要细粒度的流水线操作以实现高性能。由于 LPU 架构使计算具有确定性，编译器可以激进地调度和重叠指令以隐藏延迟。LPU 对高带宽 SRAM 的使用和激进的流水线设计，是实现 LPU 低延迟的两个主要因素。

第一代 LPU 基于传统的格芯（GlobalFoundries）14nm 制程节点设计，由 Marvell 负责芯片的物理设计。当其在 2020 年流片时，与同行相比这是一个成熟得多的制程节点，当时主流的 AI 芯片平台大多采用台积电（TSMC）的 N7 平台。对于一款专注于验证 Groq 架构并将其以推理为中心的设计推向市场的早期产品而言，这是合理的选择。14nm 制程节点已经成熟、相对容易被理解，并且适合用于初始芯片，因为在这一阶段，架构差异化比将硅片推向最前沿制程更为重要。

其卖点之一是，该芯片可以完全在美国本土制造和封装，相比之下，其竞争对手则严重依赖亚洲半导体供应链：逻辑芯片和封装在台湾地区完成，而 HBM 则来自韩国。

自那以后，由于执行问题，Groq 的路线图停滞不前，至今未出货第二代 LPU（LPU 2）。这使得 Groq LPU 在与竞争对手路线图的对比中显得更加过时。与 7nm 时代的同行相比，曾经显著但仍可控的制程节点劣势已经扩大为更为悬殊的差距，如今所有领先的加速器平台都将在 2026 年迈向 3nm 级制程。

后续的 Groq LPU 2 专为三星（Samsung）晶圆代工厂（foundry）的 SF4X 制程节点设计，具体在三星的奥斯汀晶圆厂（fab）生产，这使得他们能够延续 Groq 在美国本土制造的宣传口径。三星还为其提供后端设计支持。选择三星是出于其提供的优惠条款与投资，当时三星晶圆代工厂正难以为其先进制程节点寻找客户，且一直未能斩获 AI 逻辑芯片客户。毫不意外，三星是 Groq 随后在 2024 年 8 月 D 轮融资中的主要投资者，最近一次投资则发生在 2025 年 9 月英伟达“收购”之前。

然而，由于设计问题，Groq LPU 2 从未实现产品化。芯片上的芯片间串行器/解串器（C2C SerDes）无法达到宣传的 112G 速率，导致该设计出现故障，正如我们早前在[加速器模型](https://semianalysis.com/accelerator-hbm-model/)中所详述的那样。第三代 Groq LPU 才是英伟达将要产品化的版本。

## SRAM 与存储层级

我们之前曾撰文探讨过 SRAM 在存储层级中的作用，简而言之，SRAM 速度极快（低延迟且高带宽），但这是以牺牲密度为代价的，因此成本高昂。

因此，像 Groq 的 LPU 这样的 SRAM 机器能够实现极快的首个 token 生成时间和每用户每秒 token 数，但这以牺牲总吞吐量为代价。因为它们有限的 SRAM 容量很快就会被权重占满，几乎没有剩余空间留给随着批处理用户增多而不断增长的 KVcache。正如我们所展示的，GPU 在吞吐量和成本方面胜出。这就是为什么英伟达决定将这两种架构结合以实现优势互补：在像 LPU 这样低延迟、搭载大量 SRAM 的芯片上，加速那些对延迟更敏感且内存需求不大的解码部分；而将极其消耗内存的注意力机制交由配备大量快速（尽管不及 SRAM 快）内存容量的 GPU 来执行。

![](https://substackcdn.com/image/fetch/$s_!6Cix!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa939a961-40da-4762-b7d2-1ebb2423e9a2_2188x350.png)

来源：SemiAnalysis

这就引出了 Groq 3 LPU 或 LP30，而第二代 LPU 则被直接跳过。这款芯片没有英伟达的设计参与。影响第二代的 SerDes 问题似乎已得到修复。在付费内容中，我们将揭晓 SerDes IP 供应商，这可能会让人感到意外。英伟达还发布了 LP35，这是 LP30 的小幅更新版本，它将继续采用 SF4，并需要重新流片。它将集成 NVFP4 数值格式，但考虑到英伟达目前优先保证上市时间，我们预计不会有其他重大的设计变更。

![](https://substackcdn.com/image/fetch/$s_!iPH0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F39025ad5-927c-4619-b929-88d5555be853_1590x860.jpeg)

来源：英伟达

LPU 3 接近光罩极限尺寸的裸片布局与 LPU 1 非常相似。很大一部分面积被 500MB 的片上 SRAM 占据，只有极少部分面积分配给提供 1.2 PFLOPs FP8 算力的 MatMul 核心——这仅为英伟达 GPU 算力的一小部分。相比之下，LPU 1 拥有 230MB 的 SRAM 和 750 TFLOPs 的 INT8 算力，性能的提升主要得益于从 GF16 到 SF4 的制程节点迁移。由于采用单片式裸片设计，因此不需要先进封装。

依赖 SF4 的好处之一是它不会[像台积电的 N3 制程那样受到产能限制，这种限制给加速器产量设定了上限，也是整个行业仍然面临算力瓶颈的关键原因。](https://newsletter.semianalysis.com/p/the-great-ai-silicon-shortage)此外，该设计也不需要使用[同样受限于产能的 HBM](https://newsletter.semianalysis.com/p/memory-mania-how-a-once-in-four-decades)。这使得英伟达能够扩大 LPU 的生产规模，而无需牺牲或挤占其宝贵的台积电或 HBM 产能配额。这代表了其他任何人都无法获取的真正增量收入与产能。

既然英伟达已经接手，下一代 LP40 将采用台积电 N3P 制程制造并使用 CoWoS-R 封装。英伟达将注入更多自有 IP，例如支持 NVLink 协议而非 Groq 的 C2C。这将是首款与 Feynman 平台进行深度协同设计的 LPU。Groq 原计划的第四代 LPU 同样由台积电代工，并由 Alchip 作为后端设计合作伙伴。由于英伟达能够自行完成后端设计，Alchip 的参与现已显得多余。计划中的一项技术创新是采用混合键合 DRAM 来扩展片上内存，与 SRAM 相比，其延迟和带宽仅有轻微下降，但性能远高于传统 DRAM。SK 海力士已被选定为用于 3D 堆叠的 DRAM 供应商。 所有这些以及更多细节，早在此前的[加速器模型](https://semianalysis.com/accelerator-hbm-model/)中就已有详述。

![](https://substackcdn.com/image/fetch/$s_!4-mW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbf0a9df3-57f3-43b2-a090-67f9dbdee3d9_2218x1215.png)

来源：Nvidia, [SemiAnalysis Accelerator 模型](https://semianalysis.com/accelerator-hbm-model/)

## GPU 与 LPU 集成：Attention 与 FFN 解耦 (AFD)

![](https://substackcdn.com/image/fetch/$s_!269y!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F05b555ed-9d4e-45db-ad03-cbc1cc261b17_3064x1497.jpeg)

来源：英伟达

了解了 LPU 的优势后，我们就能理解它们如何融入推理架构。英伟达引入 LPU 是为了提升高交互场景的性能。在这些场景中，LPU 能够利用其低延迟特性来改善解码阶段（decode phase）的延迟。LPU 改善解码阶段延迟的方法之一，是应用在 [MegaScale-Infer](https://arxiv.org/abs/2504.02263) 和 [Step-3](https://arxiv.org/abs/2507.19427) 中提出的注意力与前馈网络解耦（Attention FFN Disaggregation (AFD)）技术。

正如我们在 [InferenceX 文章](https://newsletter.semianalysis.com/p/inferencex-v2-nvidia-blackwell-vs) 中所解释的，大语言模型（LLM）推理包含两个阶段：预填充（prefill）和解码（decode）。预填充阶段处理完整的输入上下文：它是计算密集型的，非常适合 GPU 处理。另一方面，解码阶段负责预测新 token，属于内存受限型（memory-bounded）任务。由于模型需要逐个预测新 token，解码阶段对延迟极其敏感，而 LPU 的高 SRAM 带宽和低延迟特性有助于加速这一迭代过程。

![](https://substackcdn.com/image/fetch/$s_!xoes!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F97ce6be2-5ef7-4770-85b8-d65ebda7c049_1887x551.jpeg)

来源：SemiAnalysis

注意力机制（Attention）和前馈网络（FFN）是模型中的两个操作子集。在模型的前向传播（forward pass）中，注意力机制的输出会输入给 token 路由器（token router），随后 token 路由器将每个 token 分配给 k 个专家（experts），其中每个专家都是一个 FFN。注意力机制和 FFN 具有截然不同的性能特征。在解码阶段，由于受限于加载 KV Cache，即使扩大批处理规模（batch size），注意力机制的 GPU 利用率也几乎没有提升。相比之下，FFN 的 GPU 利用率随批处理规模扩大的提升效果要好得多。

针对这一问题，我们已经与部分硬件供应商和存储公司合作，[使用我们的推理模拟器进行了超过 6 个月的研究。](https://semianalysis.com/institutional/inference-simulator/)

![](https://substackcdn.com/image/fetch/$s_!hooB!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc0bd1310-e0d9-4158-8959-b52bc3b65fab_577x409.jpeg)

来源：MegaScale-Infer，SemiAnalysis

随着最先进的混合专家（MoE）模型变得日益稀疏，token 可以从更大的专家池中选择专家。因此，每个专家接收到的 token 数量减少，导致利用率下降。这促使了注意力与前馈网络解耦。如果 GPU 仅执行注意力操作，其 HBM 容量就可以完全分配给 KV Cache，从而增加其能够处理的 token 总数，进而提高每个专家平均处理的 token 数量。

![](https://substackcdn.com/image/fetch/$s_!ZhUl!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc51c24d7-d5a7-4c99-a243-0baa24afbf08_1474x783.jpeg)

来源：SemiAnalysis

对比这两种操作，由于动态 KV Cache 加载模式，注意力机制是有状态的；相比之下，前馈网络（FFN）是无状态的，因为其计算仅依赖于 token 输入。因此，我们将注意力机制与 FFN 的计算进行解耦。我们将注意力计算映射到擅长处理动态工作负载的 GPU 上。对于 FFN，我们将其映射到 LPU 上，因为 LPU 架构具有固有的确定性，能够从静态计算工作负载中获益。

![](https://substackcdn.com/image/fetch/$s_!27kD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F65ead35a-ac7d-4416-b5d8-b2484e3e5a45_1217x372.jpeg)

来源：SemiAnalysis，MegaScale-Infer

在注意力与前馈网络解耦（AFD）架构下，从 GPU 到 LPU 的 token 路由可能成为瓶颈，在严格的延迟限制下尤为明显。token 路由流程包含两个操作：分发与合并。在分发阶段，我们通过 All-to-All 集合通信操作将每个 token 路由至其 top k 专家。专家完成计算后，我们执行合并阶段，通过反向 All-to-All 集合通信将输出结果发送回源位置，以继续下一层的计算。

![](https://substackcdn.com/image/fetch/$s_!XL7s!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffd5a62c2-81f4-4f64-b101-6a7e9e611fe6_830x1054.jpeg)

来源：SemiAnalysis

为了隐藏分发与合并的通信延迟，我们采用乒乓流水线并行。除了像标准流水线并行那样将批次拆分为微批次并实现计算流水线化之外，分发到 LPU 的 token 还会合并回源 GPU，从而在 GPU 与 LPU 之间进行乒乓式传输。

![](https://substackcdn.com/image/fetch/$s_!oNdF!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F15b11e7c-2540-46c1-92a2-ad4fe5b4e561_1400x673.jpeg)

来源：MegaScale-Infer

![](https://substackcdn.com/image/fetch/$s_!jmpy!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fefbdfe32-e16d-4a9b-bfd8-725d4b880569_1381x1082.jpeg)

来源：SemiAnalysis

![](https://substackcdn.com/image/fetch/$s_!G-iW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1204b3bb-7e16-4820-9a71-4171d79a719e_889x778.jpeg)

来源：SemiAnalysis

## 投机解码

LPU 改善解码阶段延迟的另一种方式是加速推测解码架构，即我们将草稿模型或多 Token 预测（MTP）层部署到 LPU 上。

对于上下文包含 N 个 token 的解码步骤，当前向传播期间添加 k 个额外 token（即对 k 个新 token 进行热预填充）时，只要 k &lt;&lt; N，延迟仅会略微增加。利用这一特性，推测解码使用小型草稿模型或 MTP 层来预测 k 个新 token；由于小模型每个解码步骤的延迟更低，因此能够节省时间。为了验证这些草稿 token，主模型只需对 k 个新 token 进行一次热预填充，其延迟代价大约相当于单个解码步骤。推测解码通常能将每个解码步骤的输出 token 数量提升 1.5 到 2 个，具体取决于草稿模型或 MTP 的准确率。凭借其低延迟特性，LPU 能够进一步增加节省的延迟并提升吞吐量。

![](https://substackcdn.com/image/fetch/$s_!cvnL!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4b9a77e7-dc29-4321-8f63-1c508cebc7e5_1335x671.jpeg)

来源：SemiAnalysis

对于 LPU 而言，部署草稿模型或 MTP 层与应用注意力与前馈网络解耦截然不同。FFN 是无状态的，而草稿模型和 MTP 层需要动态 KV 缓存加载。每个 FFN 的大小约为数百兆字节，而草稿模型和 MTP 层则占用数十吉字节。为了支持这种内存消耗，在 LPX 计算托盘上，LPU 可以通过每个 Fabric 扩展逻辑 FPGA 访问高达 256 GB 的 DDR5 内存。

## LPX 机架系统

让我们来看看 LPX 机架系统，其中包含一些值得关注的细节。英伟达展示了一个包含 32 个 1U LPU 计算托盘和 2 台 Spectrum-X 交换机的 LPX 机架。英伟达在 GTC 上展示的这个 32 托盘 1U 版本，与 Groq 被收购前的原始服务器设计非常接近。我们认为，该服务器配置并非第三季度出货的版本，英伟达正在对其进行修改。在此，我们将详细介绍目前所知的实际量产版本。这在[加速器模型](https://semianalysis.com/accelerator-hbm-model/)中已有详细说明。

![](https://substackcdn.com/image/fetch/$s_!_fd4!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F105f4b85-95b2-49c0-ad0a-7afa73fddff1_434x860.png)

来源：SemiAnalysis [Accelerator 模型](https://semianalysis.com/accelerator-hbm-model/)

#### LPX 计算托盘

每个 LPX 计算托盘或节点包含 16 个 LPU、2 个 Altera FPGA、1 个英特尔（Intel）Granite Rapids 主机 CPU 和 1 个 BlueField-4 前端模块。与其他英伟达系统一样，超大规模云服务商客户可以且将会使用其自选的前端网卡，而不是花钱购买英伟达的 BlueField。

![](https://substackcdn.com/image/fetch/$s_!6E50!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F45fbdc52-ed59-45e7-b666-5315c454d94b_1354x1851.png)

来源：SemiAnalysis [Accelerator 模型](https://semianalysis.com/accelerator-hbm-model/)

LPU 模块在 PCB 上采用正反面贴装，即 PCB 顶面安装 8 个 LP30 模块，底面安装另外 8 个 LP30 模块。LPU 引出的所有连接均通过 PCB 走线实现，考虑到节点内连接采用密集的全互联拓扑，这需要极高规格的 PCB 来支持布线。采用正反面贴装是为了缩短在“X”和“Y”维度上的 PCB 走线长度。

![](https://substackcdn.com/image/fetch/$s_!RBl1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F57bb1916-27a0-42d5-85c7-0f81c305cb3c_1839x399.png)

来源：SemiAnalysis [Networking 模型](https://semianalysis.com/ai-networking-model/)

该系统的一个有趣之处在于 FPGA 扮演了重要角色。英伟达将这些 FPGA 称为“Fabric Expansion Logic”，具备多种用途。首先，它们充当网卡（NIC），将 LPU 的 C2C 协议转换为以太网协议，以接入基于 Spectrum-X 的以太网横向扩展（scale-out）网络。LPU 正是通过该横向扩展网络连接至解码系统中的 GPU。

其次，LPU 也通过 FPGA 访问主机 CPU，在此过程中，FPGA 负责将 C2C 协议转换为 PCIe 协议与 CPU 通信。

第三，FPGA 连接至背板以与节点内的其他 FPGA 通信，我们认为这有助于管理所有 LPU 的控制流与时序。此外，每个 FPGA 还提供高达 256GB 的额外系统 DRAM。如果用户希望由 LPX 处理整个解码过程，这部分内存池可用于 KV 缓存（KVCache）。

前面板设有 8 个 OSFP 接口（cages），用于跨机架 C2C 连接；同时还有 2 个接口（可能是 QSFP-DD）连接至 Spectrum 交换机，用于在解耦的解码系统中连接 LPU 与 GPU。我们将在介绍网络部分时分享更多相关细节。

## LPU 网络

LPU 网络可分为纵向扩展的“C2C”网络，以及通过 Spectrum-X 与英伟达 GPU 交互的横向扩展网络。首先探讨纵向扩展网络，该网络可分为三部分：节点内、节点间/机架内、机架间。针对机架内的 C2C 连接，英伟达宣布单机架纵向扩展总带宽为 640TB/s，具体计算如下：256 LPUs x 90 lanes x 112Gbps/8 x 2 directions = 645TB/s。请注意，英伟达采用的是 112G 的线路速率，而非 100G 的有效数据速率。

#### 托盘内拓扑

![](https://substackcdn.com/image/fetch/$s_!i4Vn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff5b18381-6c96-4d0f-912e-e7978cc30446_1414x1617.png)

来源：SemiAnalysis [Networking 模型](https://semianalysis.com/ai-networking-model/)

在每个托盘或节点内，所有 16 个 LPU 均以全互联网状拓扑相互连接。每个 LPU 模块通过 4x100G 的 C2C 带宽与节点内的其他 15 个 LPU 相连。需要注意的是，这里的“C2C”与 NVLink 无关，而是 Groq 自有的纵向扩展互联架构。这些连接全部通过 PCB 走线实现，因此需要规格极高的 PCB 来支持如此庞大的布线密度。这也正是采用正反面贴装的原因：它缩短了所有 LPU 之间在“X”和“Y”轴上的距离，转而利用“Z”轴空间进行布线。

此外，每个 LPU 还有 1x100G 链路连接至一个 FPGA，而每个 FPGA 负责与 8 个 LPU 对接。这两个 FPGA 各自通过 8x PCIe Gen 5 链路连接至 CPU。由于 LPU 没有用于直接通信的 PCIe PHY，因此必须经过 FPGA 才能与 CPU 对接。

#### 节点间/机架内

![](https://substackcdn.com/image/fetch/$s_!xA-t!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F25d7c5ea-dce9-4703-9d95-eda3887a2e72_1066x1155.png)

来源：SemiAnalysis [Networking 模型](https://semianalysis.com/ai-networking-model/)

每个 LPU 连接到服务器中其他 15 个节点各一个 LPU。每条节点间链路的带宽为 2x100G，因此每个 LPU 引出 15x2x100G 的节点间链路。这些节点间链路通过铜缆背板实现连接。此外，每个 FPGA 也与其他每个节点中的一个 FPGA 相连，单条链路带宽为 25G 或 50G，总计 15x25G/50G。这同样通过背板进行路由。这意味着每个节点拥有 16 x 15 x 2 条用于节点间 C2C 的通道（lane），以及 2 x 15 条用于节点间 FPGA 的通道，总计 510 条通道，即 1020 对差分对（分别用于接收 Rx 和发送 Tx）。因此，背板共有 16 x 1020/2 = 8,160 对差分对——这里除以 2，是因为一个设备的发送（Tx）通道正好对应另一个设备的接收（Rx）通道。

#### 机架间

![](https://substackcdn.com/image/fetch/$s_!Wn2b!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Feaf1f2a7-972d-4d67-b1e8-aa596dcca070_3060x4100.png)

来源：SemiAnalysis [Networking 模型](https://semianalysis.com/ai-networking-model/)

最后是机架间 C2C 连接。每个 LPU 拥有 4x100G 通道，这些通道连接至 OSFP 笼（cages），用于跨 4 个机架连接 LPU。这种机架间向上扩展（scale-up）可以采用多种配置。一种方案是，每个 LPU 的 4x100G 通道接入同一个 OSFP 笼，每个 OSFP 接口引出来自 2 个 LPU 的 800G C2C 带宽。然而，为了实现更大的扇出（fan out），首选配置似乎是将 LPU 的每条 100G 通道分别接入 4 个独立的 OSFP 笼，每个 OSFP 笼引出来自 8 个 LPU 的 800G C2C 带宽。至于机架之间的网络连接方式，似乎采用了菊链配置（daisy chain configuration），每个 Node 0 分别连接到另外两个 Node 0。这些连接完全可以在 100G AEC（有源电缆）的传输距离内实现，当然，如有必要也可以使用光模块。

## 英伟达 CPO 路线图

英伟达在 GTC 2026 主题演讲中公布了其光电共封装（Co-Packaged Optics (CPO)）路线图，随后黄仁勋在次日举行的财务分析师问答会议上作了补充说明。尽管许多人曾期望光电共封装能用于 Rubin Ultra Kyber 机架内的向上扩展（scale-up），但英伟达的重点实际上是利用光电共封装来实现更大集群并行规模的计算系统。

![](https://substackcdn.com/image/fetch/$s_!7CeZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7d80c4f7-60e6-41ea-859b-f4ad8ddbf5ea_2064x397.png)

来源：[SemiAnalysis AI网络模型](https://semianalysis.com/ai-networking-model/)，英伟达（NVIDIA）

**在 Rubin 世代**，英伟达将提供采用全铜向上扩展网络的 Oberon NVL72 形态的 Rubin GPU。对于 Rubin Ultra，正如我们预期的那样，在 Oberon 和 Kyber 机架形态中，Rubin Ultra 将仅提供基于铜缆的向上扩展选项。Rubin Ultra 还将提供更大集群并行规模的系统版本，该系统将 8 个配备 72 颗 Rubin Ultra GPU 的 Oberon 机架连接起来，形成所谓的 NVL576。光电共封装的向上扩展将用于构建这种更大的集群并行规模，在机架之间通过两层全互联（all-to-all）网络进行连接，不过机架内部的向上扩展仍将基于铜缆。

**到了 Feynman 世代**，光电共封装的应用范围将通过另一个大集群并行规模机架 NVL1152 进一步扩大，该机架由 8 个 Kyber 机架组合而成。虽然概述机架配置路线图的[英伟达技术博客](https://developer.nvidia.com/blog/nvidia-vera-rubin-pod-seven-chips-five-rack-scale-systems-one-ai-supercomputer/)指出，“英伟达 Kyber 将使用类似的直接光学互连进行机架间向上扩展，从而向上扩展为庞大的全互联 NVL1152 超级计算机”，但黄仁勋在财务分析师问答环节中确实表示，Feynman 世代的 NVL1152 将是“全光电共封装（all CPO）”。关于机架内的向上扩展是继续使用铜缆还是由光电共封装取代铜缆，目前仍存在一些分歧。

英伟达的策略一直是：能用铜缆的地方就用铜缆，必须用光学互连的地方才用光学互连。Feynman 世代 NVL1152 的架构也将遵循同样的原则。显然，NVL1152 将采用光电共封装进行机架间连接，但从 GPU 到 NVLink 交换机的连接目前在计划记录（POR）中仍是铜缆。英伟达无法实现电通道速率从 224Gbit/s 双向再次翻倍至 448Gbit/s 单向，这意味着带宽表现并没有那么惊人。

尽管与采用裸片间（die-to-die）连接至光学引擎相比，448G 高速 SerDes 在芯片边缘面积（shoreline）、传输距离和功耗方面面临巨大挑战，但考虑到 Feynman 在制造难度、成本和可靠性上的综合考量，连接至交换机的链路依然必须使用铜缆。

话虽如此，NVL1152 SKU 距离问世还有数年时间，路线图极有可能发生变化。目前，我们的基准预测仍是机架内部使用铜缆、机架之间使用光电共封装，但这很容易发生改变。

目前，我们对英伟达光电共封装路线图的最佳预测如下：

Rubin：

- NVL72 —— Oberon 全铜向上扩展

Rubin Ultra：

- NVL72 —— Oberon 全铜向上扩展

- NVL144 —— Kyber 机架全铜向上扩展

- NVL288 —— Kyber 机架全铜向上扩展，通过铜缆将 2 个机架连接在一起

- NVL576 —— 8 个 Oberon 机架，机架内部采用铜缆向上扩展，机架间的交换机采用光电共封装，构成两层全互联拓扑。该配置产量较低，主要用于测试目的。

Feynman：

- NVL72 —— Oberon 机架 —— 全铜

- NVL144 —— Kyber 机架 —— 全铜

- NVL1152 —— 8 个 Kyber 机架 —— 机架内部采用铜缆，机架间的交换机采用光电共封装

![](https://substackcdn.com/image/fetch/$s_!NjAg!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F10cf337a-41ad-4a0e-b9a3-bd2f11c911f0_2389x905.png)

来源：SemiAnalysis，英伟达

## Oberon 与 Kyber 更新：引入更大集群规模及更多网络更新

英伟达对其 Kyber 机架形态进行了期待已久的更新，这是继 Oberon 之后产品线的最新成员，其原型曾在 GTC 2025 上首次预览。作为原型，该机架架构不断演进，我们注意到了一些变化。首先，每个计算刀片的密度提升，分别配备 4 个 Rubin Ultra GPU 和 2 个 Vera CPU。共有 2 个机箱（canister），每个机箱包含 18 个计算刀片，即总共 36 个计算刀片，单机架共计 144 个 GPU。最初的 Kyber 设计在单个计算刀片中配备 2 个 GPU 和 2 个 Vera CPU，共有 4 个机箱，每个机箱 18 个计算刀片。

以下细节基于 Rubin Kyber 原型，但 Rubin Ultra 版本将被重新设计。

![](https://substackcdn.com/image/fetch/$s_!57WO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6e91ff96-9d44-4d04-8a1f-eeb1575b235d_3000x4000.jpeg)

来源：SemiAnalysis

与 GTC 2025 上的原型相比，每个交换机刀片的高度也增加了一倍，每个交换机刀片配备 6 个 NVLink 7 交换机，每个机架配备 12 个交换机刀片，每个 Kyber 机架总计 72 个 NVLink 7 交换机。GPU 通过 2 块 PCB 中板（即每个机箱 1 块中板）与交换机刀片实现全互联。

![](https://substackcdn.com/image/fetch/$s_!lj22!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4c5a1ad2-cfca-47a0-be02-f39b150e8df4_3000x4000.jpeg)

*Kyber 中板 PCB（GPU 侧）。来源：英伟达，SemiAnalysis*

对于 Rubin Ultra NVL144 Kyber，[正如我们多次告知客户的那样，向上扩展网络不会使用光电共封装](https://semianalysis.com/institutional/multi-vertical-note-kyber-cpo-sku-will-be-a-low-volume-test-rack/)，尽管其他分析师有传言称 Kyber 将引入用于向上扩展的光电共封装。然而，用于 NVLink 的光器件即将到来，并将逐步引入。向上扩展的光电共封装将首先用于 Rubin Ultra NVL 576 系统，以连接 8 个 Oberon 形态的机架，形成两层全互联网络。不过，机架内部的向上扩展网络仍将使用铜缆背板。这目前仍用于小批量生产或测试目的。

回到 Kyber 机架，每个 Rubin Ultra 逻辑 GPU 提供 14.4Tbit/s 的单向向上扩展带宽，每个 GPU 使用一个 80DP 连接器（使用 72 个 DP x 200Gbit/s 双向通道 = 14.4Tbit/s）连接至中板。在全互联网络中连接所有 144 个 GPU，需要 72 颗 NVLink 7.0 交换芯片，每颗芯片的单向聚合带宽为 28.8Tbit/s。

![](https://substackcdn.com/image/fetch/$s_!028i!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa6507cbc-367c-4f8e-9f8a-6fcbccf61aa3_1513x655.png)

来源：SemiAnalysis

在下方的 Kyber 交换机刀片图片中，我们可以看到有两个独立的 PCB，每个 PCB 搭载 3 颗交换芯片。该交换机刀片应有 6 个 152DP 连接器，每 3 个连接器服务于一块中板。图片展示的是采用较低密度连接器的原型刀片，因此配备了 12 个连接器，而非量产版本预期的 6 个。

![](https://substackcdn.com/image/fetch/$s_!ET6V!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1bef24fc-b8ed-4652-a928-7abd4cf2d496_4000x3000.jpeg)

来源：英伟达，SemiAnalysis

每颗 28.8T NVLink 交换芯片拥有 144 条 200G 通道（同时双向传输），这意味着每颗交换芯片有 24 条 200G 通道接入各个连接器。由于物理距离对 PCB 走线而言过长，因此采用铜质飞线电缆将每颗交换芯片连接至中板。这也是交换芯片远离中板的原因，为飞线电缆的布线提供空间。

![](https://substackcdn.com/image/fetch/$s_!-biX!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F376fc839-5860-4555-a18c-3b591ec13156_1582x1372.png)

来源：SemiAnalysis [Networking 模型](https://semianalysis.com/ai-networking-model/)

每颗 NVLink 交换芯片通过 Flyover 线缆连接到交换机刀片边缘的连接器（使用 144 个 DP x 200 Gbit/s 双向通道 = 28.8Tbit/s），这些连接器随后插入中板。英伟达正在研究使用共封装铜缆来进一步降低损耗，以防 NPC 方案不可行。据我们所知，英伟达正指示供应链全面转向共封装铜缆。

#### Rubin Ultra NVL288

尽管英伟达在 GTC 2026 上并未正式讨论，但供应链内部已经对 NVL288 概念进行了探索。该方案需要将两个 NVL144 Kyber 机架相邻放置，并使用机架间的铜背板将两者连接。一种可能性是所有 288 颗 GPU 实现全互联，但这将需要比当前 NVLink 7 交换芯片更高端口数的交换机，目前的 NVLink 7 交换芯片最多仅提供 144 个 200G 端口。

如果部署 Rubin Ultra NVL288，每颗 Rubin Ultra GPU 将拥有 14.4Tbit/s 单向的 scale-up 带宽，需要 144 个 DP 的线缆来连接 NVLink 7 交换芯片。每颗 GPU 72 个 DP 乘以 288 颗 GPU，意味着连接这个更大的集群并行规模域总共需要额外 20,736 个 DP。这涉及大量的线缆，因此它代表了线缆用量的上限。

28.8T NVLink 交换芯片的端口数限制了每颗交换芯片在保证跨机架连接的同时所能连接的 GPU 数量。要么必须使用更高端口数的交换机，要么该架构必须引入一定程度的超订，并可能采用类似 Dragonfly 的网络拓扑。这也将减少所需的铜缆 DP 数量。

![](https://substackcdn.com/image/fetch/$s_!YbDc!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faddf00bd-ed41-47b8-864e-35e96b6768c1_1613x1158.png)

来源：SemiAnalysis

目前供应链中的所有证据均表明，NVSwitch 7 的带宽与 NVSwitch 6 相同，但坦率地说，这似乎有些不合逻辑。我们认为，NVSwitch 7 的带宽和端口数实际上是 NVSwitch 6 的 2 倍，从而能够实现全互联（all-to-all）。从系统角度来看，这在架构上是最合理的。

#### Rubin Ultra NVL576

为了将 scale-up 集群并行规模扩展至 144 颗 GPU 以上并跨越多个机架，必须引入光学器件，因为我们正在逼近铜缆互联所能支撑的最大计算密度极限。Rubin Ultra NVL576 现已列入路线图，该方案包含 8 个密度较低的 Oberon 机架。

![](https://substackcdn.com/image/fetch/$s_!kVKx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fee215fef-65ff-41ce-be3d-1a54c3af2334_2449x1037.png)

来源：SemiAnalysis

机架间连接必须使用光学器件。尽管严格来说，目前尚未确认是采用可插拔光模块还是光电共封装（Co-Packaged Optics (CPO)），但采用 CPO 的可能性显然大得多。目前的 Blackwell NVL576 原型机“Polyphe”使用的是可插拔光模块。

我们此前已经 [展示过针对 GB200 的 NVL576 概念方案](https://newsletter.semianalysis.com/i/175661160/gb200-nvl576)，该方案使用可插拔光模块来互连第二层 NVLink 交换芯片。采用可插拔光模块会导致 BOM 成本激增，从 TCO 的角度来看，这使得构建交换全互联系统的方案变得不可行。然而，Rubin Ultra NVL576 很有可能会在 Feynman NVL 1,152 之前进行测试性的小批量生产，而在后者上，我们将看到 scale-up CPO 的实际规模化量产。

这对下游供应链的深远影响已在我们的机构研究报告中予以揭示，我们的研究深受各大超大规模云服务商、半导体公司及 AI 实验室的信赖，详情请联系 sales@semianalysis.com。

#### Feynman

虽然关于 Feynman 的已知信息不多，但主题演讲中的惊鸿一瞥足以让我们确认 Feynman 将令人振奋，它在单一平台上同时推进了三项重大技术创新：[混合键合/SoIC](https://newsletter.semianalysis.com/p/hybrid-bonding-process-flow-advanced?utm_source=publication-search)、A16、[光电共封装](https://newsletter.semianalysis.com/p/co-packaged-optics-cpo-book-scaling?utm_source=publication-search)以及[定制HBM](https://newsletter.semianalysis.com/i/174558655/custom-base-die)。

虽然 Feynman 采用光电共封装已在路线图上，但问题在于采用的程度如何？机架内互连将基于铜缆还是光学器件？我们将在付费墙后展示可能的配置。**Vera ETL256**

随着 AI 工作负载在 GPU 计算之外需要更多的数据处理、预处理和编排，对 CPU 的需求正在上升。强化学习进一步推高了这一需求，因为 CPU 需要并行运行模拟、执行代码并验证输出。由于 GPU 的扩展速度快于 CPU，因此需要更大的 CPU 集群来保持 GPU 的充分利用，这使得 CPU 日益成为瓶颈。

Vera 独立机架直接解决了这一问题，通过将 256 个 CPU 容纳在单个机架中实现了前所未有的密度——这一壮举必须采用液冷技术。其底层逻辑与 NVL 机架的设计理念如出一辙：将计算组件进行高密度化封装，使得铜缆互连能够覆盖机架内的所有组件，从而消除在主干网络上使用光模块的需求。铜缆带来的成本节约足以抵消额外的散热开销。

![](https://substackcdn.com/image/fetch/$s_!KfPw!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc9e8a2b9-8417-41bc-aa32-1072b2e68fc0_3000x4000.jpeg)

来源：SemiAnalysis

每个 Vera ETL 机架包含 32 个计算托盘（上下各 16 个），对称排列在中间的 4 个 1U MGX ETL 交换机托盘（基于 Spectrum-6）周围。这种对称布局是经过深思熟虑的：它最大限度地减少了计算托盘与主干之间的线缆长度差异，确保所有连接都在铜缆的覆盖范围内。在每个交换机托盘上，后置端口连接到该铜缆主干以实现机架内通信，而 32 个前置 OSFP 接口则为 POD 的其余部分提供光学连接。

机架内网络采用 Spectrum-X 多平面拓扑，将 200 Gb/s 通道分布于四台交换机中，在保持单一网络层级的同时实现完整的全互联。每个计算托盘容纳 8 个 Vera CPU，单个机架总计 256 个 CPU，所有 CPU 均通过单一扁平网络经以太网互联。

![](https://substackcdn.com/image/fetch/$s_!UMo8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F31febbf5-a0ec-4218-b2d0-e95e40704213_4000x3000.jpeg)

来源：SemiAnalysis

![](https://substackcdn.com/image/fetch/$s_!At98!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F91ab19c1-1ceb-4b0b-a13e-6de00121eebd_1427x199.webp)

来源：[英伟达](https://developer.nvidia.com/blog/nvidia-vera-rubin-pod-seven-chips-five-rack-scale-systems-one-ai-supercomputer/)

## CMX 与 STX

我们在上一篇关于 Rubin 的文章以及内存模型中，已经对英伟达的 CMX（即 ICMS 平台）进行了详尽的探讨。英伟达此次推出了 STX 参考存储机架架构。

#### CMX

**CMX** 是英伟达的上下文内存存储平台。CMX 解决了现代推理基础设施中日益凸显的瓶颈：即为了支持长上下文和智能体工作负载（agentic workloads），所需的 **KV Cache** 正在快速膨胀。

KV 缓存随输入序列长度和用户数量呈线性增长，也是影响预填充性能（首个 Token 生成时间）时的主要权衡因素。在大规模场景下，设备端 HBM 的容量往往捉襟见肘。主机 DRAM 作为额外的缓存层，虽然扩展了 HBM 之外的容量，但同样会触及单节点总容量、内存带宽以及网络带宽的极限。这就需要引入 NVMe 存储来进行额外的 KV 缓存卸载。

英伟达在今年 1 月的 CES 上，为推理内存层级引入了一个“全新”的中间存储层“G3.5 层”。G3.5 层 NVMe 介于 G3 层 DRAM 与 G4 层共享存储（同样为 NVMe，或 SATA/SAS SSD，或 HDD）之间。它此前被称为 **ICMS（推理上下文内存存储）**，如今被重新命名为 **CMX 平台**，这本质上只是将通过 Bluefield 网卡连接至计算服务器的存储服务器进行了又一次品牌重塑。其与传统 NVMe 架构的唯一区别，仅仅是将 Connect-X 网卡替换为了 Bluefield 网卡。

![](https://substackcdn.com/image/fetch/$s_!wa5A!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb3a0a186-dbca-4e82-b477-f41c8148e2f3_1336x1258.jpeg)

来源：2026 年 1 月发布的英伟达 ICMS 原博客——于 2026 年 3 月 16 日更新并重新发布 [https://developer.nvidia.com/blog/introducing-nvidia-bluefield-4-powered-inference-context-memory-storage-platform-for-the-next-frontier-of-ai/](https://developer.nvidia.com/blog/introducing-nvidia-bluefield-4-powered-inference-context-memory-storage-platform-for-the-next-frontier-of-ai/)

#### STX

为了拓展 CMX 的应用范围，英伟达还推出了 STX。STX 是一种参考机架架构，采用英伟达基于 BF-4 的存储解决方案，作为 VR 计算机架的补充。该参考架构精确规定了特定集群所需的驱动器、Vera CPU、BF-4 DPU、CX-9 NIC 以及 Spectrum-X 交换机的确切数量。

![](https://substackcdn.com/image/fetch/$s_!p_Sv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fddb9b036-0027-4510-975b-9c707ca486c4_3000x4000.jpeg)

*STX 中的 BF-4。来源：英伟达，SemiAnalysis*

VR NVL72 中的 BF-4 由单颗 Grace CPU 和单张 CX-9 NIC 组成。相比之下，STX 参考设计中的 BF-4 则包含单颗 Vera CPU、两张 CX-9 NIC 以及两个 SOCAMM 模块。每个 STX 机箱内置两个 BF-4 单元，共计两颗 Vera CPU、四张 CX-9 NIC 和四个 SOCAMM 模块。整个 STX 机架共包含 16 个机箱，即总共配备 32 颗 Vera CPU、64 张 CX-9 NIC 和 64 个 SOCAMM 模块。

![](https://substackcdn.com/image/fetch/$s_!N7af!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F31ef2de0-8f01-45f0-bea0-0fca1c8744ee_878x1030.png)

*STX 机架（左）。来源：英伟达，SemiAnalysis*

在发布 STX 时，英伟达进行了典型的实力展示，宣布所有主流存储供应商均支持 STX，其中包括 AIC、Cloudian、DDN、Dell Technologies、Everpure、Hitachi Vantara、HPE、IBM、MinIO、NetApp、Nutanix、Supermicro、Quanta Cloud Technology (QCT)、VAST Data 和 WEKA。

综合来看，BlueField-4、CMX 和 STX 体现了英伟达致力于在存储层面对集群设计进行标准化的宏大布局。英伟达已经主导了计算和网络层，并正逐步向存储、软件以及基础设施运营层积极扩张。

接下来在付费内容中，我们将分享更多关于这一切将如何影响供应链的细节，包括 LPX 系统以及更新版 Kyber 机架的受益厂商。我们还将揭晓一款英伟达尚未公布的机架概念。

## Feynman NVL1152 网络拓扑

在每个 Feynman Kyber 机架内，我们暂且假设每个逻辑 GPU 的带宽和 NVLink 交换机带宽均翻倍，分别达到 28.8T 和 57.6T。尽管 Jensen 在 GTC Keynote 次日的财务问答环节中，将 NVL1152 描述为“全光电共封装（CPO）”，但[概述新机架形态的关键技术博客](https://developer.nvidia.com/blog/nvidia-vera-rubin-pod-seven-chips-five-rack-scale-systems-one-ai-supercomputer/)仅明确指出机架间互连采用了光电共封装。我们将探讨这两种方案的潜在拓扑结构。

若要使用铜互连将 scale-up 带宽翻倍，英伟达必须实现每通道 448Gbit/s 单向带宽（并采用同步双向 SerDes，使每个物理通道承载 448G 的 RX 和 448G 的 TX）。然而，这是一项艰巨的挑战，因为他们首先必须证明大批量生产 448Gb/s PAM4 SerDes 的可行性，然后还要实现[回波抵消以实现双向带宽](https://newsletter.semianalysis.com/p/vera-rubin-extreme-co-design-an-evolution)，这本身就极其困难。我们认为英伟达只会采用 448G 单向方案。

![](https://substackcdn.com/image/fetch/$s_!i-U0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd34ddb8c-e8ae-4e4e-8478-62996d8775e7_1799x952.png)

来源：SemiAnalysis

Feynman 可以采用机架内光互连，即交换机刀片通过光学连接器与中板盲插连接，并使用细光纤束代替飞线电缆将光学连接器连接到 NVLink 8 交换机。但我们认为这极不可能。

![](https://substackcdn.com/image/fetch/$s_!uIm6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fecaed357-cd0b-4635-99c4-70bc5cf9fec9_1782x930.png)

来源：SemiAnalysis

针对机架间互连，我们探讨两种不同的拓扑结构。第一种是两层 CLOS 网络，它类似于 Oberon 形态，但每个 GPU 和 NVLink 交换机的带宽均翻倍。

![](https://substackcdn.com/image/fetch/$s_!JB0C!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0cb78043-cb1d-4d66-9f72-d97c1cefe4de_1062x462.png)

来源：SemiAnalysis

第二种是采用 OCS 交换机连接这 8 个机架的可重构蜻蜓拓扑。该拓扑所需的 OCS 端口数量暂未确定。

![](https://substackcdn.com/image/fetch/$s_!HR-M!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe606aa58-6349-444b-92f5-bf49c165ae4d_1141x1225.png)

来源：SemiAnalysis

## GTC 2026 供应链影响

在此，我们将探讨我们的调查发现，分析 GTC 上的这些发布将为供应链价值量带来哪些重大变化。

#### LP30 中的 AlphaWave 112G SerDes

读者可能会感到惊讶，高通（Qualcomm）竟然在 Groq LPU 3 芯片中拥有 IP！具体而言，是高通去年收购的 AlphaWave 为 Groq 的 C2C 互联提供 112G SerDes。AlphaWave 之所以入选，是因为它是唯一能为三星晶圆代工厂提供高速 SerDes 的 IP 供应商。此前正是 AlphaWave 的 SerDes 导致了 Groq LPU 2 出现问题。LP35 将继续使用 AlphaWave，但当 LP40 重新转回台积电代工时，英伟达显然会使用自家的 NVLink SerDes IP。

#### LPX PCB

接下来，我们曾提到 LPX 计算托盘需要极高规格的 PCB。我们预估每块计算托盘主板 PCB 的平均售价（ASP）将达到 7000 美元。其供应商为胜宏科技（Victory Giant）和沪电股份（WUS）。当然，计算托盘中还有其他几个 PCB 模块，但它们不需要如此高的规格。英伟达延续了与 Vera Rubin 计算托盘类似的无缆化设计理念，这需要大量板对板连接器，这也引出了下一个主要受益方。

#### 线缆与连接器：Amphenol 持续受益

对于 LPX 而言，Amphenol 将成为背板所有连接器的受益方。每个 LPX 节点需要 16 个 80DP Paladin 连接器用于背板。此外，还需要板对板连接器来连接托盘内的各个模块：将主 LPU 板与主机 CPU 模块、位于 CPU 模块下方的 OSFP/QSFP 模块、前端网卡（NIC）模块以及管理模块连接起来。Amphenol 也将供应线缆背板，每个机架包含 8,160 个差分对（DP）。

#### NVL288 系统

对于我们在上文讨论过的 Vera Rubin Ultra NVL288 系统，可以说线缆背板将在 Kyber 中回归。如果 Rubin Ultra 采用这种形态部署——每颗 Rubin Ultra GPU 将具备 14.4Tbit/s 单向的纵向扩展带宽，需要 144 个 DP 线缆连接至 NVSwitch。144 个 DP 乘以 288 颗 GPU，意味着总共需要 41,472 个 DP 才能连接这个更大的集群并行规模域。这涉及庞大的线缆数量，因此它更像是此处线缆用量的上限。如果存在超分（oversubscription），或者机架间连接通过交换机进行，那么实际所需的 DP 数量可能会更少。

#### FIT 入局

背板线缆插接件与 Paladin 连接器的需求极为强劲，导致 Amphenol 的产能已无法跟上供应。Amphenol 现已完成将 VR NVL72 背板线缆插接件以及 Paladin HD 连接器对 FIT 的授权，后者现可制造这些组件。此事已筹备多时，如今终于尘埃落定。Amphenol 将从 FIT 销售的这些授权组件中赚取授权费。

#### Kyber Voronoi——FIT 的又一次胜利？

Kyber 中板将使用大量 8×19 DP 连接器，用于与机架前端的计算托盘以及机架后端的交换机刀片进行接口连接。

对于 Kyber 而言，英伟达目前在 IP 方面占据了主导地位，并设计了一款名为 Voronoi 的专有连接器规格，因此将不再使用 Amphenol 的 Paladin 连接器。目前有三家供应商竞标该项目：FIT、Molex 和 Amphenol。FIT 似乎在这些连接器的市场中处于领先地位，但据报道，Amphenol 也在与 FIT 密切合作制造这些连接器。Voronoi 的设计与实现仍处于变动之中，但 FIT 和 Amphenol 都需要利用从英伟达获得的规格授权来大幅提升产量。

中板、交换机托盘和计算托盘均配备母头连接器，这将需要使用带有弹簧结构的公头部件，以保护引脚并在两侧之间实现接口连接。这些连接器的密度最终将远高于 Amphenol 的 Paladin 连接器。

更多内容仅供我们的机构订阅客户阅读，请联系 sales@semianalysis.com。

#### 板载光学——英伟达向可插拔模块宣战

有趣的是，在 GTC 2026 展区展出的 Kyber 机架缺少用于横向扩展网络的 OSFP 接口笼。相反，我们只看到每个计算托盘引出 4 个 MPO 端口。这一设计实际上将除 DSP 之外的关键可插拔收发器组件（驱动器、TIA 等）提取出来，并放置在板载光模块（Midboard Optical Module (MBOM)）上，然后该模块通过平面网格阵列（LGA）插座连接到 PCB。两个 CX-9 共享一个板载光模块，后者随后通过短光纤连接到 MPO 面板。该板载光模块提供两个 MPO 端口，每个端口速率为 2x800G，总连接带宽达到 1.6T。

![](https://substackcdn.com/image/fetch/$s_!RazY!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3445fbb8-93c3-458e-8937-a67192ef8276_4000x3000.jpeg)

*左侧为 4 个 MPO 端口，而非 OSFP 接口笼。来源：英伟达，SemiAnalysis*

使用板载光模块将阻碍任何形式的可插拔收发器或 AEC 的使用，超级云服务商自然对这一想法表示“绝对拒绝”（CP-Hell No，此处暗讽对光电共封装 CPO 的抵触），并继续极力要求保留 OSFP 接口笼，以便能够继续使用可插拔模块。

需要指出的是，Kyber 设计的许多方面仍处于变动之中，在 Kyber 机架实际部署之前，仍可能出现多项设计变更。毕竟——从四个节点机箱（canister）的设计改为“两个计算托盘机箱 + 一个交换机刀片组”已经是一项巨大的改变。
