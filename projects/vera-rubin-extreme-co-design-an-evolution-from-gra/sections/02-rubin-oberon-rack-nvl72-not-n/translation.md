自英伟达（NVIDIA）在 2024 年 GTC 大会上发布 GB200 以来，AI 服务器系统的概念已从机箱（Chassis）转向机柜级（Rack-scale）系统。在我们的 [GB200 文章](https://newsletter.semianalysis.com/p/gb200-hardware-architecture-and-component) 中，我们讨论了英伟达 AI 服务器形态从 HGX（每节点 8 颗 GPU）到 Oberon（NVL72 机柜级）的演进。虽然 HGX 形态依然存在，但英伟达 Blackwell 架构 GPU 的大部分都集成在 Oberon 形态中。Rubin 同样将提供 HGX 和 Oberon 两种系统。

Blackwell 与 Rubin Oberon 架构之间的关键区别在于提供给客户的 SKU 数量。由于 Blackwell Oberon 是首个大规模部署的机柜级解决方案，其 GB200 NVL72 SKU 的机架功率密度超过了 100kW，许多数据中心尚未准备好支持单机架 100kW 以上的基础设施。因此，英伟达提供了两种 Blackwell Oberon SKU：GB200 NVL72 和 GB200 NVL36x2。后者是为那些基础设施尚未准备好处理单高密度机架散热需求的客户提供的低密度 SKU。我们已在 [GB200 文章](https://newsletter.semianalysis.com/p/gb200-hardware-architecture-and-component). 中讨论了这两种形态的区别。

与 Blackwell 不同，Rubin 仅提供 VR NVL72 这一种 SKU。其配置与 GB200/GB300 NVL72 非常相似。每套 VR NVL72 系统包含：

- 72 个 Rubin GPU 封装

- 36 颗 Vera CPU

- 36 颗 NVLink 6 交换机 ASIC

https://substackcdn.com/image/fetch/$s_!xB_f!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F42660b70-c898-4e6b-a117-7490baf5ae4c_733x1702.png

来源： Nvidia VR NVL72 BoM and Power Budget Model

顺带一提，VR NVL72 最初被称为 VR NVL144，因为根据 GTC 2025 上的 黄氏数学（Jensen math），系统中的 GPU 数量被定义为系统内 GPU 计算裸片（compute die）的数量（每个封装包含 2 个计算裸片，每个 Oberon 机架包含 72 个 Rubin 封装 = 144 个计算裸片）。在 12 月下旬，命名被改回 VR NVL72，以代表系统中的 72 个 Rubin GPU 封装。这恰好发生在 CES 2026 之前，届时该命名被正式确认为 VR NVL72。

### CPX 形态规格

https://substackcdn.com/image/fetch/$s_!BH0r!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F30fd28ad-beb1-46a4-844e-bab6c4d4b216_1507x1697.png

来源： Nvidia VR NVL72 BoM and Power Budget Model

尽管英伟达（NVIDIA）最初计划将 CPX 加速器集成到 VR NVL72 机柜中，但目前的进展表明，CPX 将仅作为独立机柜提供，正如我们在 介绍英伟达的文章 [CPX](https://newsletter.semianalysis.com/p/another-giant-leap-the-rubin-cpx-specialized-accelerator-rack) 中所详述的那样。回顾我们在前篇 CPX 文章中提到的 Rubin 时代系统规划，英伟达最初考虑了三种 VR NVL72 配置：

- VR NVL72（常规版）： 不带 CPX 的标准 Oberon VR NVL72

- VR NVL72 CPX（集成版）： Rubin GPU 和 Rubin CPX 位于同一个算力托盘内

- VR NVL72 CPX（双机架版）： Rubin CPX 部署在与 VR NVL72 机架并列的独立机架中

独立/专用机架的方向实质性地改变了部署的权衡逻辑。双机架方案允许超大规模云厂商（Hyperscalers）独立扩展 Prefill 和 Decode 环节（Decode Loop）的容量，优化数据中心功耗包络，并降低与紧耦合托盘相比的系统级故障域。更重要的是，它正式确立了推理 Prefill（受算力限制）与 Decode 环节（受带宽限制）之间的架构解耦。

Rubin CPX 最初被设计为一种基于 GDDR7 的加速器，专门针对 Prefill 进行了优化，这基于三个关键考量：

- Prefill 主要受算力（FLOPs）限制，而非带宽限制，这使得 HBM 并非不可或缺。

- HBM 增加的带宽在 Prefill 环节中存在结构性的利用不足。

- GDDR7 提供了显著更低的单位容量成本（cost per GB），且无需 2.5D 封装。

然而，英伟达（NVIDIA）开始探索用于 Prefill 的配备 HBM 的变体，无论是通过修改 CPX 配置，还是通过专门用于 Prefill 的低内存规格（如使用 HBM3E）的 Rubin 部署，正如我们在去年12月初的加速器与HBM模型中指出的那样。

我们还认为，这种转变在很大程度上是由不断变化的内存经济效益驱动的。常规 DRAM 价格已大幅上涨： 随着 DDR 价格上涨，HBM 的相对溢价正在缩小，因为其定价在长期合同中更为固定，从而缩小了基于 GDDR 的 CPX 与低规格 HBM 配置之间的成本差距，因此消除了 GDDR 相对于其性能表现所具备的许多成本优势。虽然与 Decode 环节相比，内存带宽对于 Prefill 并不那么重要，但它仍然是必要的。
