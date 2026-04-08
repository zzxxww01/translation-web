英伟达对其 Kyber 机架形态进行了期待已久的更新，这是继 Oberon 之后产品线的最新成员，其原型曾在 GTC 2025 上首次预览。作为原型，该机架架构不断演进，我们注意到了一些变化。首先，每个计算刀片的密度提升，分别配备 4 个 Rubin Ultra GPU 和 2 个 Vera CPU。共有 2 个机箱（canister），每个机箱包含 18 个计算刀片，即总共 36 个计算刀片，单机架共计 144 个 GPU。最初的 Kyber 设计在单个计算刀片中配备 2 个 GPU 和 2 个 Vera CPU，共有 4 个机箱，每个机箱 18 个计算刀片。

以下细节基于 Rubin Kyber 原型，但 Rubin Ultra 版本将被重新设计。

https://substackcdn.com/image/fetch/$s_!57WO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6e91ff96-9d44-4d04-8a1f-eeb1575b235d_3000x4000.jpeg

来源：SemiAnalysis

与 GTC 2025 上的原型相比，每个交换机刀片的高度也增加了一倍，每个交换机刀片配备 6 个 NVLink 7 交换机，每个机架配备 12 个交换机刀片，每个 Kyber 机架总计 72 个 NVLink 7 交换机。GPU 通过 2 块 PCB 中板（即每个机箱 1 块中板）与交换机刀片实现全互联。

https://substackcdn.com/image/fetch/$s_!lj22!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4c5a1ad2-cfca-47a0-be02-f39b150e8df4_3000x4000.jpeg

Kyber 中板 PCB（GPU 侧）。来源：英伟达，SemiAnalysis

对于 Rubin Ultra NVL144 Kyber，正如我们多次告知客户的那样，向上扩展网络不会使用光电共封装，尽管其他分析师有传言称 Kyber 将引入用于向上扩展的光电共封装。然而，用于 NVLink 的光器件即将到来，并将逐步引入。向上扩展的光电共封装将首先用于 Rubin Ultra NVL 576 系统，以连接 8 个 Oberon 形态的机架，形成两层全互联网络。不过，机架内部的向上扩展网络仍将使用铜缆背板。这目前仍用于小批量生产或测试目的。

回到 Kyber 机架，每个 Rubin Ultra 逻辑 GPU 提供 14.4Tbit/s 的单向向上扩展带宽，每个 GPU 使用一个 80DP 连接器（使用 72 个 DP x 200Gbit/s 双向通道 = 14.4Tbit/s）连接至中板。在全互联网络中连接所有 144 个 GPU，需要 72 颗 NVLink 7.0 交换芯片，每颗芯片的单向聚合带宽为 28.8Tbit/s。

https://substackcdn.com/image/fetch/$s_!028i!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa6507cbc-367c-4f8e-9f8a-6fcbccf61aa3_1513x655.png

来源：SemiAnalysis

在下方的 Kyber 交换机刀片图片中，我们可以看到有两个独立的 PCB，每个 PCB 搭载 3 颗交换芯片。该交换机刀片应有 6 个 152DP 连接器，每 3 个连接器服务于一块中板。图片展示的是采用较低密度连接器的原型刀片，因此配备了 12 个连接器，而非量产版本预期的 6 个。

https://substackcdn.com/image/fetch/$s_!ET6V!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1bef24fc-b8ed-4652-a928-7abd4cf2d496_4000x3000.jpeg

来源：英伟达，SemiAnalysis

每颗 28.8T NVLink 交换芯片拥有 144 条 200G 通道（同时双向传输），这意味着每颗交换芯片有 24 条 200G 通道接入各个连接器。由于物理距离对 PCB 走线而言过长，因此采用铜质飞线电缆将每颗交换芯片连接至中板。这也是交换芯片远离中板的原因，为飞线电缆的布线提供空间。

https://substackcdn.com/image/fetch/$s_!-biX!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F376fc839-5860-4555-a18c-3b591ec13156_1582x1372.png

来源：SemiAnalysis Networking 模型

每颗 NVLink 交换芯片通过 Flyover 线缆连接到交换机刀片边缘的连接器（使用 144 个 DP x 200 Gbit/s 双向通道 = 28.8Tbit/s），这些连接器随后插入中板。英伟达正在研究使用共封装铜缆来进一步降低损耗，以防 NPC 方案不可行。据我们所知，英伟达正指示供应链全面转向共封装铜缆。

#### Rubin Ultra NVL288

尽管英伟达在 GTC 2026 上并未正式讨论，但供应链内部已经对 NVL288 概念进行了探索。该方案需要将两个 NVL144 Kyber 机架相邻放置，并使用机架间的铜背板将两者连接。一种可能性是所有 288 颗 GPU 实现全互联，但这将需要比当前 NVLink 7 交换芯片更高端口数的交换机，目前的 NVLink 7 交换芯片最多仅提供 144 个 200G 端口。

如果部署 Rubin Ultra NVL288，每颗 Rubin Ultra GPU 将拥有 14.4Tbit/s 单向的 scale-up 带宽，需要 144 个 DP 的线缆来连接 NVLink 7 交换芯片。每颗 GPU 72 个 DP 乘以 288 颗 GPU，意味着连接这个更大的集群并行规模域总共需要额外 20,736 个 DP。这涉及大量的线缆，因此它代表了线缆用量的上限。

