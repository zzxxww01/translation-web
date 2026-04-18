微软详细介绍了其Maia 200 AI加速器。这篇论文与其说是一篇研究论文，不如说更像一份白皮书，仅包含一张图片和一份将其与Maia 100进行比较的规格表。考虑到Maia 200的许多性能宣称（例如其每平方毫米浮点运算性能（FLOPS/mm²）和每瓦浮点运算性能（FLOPS/W））本身存疑，这种做法倒也合乎情理。

Maia 100 设计于 GPT 时代之前，而 Maia 200 则是为当前模型时代、特别是为推理任务而设计的。今年早些时候，基于 Maia 200 芯片的计算节点已在 Azure 云平台上普遍可用。

https://substackcdn.com/image/fetch/$s_!3VIK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0c381cad-9332-483a-9fd7-8de08cd7d90a_2880x1620.jpeg

微软 Maia 200 规格总结。来源：微软，ISSCC 2026

Maia 200 是光罩尺寸单芯片设计的最后坚守者。所有配备高带宽内存（HBM）的主要训练和推理加速器都已转向多芯片设计，每个封装内包含 2、4 甚至 8 个计算裸片。芯片的每一平方毫米都为实现单一目标而做了极致优化。与英伟达或 AMD 的 GPU 不同，它没有为媒体或向量运算保留的遗留硬件。微软在台积电（TSMC）的 N3P 工艺上将光罩尺寸单芯片方法推向了极限，集成了超过 10 PFLOPs 的 FP4 算力、6 个 HBM3E 堆栈以及 28 条 400 Gb/s 全双工 D2D 链路。

https://substackcdn.com/image/fetch/$s_!oV7g!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F98820b64-6a10-4132-b24a-a2122f7417ad_2880x1620.jpeg

微软 Maia 200 封装横截面图。来源：微软，ISSCC 2026

在封装层面，Maia 200 非常标准，模仿了 H100 的设计，采用一个 CoWoS-S 中介层来承载 1 个主裸片和 6 个 HBM3E 堆栈。

https://substackcdn.com/image/fetch/$s_!1q24!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4949a336-f267-4f4c-b813-1f6af0d7f629_506x541.jpeg

微软 Maia 200 裸片布局图。来源：微软，ISSCC 2026

芯片的长边各覆盖了3个HBM3E物理层接口（PHY），而短边则各有14条通道，共同组成28条速率为400 Gb/s的裸片到裸片（D2D）互连接口。芯片中央集成了272 MB的SRAM，其中包括80 MB的TSRAM（作为L1缓存）和192 MB的CSRAM（作为L2缓存）。

https://substackcdn.com/image/fetch/$s_!Wj4l!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F62240549-cf4a-4472-8294-7b7b2bca21fa_2880x1620.jpeg

微软 Maia 200 纵向扩展网络与输入/输出接口。来源：微软，ISSCC 2026

Maia 200 配备两种不同类型的互连接口：一种是用于连接同一节点内其他芯片的固定链路，另一种是用于连接芯片与交换机的交换链路。具体而言，21条链路被配置为固定链路，分别连接至节点内的其他芯片（例如，连接到其他三个芯片，各使用7条）；剩余的7条链路则被配置为交换链路，用于连接机架内的四个交换机之一。

我们将为机构订阅用户发布一份关于 Maia 200 的深度分析报告，涵盖其微架构和网络拓扑结构。
