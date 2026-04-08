# AI芯片大短缺

**作者**: Ivan Chiam, Myron Xie, Ray Wang
**日期**: Mar 12, 2026

*台积电N3晶圆短缺、存储受限、数据中心瓶颈与供应链之战的赢家*

## 引言

### 台积电N3（3纳米制程工艺）制程晶圆短缺、存储产能限制、数据中心瓶颈与供应链之争的赢家

作者：[Ivan Chiam](https://substack.com/@ivanchiam)、[Myron Xie](https://substack.com/@myronxie)、[Ray Wang](https://substack.com/@rwang07semis)等3人

2026年3月12日

## SemiAnalysis x Fluidstack 黑客松

今年GTC开幕前夕，我们将于15日（周日）与Fluidstack联合举办一场黑客松，诚邀您的参与！

**在此报名：** [https://luma.com/SAxFSHack](https://luma.com/SAxFSHack)

![](https://substackcdn.com/image/fetch/$s_!xoJj!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbc74983e-edab-47a0-801c-fffe0839a20e_4000x4000.png)

## 算力短缺

token需求正在飙升，对AI算力的需求持续加速。模型能力的提升与智能体工作流的迅速涌现相叠加，推动了用户采用率和总token需求的激增。在智能体编程平台Claude Code被广泛采用的推动下，仅在2月份单月，Anthropic就新增了惊人的60亿美元ARR（年度经常性收入）；如果Anthropic拥有更多算力，这一数字还会更高。尽管过去几年AI基础设施建设规模庞大，但可用算力依然稀缺。按需GPU的价格持续上涨，甚至连已经落后近两代的Hopper系列芯片也不例外。

就我们自身的经历而言，我们联系了所认识的每一家新兴云厂商，询问是否有可用的小型集群，但所有资源都早已被牢牢锁定。这种紧张的供应环境，解释了为何超大规模云服务商的资本支出计划会出现大幅重置。市场一致预期已全面大幅上调，其中谷歌是最极端的例子：受数据中心和服务器支出的主要驱动，其2026年的资本支出预期较此前翻了约一倍。

![](https://substackcdn.com/image/fetch/$s_!InA2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F685652e0-3bff-448a-a33f-f1f16feb6b61_1844x1038.png)

来源： Company Earnings, Bloomberg

这是极其庞大的支出规模，如果条件允许，超大规模云厂商甚至愿意投入更多资金，但他们受制于一个关键因素：芯片供应。现有的先进逻辑与存储芯片的晶圆厂产能，根本不足以支撑当前的算力部署节奏。尽管在ChatGPT发布后的时代，行业一直饱受CoWoS封装和数据中心电力等各种瓶颈的困扰，但如今我们已确凿无疑地步入了芯片短缺阶段。

![](https://substackcdn.com/image/fetch/$s_!f-w8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdb3eb393-a811-44e0-b4f3-7c5ebf1b7f87_2030x1076.png)

来源： SemiAnalysis Accelerator Model

## 台积电 N3 产能短缺

最大的制约因素之一（甚至可以说是首要瓶颈），就是台积电的N3逻辑晶圆产能。台积电N3系列于2023年开始出货并贡献营收，最初的需求主要由智能手机和PC驱动。N3起步并不顺利，首个版本“N3B”存在良率问题，且相对于密度提升而言成本过于昂贵。改进版N3E工艺推出后，N3系列的采用率才大幅提升。作为放宽设计规则的版本，N3E大幅减少了EUV层数，从而降低了成本。核心的智能手机和PC客户包括苹果、高通、联发科以及英特尔。其中，苹果的M3至M5 Mac芯片和A17至A19 iPhone处理器采用了N3系列工艺；高通将其用于骁龙8至尊版系列；联发科将其用于天玑智能手机SoC及部分汽车和PC芯片；英特尔则用于Lunar Lake和Arrow Lake客户端处理器。

![](https://substackcdn.com/image/fetch/$s_!lpP7!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbe6a510f-f4ee-4ee8-9267-22ccd427f99c_1860x1038.png)

来源： SemiAnalysis Foundry Model

时至今日，N3制程的需求仍主要由消费电子驱动。到2026年，所有主流AI加速器系列都将向N3制程过渡；在向N2及更先进制程演进之前，AI将占据N3制程的绝大部分需求。

从下表可以看出，迈向2026年，整个行业正向台积电的N3系列靠拢，使其成为AI加速器领先的工艺制程节点。英伟达将从Blackwell架构的4NP过渡至Rubin架构的3NP。AMD通常更早采用新制程节点，其MI350X已采用N3，且MI400的AID和MID模块也将继续沿用N3（XCD模块则采用N2）。谷歌的TPU路线图从TPU v7开始全面转向N3E，且今年TPU的项目产量大幅攀升。AWS的Trainium3也将过渡至N3P。Meta的MTIA也遵循类似路径，不过其产量要低得多。

![](https://substackcdn.com/image/fetch/$s_!F7JO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0129d5ef-d8c3-46a8-a8f5-e69d5e4a84b5_1896x1180.png)

来源： SemiAnalysis Accelerator Model

这种转变不仅限于XPU芯片。VR机架搭载的Vera CPU，其所有芯片均采用N3P工艺。此外还包括网络芯片，例如NVLink 6交换芯片，以及Tomahawk 6和Spectrum 6等横向扩展交换芯片。Rubin为每颗GPU提供了1.6T的横向扩展网络带宽，由此拉开了3nm 200G光DSP的应用序幕。

这种突然集中采用N3制程的趋势，叠加AI算力需求的持续增长，对N3制程晶圆产能造成了巨大的需求冲击。台积电对此猝不及防，其晶圆产能的扩张速度未能跟上激增的AI需求。这究竟是如何发生的？尽管史上最大规模的算力建设始于2022年底，但台积电的资本支出直到2025年才突破前期峰值。今年，台积电将大幅刷新去年的资本支出纪录，因为他们已经意识到，客户需求已远远超出其现有产能。

![](https://substackcdn.com/image/fetch/$s_!siy0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6fd015f7-6e9e-4a42-b5c9-2c359d65dd59_1424x742.png)

来源： Company Filings

尽管台积电对其仅有的竞争对手英特尔和三星保持着明显的技术领先，但如果客户无法获得充足的晶圆供应来支撑自身业务，这种优势的意义就会大打折扣。产能瓶颈因此可能迫使客户寻求更多元的晶圆代工厂布局。例如，英特尔背后有美国政府撑腰，任何将订单外包给英特尔代工厂的举动，都能在美国政府那里赢得政治加分。与此同时，凭借近期拿下的一些设计订单，三星代工厂的发展势头也开始显现。首先，三星拿下了特斯拉的AI5和AI6等部分芯片项目，尽管这些项目采取了与台积电双线并行的代工策略。三星代工厂也已打入英伟达的数据中心供应链，我们在之前的晶圆代工模型中曾探讨过这一进展。

## 数据看 N3

现在，让我们来看看产能究竟有多紧张。贯穿今年全年，N3制程加速器的晶圆需求将迅猛攀升。核心驱动力在于英伟达的Rubin产能爬坡，目前该公司正从基于4NP的Blackwell架构向基于N3P的Rubin架构过渡。然而，得益于更高的平台与供应链成熟度，今年Blackwell的出货量仍将高于Rubin。谷歌与博通的TPU在导入N3制程的进度上领先于英伟达和亚马逊，其TPUv7芯片在2025年便已投入量产。这一强劲势头在今年得以延续，在谷歌内部需求以及Anthropic等外部需求的共同推动下，TPU的出货量迎来了激增。与此同时，向下一代TPUv8变体的过渡也将启动，该系列将继续采用N3制程节点。 另一个关键变量是，基于N3P制程的Trainium3将从2026年初开始晶圆投片，以迎接下半年产能的大幅爬坡。

因此，AI相关需求（包括加速器、主机CPU和网络设备的N3需求）最终占据了今年N3制程略低于60%的产量。剩余的40%主要用于智能手机和CPU。这些需求完全吃透了N3的全部产能，台积电几乎无力再扩充更多产能。到了2027年，即使台积电增加N3产能，这种紧缺状况也会变得更加严峻。据我们测算，2027年AI需求将占到N3晶圆产量的86%，几乎完全挤占了智能手机和CPU的晶圆份额。这种转变部分源于智能手机产品路线图按计划向N2制程迁移，但N3产能紧缺无疑也加速了这一进程。至于继续留在N3制程的产品线，其需求难以得到完全满足。

![](https://substackcdn.com/image/fetch/$s_!bywn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5b707af9-3845-4437-9c68-561f36658df4_1868x1104.png)

来源： SemiAnalysis Foundry Model, SemiAnalysis Accelerator Model

![](https://substackcdn.com/image/fetch/$s_!tcQC!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0183a621-85de-4e9b-b829-6e6d90fddaa6_2092x1186.png)

来源： SemiAnalysis Accelerator Model

在客户争夺有限的N3产能时，台积电最终扮演着“造王者”的角色。在2026年的产能分配上，AI基础设施客户的优先级明显高于消费电子。AI加速器设计通常拥有更大的裸片尺寸和更复杂的封装需求，从而带来更高的平均售价。更重要的是，AI驱动的需求无疑是目前台积电增长的最大引擎。终端客户愿意不惜一切代价部署更多算力。各大AI实验室在算力上的坚定投入带来了长达数年的需求可见度，为这一趋势提供了坚实支撑。

这与目前已高度饱和的移动和客户端市场形成鲜明对比，后者无论在出货量还是单机半导体价值量增长方面，所能提供的空间都已十分有限。这使得AI加速器客户在锁定先进制程产能时具备了相对优势。其他细分市场中无法锁定充足N3制程产能的客户，可能将被迫延长现有产品周期，或者直接迁移至N2平台。

## 台积电供应现状

在需求远超供给的背景下，台积电正在扩充产能，并将现有产线逼至极限，竭力从其铭牌产能中榨取每一片晶圆。因此，预计到2026年下半年，实际N3制程稼动率将突破100%。此外，台积电还将特定的工艺层转移至其他晶圆厂，以尽可能释放增量的N3制程产能。

为什么台积电不能直接增加N3制程的晶圆投片量？与存储器供应商一样，台积电也受限于现有的无尘室空间。必须先建出额外的可用厂房面积，才能进行设备装机并实现新产能上线。在未来两年内，台积电将无法增加足够的产能来完全满足需求。因此，在此期间，如果某些公司想要获得更多的晶圆产能分配，就必须有其他公司放弃其现有宝贵的产能分配，而这极有可能发生。

![](https://substackcdn.com/image/fetch/$s_!u-E7!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F450c33c0-062f-486e-aff1-1db8c0dc68b4_2020x1088.png)

来源： SemiAnalysis Foundry Model

![](https://substackcdn.com/image/fetch/$s_!fzVm!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F12d5f30f-d1ba-4037-aa57-763d58a3bde1_2571x1505.png)

来源： SemiAnalysis Foundry Model

## Smartphones as the Front-End Release Valve?

今年，智能手机是N3晶圆需求的第二大驱动力。事实上，该领域最有可能出现需求疲软，进而为XPU晶圆腾出产能。目前，苹果以及联发科和高通等智能手机客户，均基于今年智能手机出货量仅有低个位数增长的预期，向供应链下达了订单。

然而，不断上涨的存储器价格正传导至手机BOM（物料清单）成本，并最终推高消费端的平均售价（ASP）。这很可能会抑制消费者需求。已有迹象表明，智能手机的需求预期将被下调，同比降幅达低两位数。随着智能手机需求走弱，相关的晶圆需求也将随之减少，从而为XPU逻辑芯片腾出更多产能。

据此推算出货量，若将2026年智能手机N3晶圆总投片量的5%（即43.7万片晶圆的5%）转配给AI加速器，即可额外生产约10万颗Rubin GPU，或约30万颗TPU（张量处理器，Tensor Processing Unit）v7。在更极端的假设下，若将2026年智能手机N3晶圆总投片量的25%转配给AI加速器，台积电（TSMC）就能额外生产约70万颗Rubin GPU，或约150万颗TPU v7。然而，对于AI加速器芯片而言，逻辑部分只是其中一环，存储器供应和先进封装同样不可或缺。

![](https://substackcdn.com/image/fetch/$s_!86sv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb40dd801-4946-431b-bcd4-b99550108971_1376x320.png)

来源： SemiAnalysis Foundry Model

![](https://substackcdn.com/image/fetch/$s_!N61c!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6f4f58ae-8668-4da8-8143-b528a369cd1a_2018x1084.png)

来源： SemiAnalysis Estimates

- [存储狂热：四十年一遇的短缺如何助推存储繁荣](https://newsletter.semianalysis.com/p/memory-mania-how-a-once-in-four-decades) - Dylan Patel、Ray Wang 等 3 人 · 2月6日

## Memory The Next Biggest Constraint

[全球存储芯片短缺](https://newsletter.semianalysis.com/p/memory-mania-how-a-once-in-four-decades)短期内不太可能缓解。随着芯片供应商和超大规模云厂商竞相锁定DRAM供应以满足加速器生产需求，存储芯片已成为下一个主战场。尽管DRAM晶圆总产能持续增长，但大部分新增产能正被HBM吞噬，实质上挤压了通用DRAM的产能。

按每比特晶圆消耗量计算，HBM消耗的晶圆产能约为标准型DRAM的三倍。随着今年业界向HBM4过渡，这一差距可能会扩大至近四倍，而明年进入HBM4E阶段时还会进一步拉大。因此，HBM的增量扩张从标准型DRAM手中抽离了不成比例的DRAM晶圆产能份额，进一步加剧了存储市场结构性紧缺的局面。

![](https://substackcdn.com/image/fetch/$s_!3wRG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe3edd595-4b9d-4d67-8da2-ee97a6f6e053_2136x1126.png)

来源： SemiAnalysis Memory Model

![](https://substackcdn.com/image/fetch/$s_!3eWl!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faab0bd24-a53a-4e2a-a0ea-7daa0057e0f8_2004x1094.png)

来源： SemiAnalysis Memory Model

随着单颗加速器搭载的HBM容量急剧上升，这种压力正被进一步放大。HBM的比特出货量正迎来陡峭的增长拐点，这主要归因于单设备内存容量的提升，而非仅仅依赖于设备出货量的增长。对英伟达（NVIDIA）而言，从Blackwell向Blackwell Ultra和Rubin的迭代，使其HBM容量增加了50%，而Rubin Ultra更是将推动容量进一步实现约4倍的增长。超大规模云厂商的定制芯片（ASIC）也在经历类似的跨越式升级，TPU v8AX和Trainium3均从上一代的8层（8-Hi）堆叠升级至12层（12-Hi）堆叠，而AMD从MI350到MI400的内存容量也实现了50%的增长。

![](https://substackcdn.com/image/fetch/$s_!vlh2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F17bae206-924e-4e87-a7f1-c91a3f257c9e_2098x1130.png)

来源： SemiAnalysis Accelerator Model

另一个加剧供应紧张的因素是业界对更高HBM引脚速度的追求。诸如英伟达（NVIDIA）等客户正将HBM4的引脚速度目标设定在11 Gb/s左右，这一要求对于存储供应商而言，仍难以在可接受的良率水平下达成。尽管SK海力士和三星在满足这些规格方面取得了较好的进展，但美光（Micron）在HBM4上却处于落后态势，我们早在1月份的Rubin文章以及加速器与HBM模型中就探讨过这一动态。随着客户要求更高的引脚速度，而供应商难以实现规模化交付，这种性能要求的不断升级进一步限制了HBM的有效供应。

![](https://substackcdn.com/image/fetch/$s_!nRle!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5c55d753-0c40-4c17-83f1-e3d2063f7cfc_2134x1226.png)

来源： SemiAnalysis Memory Model

除了HBM，服务器DRAM的需求也在走强。在英伟达的下一代平台中，AI服务器系统内存将出现实质性增长，VR NVL72机架搭载的DDR容量将达到原来的3倍，即每个Vera CPU配备1,536 GB，而此前的Grace CPU仅为512 GB。随着老化的云和企业服务器存量设备进入持续多年的替换周期，我们预计常规DRAM的比特需求也将在2026年迎来向上拐点。与此同时，AI工作负载，特别是数据暂存、任务编排和强化学习，正在拉动CPU需求，并将在未来逐步提升CPU与GPU的配比。

纵观整个DRAM市场，AI与通用服务器的加速部署，叠加单系统DRAM搭载量的不断提升，预计将持续推高服务器DRAM的需求。在未来两年存储器价格上涨的周期内，这一强劲需求足以完全抵消智能手机、个人电脑及消费电子市场疲软带来的影响。

![](https://substackcdn.com/image/fetch/$s_!2Opv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4f090096-02d5-4aaf-b7b2-d0233652675f_2002x1180.png)

来源： SemiAnalysis Memory Model

如果逻辑产能被释放给加速器，客户很快就需要将注意力转向从存储供应商处锁定更多HBM。传统DDR DRAM价格正在飙升，其利润率已大幅攀升，接近甚至超过了HBM供应合同锁定的利润水平。过去，HBM更丰厚的利润率，是存储供应商扩充HBM晶圆产能的明确动力。但随着利润率格局发生逆转，这一逻辑已不再成立，至少对2026年而言确实如此。

为了激励供应商增加HBM晶圆投片量而非生产常规晶圆，客户可能需要支付高于当前合约水平的价格，以确保获得增量的HBM供应。这一趋势在2027年下一轮HBM定价谈判尘埃落定时，预计将变得更加显著。如果存储供应商做出让步，将产能向HBM倾斜，那么传统DDR DRAM的可用比特供应量将进一步收紧。

另一个关键影响是比特产能从消费级应用向服务器和HBM重新分配，我们自2025年下半年起就一直在强调这一动态。在最新的存储模型分析中，我们重点探讨了消费市场冲击对潜在比特产能重新分配的影响。在消费端出货量削减50%的极端情境下，将释放约553.9亿Gb产能，大致相当于2026年DRAM总需求的14%。若出货量削减25%，则将释放约276.9亿Gb产能，约占DRAM总需求的7%，接近今年HBM总需求的80%。

![](https://substackcdn.com/image/fetch/$s_!qN_X!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffd82a56a-592f-48d7-8269-232c73920309_2379x504.png)

来源： SemiAnalysis Memory Model

我们的基本假设依然是，消费类产品出货量将出现较为温和的10%至15%的下滑。若出货量下调10%，大约将释放出110.76亿Gb的供给，这仅占DRAM总需求的3%左右。我们认为，这种程度的增量供给不足以实质性改变我们预期的今年整体供需格局。

核心问题在于，存储供应商对消费端疲软的准备有多充分，以及他们已经做出了多大程度的调整。我们认为，存储厂商对各消费终端市场的疲软态势已有充分认知。以三星为例，其管理层已在多个场合强调消费端疲软，我们认为其产能分配计划已将出货量下滑10%至15%的下行情形纳入考量。我们预计其他主要存储供应商也做出了类似部署。

## CoWoS – Tight but Easing

随着CoWoS产能限制缓解，前端产能现已成为最主要的瓶颈。尽管CoWoS产能依然受限，但台积电在规划产能时，已将N3工艺的限制考虑在内。如果没有充足的前端晶圆供应支撑，台积电过度投资CoWoS产能将毫无意义。此外，2.5D封装也有其他替代方案。CoWoS不仅可以外包，此前也已有交由日月光/硅品（ASE/SPIL）和安靠（Amkor）等封测代工厂（OSAT）的先例。例如，在传出有望获批出口许可的消息时，英伟达便将面向中国市场的H200交由安靠封装。英特尔的旗舰级EMIB 2.5D先进封装方案也是另一个日益受青睐的选择，Trainium和TPU均已在不同程度上采用了该方案。

在付费内容中，我们将探讨另外两大主要瓶颈：数据中心和电力。随着时间的推移，这些制约因素已经发生了演变。

## From Power-Constrained to Accelerator-Constrained

过去几年，数据中心和电力一直是主要的制约因素。为了部署更多算力并让新集群上线，整个行业竞相扩充数据中心与电力容量。业界在这方面表现极其出色，甚至采用了现场天然气发电等创新方案。[然而，我们的预测显示，电力供应将超出AI算力需求](https://newsletter.semianalysis.com/p/are-ai-datacenters-increasing-electric)，因为晶圆制造产能未能跟上数据中心新增容量的步伐。电力已不再是硬性约束，加速器芯片供应才是。这标志着AI周期发生了结构性转变。在周期早期，数据中心建设和电力供应曾是首要瓶颈。

![](https://substackcdn.com/image/fetch/$s_!2w69!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdd301614-887f-443c-9fc2-5d2455c8419e_1850x1046.png)

来源： SemiAnalysis Datacenter Model

扩建数据中心与电力设施，远比新建晶圆厂容易得多。

这些工作固然困难重重，供应链也将借此赚取巨额利润并诞生众多成功企业，但人类的聪明才智最终会攻克这些难关。

## Supply-Chain Control Matters Most: Nvidia The Most Prepared

在当前环境下，能否搞定采购才是重中之重。在算力短缺而数据中心电力充足的情况下，AI实验室会扫光所有能弄到手的可用算力。英伟达再次成为最大赢家，他们已经锁定了大部分逻辑晶圆、存储器以及各类其他必需组件的供应。英伟达早就预见到了这种局面，因此他们在搞定供应链方面最下血本：黄仁勋的亚洲之行可不只是为了去逛夜市。他2025年的韩国之行正是为了锁定存储器产能，这不仅为英伟达获取更便宜的DRAM打下了基础，也替客户扛下了采购压力。 尽管Anthropic对[TPU](https://newsletter.semianalysis.com/p/tpuv7-google-takes-a-swing-at-the?utm_source=publication-search)和[Trainium](https://newsletter.semianalysis.com/p/aws-trainium3-deep-dive-a-potential?utm_source=publication-search)的大量使用，在一定程度上让GPU与定制ASIC的路线之争愈演愈烈，但眼下最直接的现实是：哪家供应商能锁定最多的芯片供应，谁就能最终占据最大的已部署算力份额。
