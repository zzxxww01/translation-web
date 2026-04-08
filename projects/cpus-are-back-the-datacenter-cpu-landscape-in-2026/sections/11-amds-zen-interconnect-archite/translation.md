https://substackcdn.com/image/fetch/$s_!sC88!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7520d55a-ba5b-466e-9799-72fe683a1923_2860x1588.png

AMD 霄龙 (EPYC) CPU 演进历程。来源：AMD

https://substackcdn.com/image/fetch/$s_!Z99I!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc704a28b-2774-4428-9745-2cfdcf1f1573_2775x1508.png

英特尔抨击 AMD Naples 处理器。来源：英特尔

2017 年，AMD 携霄龙 (EPYC) Naples 7001 系列重返数据中心 CPU 市场，在业界引发轩然大波。英特尔嘲讽其设计是“四个胶水拼接的桌面级裸片”，且性能表现参差不齐。现实情况是，AMD 规模不大的设计团队必须精打细算。他们只承担得起流片一款裸片的成本，而这款裸片必须同时兼顾台式 PC、服务器，甚至还要在同一裸片上集成 10Gb 以太网以满足嵌入式需求。

https://substackcdn.com/image/fetch/$s_!NxBd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff6de7f59-7300-4154-aba5-836eae048878_3025x1693.png

AMD Zeppelin SoC（系统级芯片）架构。来源：AMD，ISSCC 2018

Naples 采用了四裸片 MCM（多芯片模块）设计，每个“Zeppelin”裸片包含 8 个核心，这使得 AMD 能够以 32 核规格超越英特尔的 28 核。每个裸片容纳 2 个核心复合体 (CCX)，内部的 4 个核心与 8MB L3 缓存通过交叉开关相连。裸片上的可扩展数据网络实现了 CCX 间的通信。封装内 Infinity Fabric (IFOP) 链路将每个裸片与封装内的其他 3 个裸片相连，而插槽间 Infinity Fabric (IFIS) 链路则用于实现双插槽设计。Infinity Fabric 实现了裸片间的一致性内存共享，该技术源自 AMD 早期的 HyperTransport 技术。

这种架构意味着没有统一的 L3缓存，且核心间延迟差异巨大。信号从一个裸片上 CCX 内的核心传输到另一个裸片上的核心，需要经过多次跳跃。一台典型的双插槽服务器最终会存在四个 NUMA 域。其通信层级包括：CCX 内部、CCX 之间、MCM 裸片之间、插槽之间。性能表现直接反映了这一点：渲染等高度可并行、极少需要核心间通信和内存访问的任务表现优异；而更依赖核心间通信、对内存和延迟敏感的任务则表现糟糕。此外，由于当时大多数软件并未针对 NUMA 架构进行优化，这让英特尔对 AMD“性能表现不稳定”的抨击显得确有其事。

### 霄龙 (EPYC) Rome 的集中式 I/O

https://substackcdn.com/image/fetch/$s_!qr8U!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F89034fe0-5221-40fe-9936-7e7e779456d6_2830x1602.png

Rome 与 Milan SoC 架构。来源：AMD

2019 年发布的 Rome 处理器彻底重构了裸片布局。AMD 借助异构解耦打造出 64 核产品，将当时仍停留在 28 核的英特尔远远甩在身后。八个 8 核核心计算裸片（CCD）环绕着一个中央 I/O 裸片，后者集成了内存和 PCIe 接口。CCD 升级至最新的台积电 N7 工艺，而 I/O 裸片则继续沿用格芯的 12nm 工艺。CCD 依然由两个 4 核 CCX 组成，但它们之间不再直接通信。相反，所有跨 CCX 的数据流量均通过 I/O 裸片路由，信号通过全局内存互连 (GMI) 链路在基板上传输。这意味着 Rome 在功能上表现为 16 个 4 核 NUMA 节点，但仅有两个 NUMA 域。

与上一代 Naples 类似，在 Rome 上启动的虚拟机（VM）必须限制在 4 核以内，以免因跨裸片通信造成性能损耗。2021 年发布的 Milan 处理器解决了这一问题。它转向了环形总线架构，将 CCX 规模扩大至 8 核，同时继续复用与 Rome 相同的 I/O 裸片。

https://substackcdn.com/image/fetch/$s_!yJpR!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F053b0db0-b10d-46be-ab7c-6826eeb1b607_2777x1154.png

AMD Turin-Dense 架构。来源：AMD

尽管最初计划采用先进封装，AMD 在接下来的两代产品中依然坚守了这一熟悉的架构设计。2022 年发布的 Genoa 处理器扩展至 12 个 CCD，而 2024 年发布的 Turin 处理器（如 128 核的霄龙 (EPYC) 9755）更是搭载了多达 16 个 CCD。这些 CCD 均围绕一个中央 I/O 裸片排列，该 I/O 裸片已升级支持 DDR5 和 PCIe 5.0 接口。

这种芯粒设计的核心优势在于，仅需一次裸片流片即可实现核心数量的可扩展性。AMD 只需设计单一 CCD，通过组合不同数量的 CCD，就能在整个 SKU 矩阵中提供全系列的核心数量配置。此外，每个 CCD 的裸片面积较小，这不仅有助于提升良率，还能在向新制程节点迁移时加快上市时间。这与网格（mesh）架构设计形成鲜明对比：后者采用接近光刻掩模版极限尺寸的大型裸片，且针对不同核心数量的较小网格配置，必须进行多次流片。在共享同一 I/O 裸片和插槽平台的前提下，AMD 还能灵活替换不同的 CCD 设计。例如，AMD 借助紧凑的 Zen 4c 核心打造了 Bergamo 处理器，并利用 Zen 5c 核心推出了 192 核的 Turin 衍生版本。

我们此前曾撰文分析过这种专为高效云计算打造的新型核心衍生版本。架构解耦还允许打造更小规模的版本，例如 EPYC 8004 Siena 处理器，该产品在 6 通道内存平台上仅使用了 4 个 Zen 4c CCD。

- Zen 4c：AMD 对超大规模 ARM 与英特尔 Atom 的有力回击 - Dylan Patel 与 Gerald Wong · 2023 年 6 月 5 日
