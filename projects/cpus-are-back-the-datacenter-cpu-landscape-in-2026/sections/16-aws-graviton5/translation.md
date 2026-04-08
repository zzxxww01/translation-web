https://substackcdn.com/image/fetch/$s_!wrPN!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faf081f84-4b44-4861-83b9-7467a1b74f89_2964x1485.png

Graviton CPU 发展史。来源：AWS

亚马逊云科技 (AWS) 是首家成功为云端开发并部署自研 CPU 的超大规模云厂商。得益于收购 Annapurna Labs 芯片设计团队，并采用 ARM 的 Neoverse 计算子系统 (CSS) 参考设计，AWS 如今能以更低价格提供 EC2 云实例。他们跳过采购英特尔至强 (Xeon) 处理器，直接交由台积电和外包半导体封装测试 (OSAT) 合作伙伴生产芯片；这种模式大幅改善了利润率结构，为降价提供了空间。

Graviton 的全面发力始于疫情繁荣期的 Graviton2 代产品。当时 AWS 抛出大幅折扣，吸引云客户将程序从 x86 架构迁移至 ARM 生态。尽管单核性能不及英特尔同期的 Cascade Lake，但 Graviton2 以极低的价格提供了 64 个 Neoverse N1 核心，性价比实现了大幅跃升。

2021 年底亮相的 Graviton3 预览版引入了多项变革，核心目标是将单核性能提升至具备竞争力的水平。AWS 转向了 ARM 的 Neoverse V1 架构；这是一款面积更大的 CPU 核心，浮点性能达到 N1 的两倍，而总核心数仍维持在 64 个。该芯片采用 10x7 核心网格网络 (CMN)，裸片上实际物理布图包含 65 个核心，预留 1 个核心以便在芯片分级 (Binning) 时屏蔽。AWS 还采用了小芯片 (Chiplet) 解耦设计：台积电 N5 工艺制造的中央计算裸片周围，环绕着 4 个 DDR5 内存小芯片和 2 个 PCIe5 I/O 小芯片，所有模块均通过英特尔的嵌入式多芯片互连桥接 (EMIB) 先进封装技术互连。受英特尔 Sapphire Rapids 延期影响，Graviton3 顺势成为首批部署 DDR5 和 PCIe5 的数据中心 CPU，比 AMD 和英特尔整整领先了一年，我们曾在此前文章中对此做过详细分析。

- 亚马逊 Graviton 3 采用小芯片与先进封装推动高性能 CPU 商品化 | 首款 PCIe 5.0 与 DDR5 服务器 CPU - Dylan Patel · 2021年12月2日

Graviton4 延续了规模扩张的步伐，采用升级版 Neoverse V2 核心，将核心数和内存通道数均提升 50%，分别达到 96 核与 12 通道，较上一代实现了 30% 至 45% 的性能提速。PCIe5 通道数从 32 条激增至三倍达到 96 条，大幅增强了与网络及存储设备的连接能力。Graviton4 还引入了对双路插槽配置的支持，进一步推高了单实例的核心上限。

https://substackcdn.com/image/fetch/$s_!P_3k!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcaa991f9-af71-4c1d-b519-c7aa45b5bfac_2732x1472.png

Graviton5 核心架构图。来源：AWS

自 2025 年 12 月推出预览版以来，Graviton5 的性能再次实现大幅跃升。它采用台积电 3nm 工艺，集成 1720 亿个晶体管，搭载 192 个 Neoverse V3 核心，较上一代翻倍。虽然每核二级缓存维持在 2MB，但共享三级缓存从 Graviton4 少得可怜的 36MB 增至 Graviton5 相当可观的 192MB。尽管核心数翻倍，内存带宽却仅提升了 57%（12 通道 DDR5-8800），这些额外增加的缓存正好充当了缓冲池。

正如我们在 Core Research 中所探讨的，Graviton5 的封装非常独特，这对供应链中的几家供应商产生了深远影响。

有趣的是，虽然 PCIe 通道升级到了 Gen6，但通道数量却从 Graviton4 的 96 条倒退回 Graviton5 的 64 条，显然是因为 AWS 在实际部署中通常用不满所有 PCIe 通道。这种成本优化在不影响性能的前提下，为亚马逊节省了大量 TCO。

Graviton5 采用了演进版的芯粒架构与互连技术，现在每 2 个核心共享同一个网格节点，整体呈 8x12 网格排列。虽然 AWS 这次并未展示具体的封装和裸片配置，但他们确认 Graviton5 确实采用了全新的封装策略，并且 CPU 核心网格被拆分到了多个计算裸片上。

https://substackcdn.com/image/fetch/$s_!0qb4!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9280a965-5af9-4c30-8ae0-b107f9248e48_2697x1149.png

Graviton 硅前设计。来源：AWS

在 CPU 使用方面，AWS 自豪地提到，他们已在内部持续集成/持续部署 (CI/CD) 设计流程中使用了数千颗 Graviton CPU，并运行电子设计自动化 (EDA) 工具来设计和验证未来的 Graviton、Trainium 和 Nitro 芯片，由此形成了一个“用 Graviton 设计 Graviton”的内部试用 (Dogfooding) 闭环。AWS 还宣布，其 Trainium3 加速器将采用 Graviton CPU 作为头节点，比例为 1 颗 CPU 搭配 4 颗 XPU。虽然初始版本搭载的是 Graviton4，但未来的 Trainium3 集群将由 Graviton5 驱动。
