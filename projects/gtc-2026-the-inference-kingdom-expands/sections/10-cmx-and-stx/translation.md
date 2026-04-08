我们在上一篇关于 Rubin 的文章以及内存模型中，已经对英伟达的 CMX（即 ICMS 平台）进行了详尽的探讨。英伟达此次推出了 STX 参考存储机架架构。

#### CMX

CMX 是英伟达的上下文内存存储平台。CMX 解决了现代推理基础设施中日益凸显的瓶颈：即为了支持长上下文和智能体工作负载（agentic workloads），所需的 KV Cache 正在快速膨胀。

KV 缓存随输入序列长度和用户数量呈线性增长，也是影响预填充性能（首个 Token 生成时间）时的主要权衡因素。在大规模场景下，设备端 HBM 的容量往往捉襟见肘。主机 DRAM 作为额外的缓存层，虽然扩展了 HBM 之外的容量，但同样会触及单节点总容量、内存带宽以及网络带宽的极限。这就需要引入 NVMe 存储来进行额外的 KV 缓存卸载。

英伟达在今年 1 月的 CES 上，为推理内存层级引入了一个“全新”的中间存储层“G3.5 层”。G3.5 层 NVMe 介于 G3 层 DRAM 与 G4 层共享存储（同样为 NVMe，或 SATA/SAS SSD，或 HDD）之间。它此前被称为 ICMS（推理上下文内存存储），如今被重新命名为 CMX 平台，这本质上只是将通过 Bluefield 网卡连接至计算服务器的存储服务器进行了又一次品牌重塑。其与传统 NVMe 架构的唯一区别，仅仅是将 Connect-X 网卡替换为了 Bluefield 网卡。

https://substackcdn.com/image/fetch/$s_!wa5A!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb3a0a186-dbca-4e82-b477-f41c8148e2f3_1336x1258.jpeg

来源：2026年1月发布的英伟达ICMS原博客——于2026年3月16日更新并重新发布 https://developer.nvidia.com/blog/introducing-nvidia-bluefield-4-powered-inference-context-memory-storage-platform-for-the-next-frontier-of-ai/

#### STX

为了拓展 CMX 的应用范围，英伟达还推出了 STX。STX 是一种参考机架架构，采用英伟达基于 BF-4 的存储解决方案，作为 VR 计算机架的补充。该参考架构精确规定了特定集群所需的驱动器、Vera CPU、BF-4 DPU、CX-9 NIC 以及 Spectrum-X 交换机的确切数量。

https://substackcdn.com/image/fetch/$s_!p_Sv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fddb9b036-0027-4510-975b-9c707ca486c4_3000x4000.jpeg

STX 中的 BF-4。来源：英伟达，SemiAnalysis

VR NVL72 中的 BF-4 由单颗 Grace CPU 和单张 CX-9 NIC 组成。相比之下，STX 参考设计中的 BF-4 则包含单颗 Vera CPU、两张 CX-9 NIC 以及两个 SOCAMM 模块。每个 STX 机箱内置两个 BF-4 单元，共计两颗 Vera CPU、四张 CX-9 NIC 和四个 SOCAMM 模块。整个 STX 机架共包含 16 个机箱，即总共配备 32 颗 Vera CPU、64 张 CX-9 NIC 和 64 个 SOCAMM 模块。

https://substackcdn.com/image/fetch/$s_!N7af!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F31ef2de0-8f01-45f0-bea0-0fca1c8744ee_878x1030.png

STX 机架（左）。来源：英伟达，SemiAnalysis

在发布 STX 时，英伟达进行了典型的实力展示，宣布所有主流存储供应商均支持 STX，其中包括 AIC、Cloudian、DDN、Dell Technologies、Everpure、Hitachi Vantara、HPE、IBM、MinIO、NetApp、Nutanix、Supermicro、Quanta Cloud Technology (QCT)、VAST Data 和 WEKA。

综合来看，BlueField-4、CMX 和 STX 体现了英伟达致力于在存储层面对集群设计进行标准化的宏大布局。英伟达已经主导了计算和网络层，并正逐步向存储、软件以及基础设施运营层积极扩张。

接下来在付费内容中，我们将分享更多关于这一切将如何影响供应链的细节，包括 LPX 系统以及更新版 Kyber 机架的受益厂商。我们还将揭晓一款英伟达尚未公布的机架概念。
