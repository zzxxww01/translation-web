https://substackcdn.com/image/fetch/$s_!VLAl!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9634fe8d-37d6-4a92-87a5-1b371d9a6a4f_1920x1080.png

Microsoft Cobalt 200 服务器。来源：Microsoft

https://substackcdn.com/image/fetch/$s_!nG1L!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F80839a8f-c1e0-44fe-ab4e-310b4427ccd1_2608x1427.png

Cobalt 200 SoC 物理布图。来源：Microsoft

- Microsoft 基础设施——AI 与 CPU 定制芯片 Maia 100、Athena、Cobalt 100 - Dylan Patel 与 Myron Xie · 2023 年 11 月 15 日

继我们在前文探讨过的 2023 年微软首款 Cobalt 100 CPU 之后，Cobalt 200 于 2025 年底发布，并带来了多项升级。虽然核心数量增幅不大（从 128 个微增至 132 个），但与上一代的 Neoverse N2 相比，采用 Neoverse V3 设计的新核心性能大幅提升。每个核心配备高达 3MB 的超大 L2缓存。这些核心分布在两颗台积电 3nm 计算裸片上，通过标准的 ARM Neoverse CMN S3 网格网络连接，裸片之间则采用定制的高带宽互连技术。从架构图来看，每颗裸片采用 8x8 网格布局，配备 6 个 DDR5 通道以及 64 条支持 CXL 的 PCIe6 通道。每 2 个核心共享一个网格节点（mesh stop）。每颗裸片上物理集成了 72 个核心，出于良率考量，实际启用了 66 个。此外，网格网络中还分布着 192MB 的共享 L3缓存。

凭借这些升级，Cobalt 200 的运行速度较 Cobalt 100 提升了 50%。

与 Graviton5 不同，Cobalt 200 将仅用于 Azure 的通用 CPU 计算服务，不会被用作 AI 头节点。微软的 Maia 200 机架级系统转而部署了英特尔的 Granite Rapids CPU。
