https://substackcdn.com/image/fetch/$s_!iUhJ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F05f65e22-af68-4a66-8471-20eb13de627b_3005x1594.png

Axion C4A 晶圆与封装。来源：Hajime Oguri, Google Cloud Next ’24

https://substackcdn.com/image/fetch/$s_!8nFB!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7cca6b00-0503-42dd-b09d-15a595e864d9_1844x1814.png

Axion N4A CPU。来源：Google

Axion 产品线于 2024 年发布，并于 2025 年全面上市，标志着谷歌正式为其 GCP (谷歌云平台) 云服务引入定制 CPU 芯片。Axion C4A 实例采用大型单片 5nm 裸片，在标准网格网络上搭载多达 72 个 Neoverse V2 核心，并配备 8 通道 DDR5 与 PCIe5 连接。根据 Google Cloud Next 2024 大会展示的 Axion 晶圆特写图，该裸片似乎以 9x9 网格布局光刻了 81 个核心，预留了 9 个核心供屏蔽以保障良率。因此我们笃定，2025 年底开启预览的 96 核 C4A 裸金属实例必然采用了全新设计的 3nm 裸片。

针对更具成本效益的横向扩展 Web 与微服务，谷歌目前已推出 Axion N4A 实例预览版。该实例在尺寸大幅缩小的裸片上搭载了 64 个性能较低的 Neoverse N3 核心，为 2026 年全年的大规模产能爬坡铺平了道路。Axion N4A 芯片由谷歌基于台积电 3nm 工艺全定制设计。随着谷歌将内部基础设施向 ARM 架构迁移，Gmail、YouTube、Google Play 等服务将在 Axion 与原有的 x86 架构上并行运行。未来，谷歌将专门设计 Axion CPU，用作驱动 Gemini 的 TPU (张量处理器) 集群的头节点。
