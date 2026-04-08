最大的制约因素之一（甚至可以说是首要瓶颈），就是台积电的N3逻辑晶圆产能。台积电N3系列于2023年开始出货并贡献营收，最初的需求主要由智能手机和PC驱动。N3起步并不顺利，首个版本“N3B”存在良率问题，且相对于密度提升而言成本过于昂贵。改进版N3E工艺推出后，N3系列的采用率才大幅提升。作为放宽设计规则的版本，N3E大幅减少了EUV层数，从而降低了成本。核心的智能手机和PC客户包括苹果、高通、联发科以及英特尔。其中，苹果的M3至M5 Mac芯片和A17至A19 iPhone处理器采用了N3系列工艺；高通将其用于骁龙8至尊版系列；联发科将其用于天玑智能手机SoC及部分汽车和PC芯片；英特尔则用于Lunar Lake和Arrow Lake客户端处理器。

https://substackcdn.com/image/fetch/$s_!lpP7!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbe6a510f-f4ee-4ee8-9267-22ccd427f99c_1860x1038.png

来源： SemiAnalysis Foundry Model

时至今日，N3制程的需求仍主要由消费电子驱动。到2026年，所有主流AI加速器系列都将向N3制程过渡；在向N2及更先进制程演进之前，AI将占据N3制程的绝大部分需求。

从下表可以看出，迈向2026年，整个行业正向台积电的N3系列靠拢，使其成为AI加速器领先的工艺制程节点。英伟达将从Blackwell架构的4NP过渡至Rubin架构的3NP。AMD通常更早采用新制程节点，其MI350X已采用N3，且MI400的AID和MID模块也将继续沿用N3（XCD模块则采用N2）。谷歌的TPU路线图从TPU v7开始全面转向N3E，且今年TPU的项目产量大幅攀升。AWS的Trainium3也将过渡至N3P。Meta的MTIA也遵循类似路径，不过其产量要低得多。

https://substackcdn.com/image/fetch/$s_!F7JO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0129d5ef-d8c3-46a8-a8f5-e69d5e4a84b5_1896x1180.png

来源： SemiAnalysis Accelerator Model

这种转变不仅限于XPU芯片。VR机架搭载的Vera CPU，其所有芯片均采用N3P工艺。此外还包括网络芯片，例如NVLink 6交换芯片，以及Tomahawk 6和Spectrum 6等横向扩展交换芯片。Rubin为每颗GPU提供了1.6T的横向扩展网络带宽，由此拉开了3nm 200G光DSP的应用序幕。

这种突然集中采用N3制程的趋势，叠加AI算力需求的持续增长，对N3制程晶圆产能造成了巨大的需求冲击。台积电对此猝不及防，其晶圆产能的扩张速度未能跟上激增的AI需求。这究竟是如何发生的？尽管史上最大规模的算力建设始于2022年底，但台积电的资本支出直到2025年才突破前期峰值。今年，台积电将大幅刷新去年的资本支出纪录，因为他们已经意识到，客户需求已远远超出其现有产能。

https://substackcdn.com/image/fetch/$s_!siy0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6fd015f7-6e9e-4a42-b5c9-2c359d65dd59_1424x742.png

来源： Company Filings

尽管台积电对其仅有的竞争对手英特尔和三星保持着明显的技术领先，但如果客户无法获得充足的晶圆供应来支撑自身业务，这种优势的意义就会大打折扣。产能瓶颈因此可能迫使客户寻求更多元的晶圆代工厂布局。例如，英特尔背后有美国政府撑腰，任何将订单外包给英特尔代工厂的举动，都能在美国政府那里赢得政治加分。与此同时，凭借近期拿下的一些设计订单，三星代工厂的发展势头也开始显现。首先，三星拿下了特斯拉的AI5和AI6等部分芯片项目，尽管这些项目采取了与台积电双线并行的代工策略。三星代工厂也已打入英伟达的数据中心供应链，我们在之前的晶圆代工模型中曾探讨过这一进展。
