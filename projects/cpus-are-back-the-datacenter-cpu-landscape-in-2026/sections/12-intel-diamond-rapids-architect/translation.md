https://substackcdn.com/image/fetch/$s_!ZcsD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F73fc256f-03cf-47b4-9ac5-a6240b0c9de0_2786x1606.png

Diamond Rapids 架构概览。来源：HEPiX，经由 @InstLatX64

乍看之下，Diamond Rapids 简直是 AMD 设计的翻版，计算裸片紧紧环绕着中央的 I/O 裸片。看来要在 Granite Rapids 的 10x19 规模之上继续扩展单一网格网络以增加核心数，难度实在太大。这意味着英特尔最终妥协，接受了多 NUMA 节点与多 L3缓存域的架构。四个核心构建块 (CBB) 裸片分布在两侧，将两个 I/O与内存集线器 (IMH) 裸片夹在中间。

在每个 CBB 内部，32 个基于 Intel 18A-P 工艺的双核模块 (DCM) 被混合键合到基础的 Intel 3-PT 裸片上，该基础裸片包含 L3缓存与本地网格互连。为了减少网格站点数量并降低网络流量，现在每个 DCM 中的两个核心共享一个 L2缓存。这种设计让人不禁联想到 2008 年的 Dunnington 架构。虽然这意味着 Diamond Rapids 总共拥有 256 个核心，但主流 SKU 似乎最多只会启用 192 个核心。受限于较低良率，更高核心数的版本大概率将预留给路线图之外的定制订单。

IMH 裸片包含 16 通道 DDR5 内存接口、支持 CXL3 的 PCIe6，以及英特尔数据路径加速器（QAT、DLB、IAA、DSA）。

有趣的是，裸片间互连似乎不再需要 EMIB (嵌入式多芯片互连桥接) 先进封装。封装基板上的长走线将每个 CBB 裸片与两个 IMH 裸片直接相连。这使得每个 CBB 都能直接访问完整的内存与 I/O 接口，无需再额外跳转至另一个 IMH。这也确保了任何 CBB 间的通信仅需 2 次跨裸片跳数。由于放弃了先进封装并将核心拆分到 4 个裸片上，我们预计跨 CBB 的延迟将明显恶化，与同一裸片内的延迟相比将出现巨大落差。

https://substackcdn.com/image/fetch/$s_!v88S!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe49ef13f-5a91-465a-af7e-3caabc9c651a_2942x1627.png

英特尔在其 P核 (性能核) 上移除了 SMT。来源：英特尔

延迟恶化固然棘手，但 Diamond Rapids 最致命的问题在于砍掉了 SMT。幽灵 (漏洞) 和熔断 (漏洞) 对英特尔的根本性打击远超 AMD，英特尔核心设计团队对此心有余悸，因此从 2024 年客户端 PC 的 Lion Cove 架构开始，他们在设计 P核 (性能核) 时便彻底抛弃了该功能。英特尔当时给出的合理化解释是，移除 SMT 功能所节省的芯片面积能带来更好的效率，代价则是牺牲原始吞吐量。这对 PC 设计来说并无大碍，因为它们同时集成了 E核 (能效核)，足以提振多线程性能。

然而，最大吞吐量对数据中心 CPU 至关重要，这让 Diamond Rapids 陷入了严重劣势。与当前 128 核、256 线程的 Granite Rapids 相比，我们预计主流的 192 核、192 线程 Diamond Rapids 速度仅能提升约 40%，这将导致英特尔在又一代产品中再次面临性能落后于 AMD 的窘境。

在产品开发后期，英特尔彻底砍掉了主流的 8 通道 Diamond Rapids-SP 平台，导致其出货量最大的核心市场至少要到 2028 年才会迎来换代产品。尽管这有助于精简英特尔臃肿的 SKU 产品线，但我们认为这是一步错棋，因为用于 AI 工具调用和上下文存储的通用计算，更多依赖于具备良好连接性的主流 CPU，而非追求极致单插槽性能的产品。
