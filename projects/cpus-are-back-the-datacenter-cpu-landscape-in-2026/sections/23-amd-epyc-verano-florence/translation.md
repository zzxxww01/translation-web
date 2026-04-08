https://substackcdn.com/image/fetch/$s_!vm-p!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa49ab8ae-a31f-4ca0-b522-8bfa4c30a0fc_2671x1489.png

AMD 机架级 AI 基础设施路线图。来源：AMD

AMD 下一代 MI500 AI 机架将于 2027 年发布，并搭载全新的霄龙 (EPYC) Verano CPU，距 Venice 问世仅相隔一年。据我们了解，Zen 7 CPU 内核架构赶不上 Verano 的发布节奏，因为内核团队的研发周期约为两年。因此我们认为，Verano 将是 Venice 的变体，继续沿用 Zen 6 内核，且极有可能保持相同的 256 核配置。Verano 的不同之处应在于采用全新的 3nm I/O 裸片，支持 PCIe Gen7 和 200G 以太网 SerDes (串行器/解串器)。这能大幅提升连接 MI500 GPU 的 Infinity Fabric 速度。这也将支持 UALoE。

代号为 Florence 的真正下一代 Zen 7 霄龙 (EPYC) 预计将于 2028 年问世，采用台积电 A16 工艺并支持背面供电。或者，如果不使用背面供电，AMD 也可以等待台积电 A14 工艺成熟，将其用于 2029 年的产品。我们预计其核心数量将增加至 320 个左右。

https://substackcdn.com/image/fetch/$s_!otrQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe4a3cd7a-72fe-4414-bcf7-9a1ac1d827f2_3111x1740.png

AMD Zen CPU 内核路线图。来源：AMD

在内核微架构方面，AMD 首席技术官 Mark Papermaster 证实，Zen7 引入了全新的专用矩阵乘法引擎以处理本地 AI 计算。该引擎在 x86 咨询小组中被称为 ACE。这与英特尔在 2023 年随 Sapphire Rapids 引入的 AMX (高级矩阵扩展) 引擎极为相似。Zen7 还采用了 AVX10。作为 AVX-512 的演进版本，它在更小位宽下提供了更多功能与更高的指令灵活性。FRED (灵活返回与事件交付) 中的全新中断模型以及 ChkTag 内存标记技术也将在 Zen7 上首度亮相。所有这些特性都将率先在英特尔 Diamond Rapids 上推出。此外，Diamond Rapids 还支持 APX (高级性能扩展)。这种指令集扩展增加了对更多寄存器的访问权限，并提升了通用计算性能。

Zen7 似乎并未包含该特性。
