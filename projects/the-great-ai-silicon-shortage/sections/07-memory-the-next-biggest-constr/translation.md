全球存储芯片短缺短期内不太可能缓解。随着芯片供应商和超大规模云厂商竞相锁定DRAM供应以满足加速器生产需求，存储芯片已成为下一个主战场。尽管DRAM晶圆总产能持续增长，但大部分新增产能正被HBM吞噬，实质上挤压了通用DRAM的产能。

按每比特晶圆消耗量计算，HBM消耗的晶圆产能约为标准型DRAM的三倍。随着今年业界向HBM4过渡，这一差距可能会扩大至近四倍，而明年进入HBM4E阶段时还会进一步拉大。因此，HBM的增量扩张从标准型DRAM手中抽离了不成比例的DRAM晶圆产能份额，进一步加剧了存储市场结构性紧缺的局面。

https://substackcdn.com/image/fetch/$s_!3wRG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe3edd595-4b9d-4d67-8da2-ee97a6f6e053_2136x1126.png

来源： SemiAnalysis Memory Model

https://substackcdn.com/image/fetch/$s_!3eWl!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faab0bd24-a53a-4e2a-a0ea-7daa0057e0f8_2004x1094.png

来源： SemiAnalysis Memory Model

随着单颗加速器搭载的HBM容量急剧上升，这种压力正被进一步放大。HBM的比特出货量正迎来陡峭的增长拐点，这主要归因于单设备内存容量的提升，而非仅仅依赖于设备出货量的增长。对英伟达（NVIDIA）而言，从Blackwell向Blackwell Ultra和Rubin的迭代，使其HBM容量增加了50%，而Rubin Ultra更是将推动容量进一步实现约4倍的增长。超大规模云厂商的定制芯片（ASIC）也在经历类似的跨越式升级，TPU v8AX和Trainium3均从上一代的8层（8-Hi）堆叠升级至12层（12-Hi）堆叠，而AMD从MI350到MI400的内存容量也实现了50%的增长。

https://substackcdn.com/image/fetch/$s_!vlh2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F17bae206-924e-4e87-a7f1-c91a3f257c9e_2098x1130.png

来源： SemiAnalysis Accelerator Model

另一个加剧供应紧张的因素是业界对更高HBM引脚速度的追求。诸如英伟达（NVIDIA）等客户正将HBM4的引脚速度目标设定在11 Gb/s左右，这一要求对于存储供应商而言，仍难以在可接受的良率水平下达成。尽管SK海力士和三星在满足这些规格方面取得了较好的进展，但美光（Micron）在HBM4上却处于落后态势，我们早在1月份的Rubin文章以及加速器与HBM模型中就探讨过这一动态。随着客户要求更高的引脚速度，而供应商难以实现规模化交付，这种性能要求的不断升级进一步限制了HBM的有效供应。

https://substackcdn.com/image/fetch/$s_!nRle!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5c55d753-0c40-4c17-83f1-e3d2063f7cfc_2134x1226.png

来源： SemiAnalysis Memory Model

除了HBM，服务器DRAM的需求也在走强。在英伟达的下一代平台中，AI服务器系统内存将出现实质性增长，VR NVL72机架搭载的DDR容量将达到原来的3倍，即每个Vera CPU配备1,536 GB，而此前的Grace CPU仅为512 GB。随着老化的云和企业服务器存量设备进入持续多年的替换周期，我们预计常规DRAM的比特需求也将在2026年迎来向上拐点。与此同时，AI工作负载，特别是数据暂存、任务编排和强化学习，正在拉动CPU需求，并将在未来逐步提升CPU与GPU的配比。

纵观整个DRAM市场，AI与通用服务器的加速部署，叠加单系统DRAM搭载量的不断提升，预计将持续推高服务器DRAM的需求。在未来两年存储器价格上涨的周期内，这一强劲需求足以完全抵消智能手机、个人电脑及消费电子市场疲软带来的影响。

https://substackcdn.com/image/fetch/$s_!2Opv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4f090096-02d5-4aaf-b7b2-d0233652675f_2002x1180.png

来源： SemiAnalysis Memory Model

如果逻辑产能被释放给加速器，客户很快就需要将注意力转向从存储供应商处锁定更多HBM。传统DDR DRAM价格正在飙升，其利润率已大幅攀升，接近甚至超过了HBM供应合同锁定的利润水平。过去，HBM更丰厚的利润率，是存储供应商扩充HBM晶圆产能的明确动力。但随着利润率格局发生逆转，这一逻辑已不再成立，至少对2026年而言确实如此。

为了激励供应商增加HBM晶圆投片量而非生产常规晶圆，客户可能需要支付高于当前合约水平的价格，以确保获得增量的HBM供应。这一趋势在2027年下一轮HBM定价谈判尘埃落定时，预计将变得更加显著。如果存储供应商做出让步，将产能向HBM倾斜，那么传统DDR DRAM的可用比特供应量将进一步收紧。

另一个关键影响是比特产能从消费级应用向服务器和HBM重新分配，我们自2025年下半年起就一直在强调这一动态。在最新的存储模型分析中，我们重点探讨了消费市场冲击对潜在比特产能重新分配的影响。在消费端出货量削减50%的极端情境下，将释放约553.9亿Gb产能，大致相当于2026年DRAM总需求的14%。若出货量削减25%，则将释放约276.9亿Gb产能，约占DRAM总需求的7%，接近今年HBM总需求的80%。

https://substackcdn.com/image/fetch/$s_!qN_X!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffd82a56a-592f-48d7-8269-232c73920309_2379x504.png

来源： SemiAnalysis Memory Model

我们的基本假设依然是，消费类产品出货量将出现较为温和的10%至15%的下滑。若出货量下调10%，大约将释放出110.76亿Gb的供给，这仅占DRAM总需求的3%左右。我们认为，这种程度的增量供给不足以实质性改变我们预期的今年整体供需格局。

核心问题在于，存储供应商对消费端疲软的准备有多充分，以及他们已经做出了多大程度的调整。我们认为，存储厂商对各消费终端市场的疲软态势已有充分认知。以三星为例，其管理层已在多个场合强调消费端疲软，我们认为其产能分配计划已将出货量下滑10%至15%的下行情形纳入考量。我们预计其他主要存储供应商也做出了类似部署。