28.8T NVLink 交换芯片的端口数限制了每颗交换芯片在保证跨机架连接的同时所能连接的 GPU 数量。要么必须使用更高端口数的交换机，要么该架构必须引入一定程度的超订，并可能采用类似 Dragonfly 的网络拓扑。这也将减少所需的铜缆 DP 数量。

https://substackcdn.com/image/fetch/$s_!YbDc!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faddf00bd-ed41-47b8-864e-35e96b6768c1_1613x1158.png

来源：SemiAnalysis

目前供应链中的所有证据均表明，NVSwitch 7 的带宽与 NVSwitch 6 相同，但坦率地说，这似乎有些不合逻辑。我们认为，NVSwitch 7 的带宽和端口数实际上是 NVSwitch 6 的 2 倍，从而能够实现全互联（all-to-all）。从系统角度来看，这在架构上是最合理的。

#### Rubin Ultra NVL576

为了将 scale-up 集群并行规模扩展至 144 颗 GPU 以上并跨越多个机架，必须引入光学器件，因为我们正在逼近铜缆互联所能支撑的最大计算密度极限。Rubin Ultra NVL576 现已列入路线图，该方案包含 8 个密度较低的 Oberon 机架。

https://substackcdn.com/image/fetch/$s_!kVKx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fee215fef-65ff-41ce-be3d-1a54c3af2334_2449x1037.png

来源：SemiAnalysis

机架间连接必须使用光学器件。尽管严格来说，目前尚未确认是采用可插拔光模块还是光电共封装（Co-Packaged Optics (CPO)），但采用 CPO 的可能性显然大得多。目前的 Blackwell NVL576 原型机“Polyphe”使用的是可插拔光模块。

我们此前已经 展示过针对 GB200 的 NVL576 概念方案，该方案使用可插拔光模块来互连第二层 NVLink 交换芯片。采用可插拔光模块会导致 BOM 成本激增，从 TCO 的角度来看，这使得构建交换全互联系统的方案变得不可行。然而，Rubin Ultra NVL576 很有可能会在 Feynman NVL 1,152 之前进行测试性的小批量生产，而在后者上，我们将看到 scale-up CPO 的实际规模化量产。

这对下游供应链的深远影响已在我们的机构研究报告中予以揭示，我们的研究深受各大超大规模云服务商、半导体公司及 AI 实验室的信赖，详情请联系 sales@semianalysis.com。

#### Feynman

虽然关于 Feynman 的已知信息不多，但主题演讲中的惊鸿一瞥足以让我们确认 Feynman 将令人振奋，它在单一平台上同时推进了三项重大技术创新：混合键合/SoIC、A16、光电共封装以及定制HBM。

虽然 Feynman 采用光电共封装已在路线图上，但问题在于采用的程度如何？机架内互连将基于铜缆还是光学器件？我们将在付费墙后展示可能的配置。Vera ETL256

随着 AI 工作负载在 GPU 计算之外需要更多的数据处理、预处理和编排，对 CPU 的需求正在上升。强化学习进一步推高了这一需求，因为 CPU 需要并行运行模拟、执行代码并验证输出。由于 GPU 的扩展速度快于 CPU，因此需要更大的 CPU 集群来保持 GPU 的充分利用，这使得 CPU 日益成为瓶颈。

Vera 独立机架直接解决了这一问题，通过将 256 个 CPU 容纳在单个机架中实现了前所未有的密度——这一壮举必须采用液冷技术。其底层逻辑与 NVL 机架的设计理念如出一辙：将计算组件进行高密度化封装，使得铜缆互连能够覆盖机架内的所有组件，从而消除在主干网络上使用光模块的需求。铜缆带来的成本节约足以抵消额外的散热开销。

https://substackcdn.com/image/fetch/$s_!KfPw!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc9e8a2b9-8417-41bc-aa32-1072b2e68fc0_3000x4000.jpeg

来源：SemiAnalysis

每个 Vera ETL 机架包含 32 个计算托盘（上下各 16 个），对称排列在中间的 4 个 1U MGX ETL 交换机托盘（基于 Spectrum-6）周围。这种对称布局是经过深思熟虑的：它最大限度地减少了计算托盘与主干之间的线缆长度差异，确保所有连接都在铜缆的覆盖范围内。在每个交换机托盘上，后置端口连接到该铜缆主干以实现机架内通信，而 32 个前置 OSFP 接口则为 POD 的其余部分提供光学连接。

机架内网络采用 Spectrum-X 多平面拓扑，将 200 Gb/s 通道分布于四台交换机中，在保持单一网络层级的同时实现完整的全互联。每个计算托盘容纳 8 个 Vera CPU，单个机架总计 256 个 CPU，所有 CPU 均通过单一扁平网络经以太网互联。

https://substackcdn.com/image/fetch/$s_!UMo8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F31febbf5-a0ec-4218-b2d0-e95e40704213_4000x3000.jpeg

来源：SemiAnalysis

https://substackcdn.com/image/fetch/$s_!At98!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F91ab19c1-1ceb-4b0b-a13e-6de00121eebd_1427x199.webp

来源：英伟达
