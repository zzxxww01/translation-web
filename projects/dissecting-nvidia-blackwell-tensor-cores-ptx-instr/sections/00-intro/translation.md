### 微基准测试、tcgen05、2SM MMA、UMMA、TMA、LDGSTS、UBLKCP、理论极限性能 (Speed of Light, SoL)、分布式共享内存 (DSMEM)、GPC 核心屏蔽 (Floorsweeping)、SM 良率

作者：Kimbo Chen 与 Dylan Patel

2026年3月31日 · 付费文章

英伟达（NVIDIA）的数据中心 Blackwell GPU (SM100) 代表了这一代 GPU 微架构最重大的变革之一，但目前尚无详细的官方白皮书。时至今日，市面上仍没有任何针对数据中心 Blackwell 架构的公开微基准测试研究，能够专门针对 AI 负载并深入到 PTX 和 SASS 指令级别（如 UMMA 和 TMA）。

继发布深度长文 《英伟达 Tensor Core 演进史：从 Volta 到 Blackwell》 之后，SemiAnalysis 投入了数月的工程时间深度剖析 Blackwell 架构，测量底层 PTX 指令性能，确立了严格的实际性能上限，并将其与理论峰值进行对比。此举旨在揭示单元级和指令级的硬件吞吐量与延迟极限，从而为机器学习系统与内核开发提供极具价值的性能特征分析。我们重点关注深度学习负载配置，例如对主流深度学习库 FlashInfer 中使用的异步内存拷贝机制进行基准测试。

我们已在 此处 开源了 Blackwell 微架构级基准测试代码库。如果觉得有帮助，请给项目点个 Star。
