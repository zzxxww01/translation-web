https://substackcdn.com/image/fetch/$s_!6xHo!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F44e44d5f-8aeb-4974-9868-cd834fe74993_2560x1440.png

ARM 的 CSS 产品在定制化与开发成本之间取得平衡。来源：ARM

ARM 的核心 IP 授权业务在数据中心市场大获成功。几乎所有超大规模云厂商都在其定制 CPU 中采用了 ARM 的 Neoverse 计算子系统 (CSS) 设计。迄今为止，已有超过 10 亿个 Neoverse 核心部署于数据中心 CPU 和 DPU 中，12 家公司共签署了 21 份 CSS 授权协议。随着核心数量不断增加以及超大规模云厂商大举部署 ARM CPU，其数据中心版税营收实现同比翻番有余。ARM 预计，未来几年 CSS 将贡献超过 50% 的版税营收。阅读我们此前的文章，深入了解 ARM 的商业模式以及 CSS 如何攫取更多商业价值。

- 《Arm 的代价：Arm 如何榨取自身的真正价值》 - Dylan Patel、Myron Xie 及另外 2 人 · 2023 年 9 月 14 日

然而，ARM 将在 2026 年更进一步，直接提供完整的数据中心 CPU 设计，Meta 将成为其首发客户。这款代号为 Phoenix 的 CPU 将彻底改变 ARM 的商业模式。ARM 将借此转型为芯片供应商，包揽从核心到封装的整颗芯片设计。这意味着 ARM 势必与那些获得 Neoverse CSS 架构授权的客户展开直接竞争。作为软银控股的企业，ARM 还在为 OpenAI 设计定制 CPU，这也是星际之门 (Stargate) OpenAI 与软银合资项目的一部分。此外，Cloudflare 也有望成为 Phoenix 的客户。我们在 Core Research 中详细剖析了其销货成本 (COGS)、利润率与营收。

Phoenix 采用了标准的 Neoverse CSS 设计，其物理布图与微软 Cobalt 200 类似。128 个 Neoverse V3 核心通过 ARM 的核心网格网络 (CMN) 互联。这些核心分布在两颗半掩膜尺寸的裸片上，采用台积电 3nm 制程节点制造。在内存与 I/O 方面，Phoenix 配备 12 通道 DDR5（速率为 8400 MT/s）以及 96 条 PCIe 6.0 通道。其能效表现极具竞争力，CPU 的可配置热设计功耗 (TDP) 介于 250W 至 350W 之间。

借此，Meta 如今也拥有了自家的 ARM CPU，足以与微软、谷歌和 AWS (亚马逊云科技) 旗鼓相当。作为 AI 头节点，Phoenix 能够通过加速器支持套件 (Accelerator Enablement Kit)，经由 PCIe 6.0 为外接的 XPU 提供一致性共享内存。下文我们将为订阅用户详细解析下一代 ARM Venom CPU 设计，其中包括一项重大的内存架构变更。
