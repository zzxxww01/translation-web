https://substackcdn.com/image/fetch/$s_!o-hR!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F62444551-a7bc-4619-ae99-74199208f209_2880x1620.jpeg

AMD MI300X 与 MI355X XCD 对比图。来源：AMD, ISSCC 2026

AMD 介绍了其 MI355X GPU。在会议演讲中，AMD 通常只是复述先前的公告，仅引入一两条新信息。但这份论文在这方面要好得多，它详细解释了 MI355X 的 XCD（核心计算芯片）和 IOD（输入输出芯片）相较于 MI300X 是如何改进的。

https://substackcdn.com/image/fetch/$s_!zxX3!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb0f76dac-c592-4dd4-ab6d-0d1054fc2f8b_2880x1620.jpeg

AMD MI300X 与 MI355X XCD 面积效率对比。来源：AMD, ISSCC 2026

AMD 详细说明了他们如何在保持总面积不变、计算单元（CU）数量大体相似的情况下，将每个 CU 的矩阵吞吐量提升了一倍。首先，当然是从 N5（5纳米）制程节点转向 N3P（3纳米增强版）节点；这带来了晶体管密度提升的主要部分。N3P 提供的额外两层金属层改善了布线能力，从而提高了单元利用率。与之前在 N5 节点上的做法一样，AMD 设计了自家的标准单元，以针对其高性能计算（HPC）应用场景进行优化。

他们还采用了更密集的布局算法，其思路类似于 EPYC Bergamo CPU 中使用的 Zen 4c 核心比 EPYC Genoa CPU 中的 Zen 4 核心更紧凑的设计。

在使用 FP16、FP8、MXFP4 等多种不同数据格式执行相同计算时，有两种方法。第一种是使用共享硬件，所有格式都经过相同的电路。然而，这会带来功耗代价，因为针对每种格式的优化很少。第二种选择是每种数据格式使用完全不同的电路组进行计算。但这会占用大量额外面积。当然，最优方案介于两者之间——这也正是 AMD 优化工作的一个重要焦点。

https://substackcdn.com/image/fetch/$s_!tuPF!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2c313972-5315-4d1e-aa02-be6f1ffad996_2880x1620.jpeg

AMD MI355X XCD 频率与能效提升。来源：AMD, ISSCC 2026

作为晶体管性能得到改进的下一代制程节点，N3P 本身就能带来性能提升。然而，在不依赖制程节点改进的情况下，AMD 就已设法在同等功耗下将频率提升了 5%。此外，他们还设计了多种具有不同功耗和性能特性的触发器变体，并根据使用场景和架构需求，将其部署在芯片的不同区域。

https://substackcdn.com/image/fetch/$s_!Yxoy!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8b8604cb-0c0d-404c-942a-7b8fe000edd8_2880x1620.jpeg

AMD MI355X IOD 合并带来的能效提升。来源：AMD, ISSCC 2026

MI300X 配备了 4 个 IOD（输入输出裸片）。MI355X 则将其减少至两个。通过这种方式，AMD 节省了用于裸片间互连的面积。更大的单片式裸片改善了延迟，并减少了串行器/解串器（SerDes）及相关的协议转换开销。此外，通过增加互连宽度，高带宽内存（HBM）的效率也得到了提升。由此节省的功耗可以重新分配给计算裸片，以提高性能。

https://substackcdn.com/image/fetch/$s_!rkb_!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faee3a34c-c53c-4661-ac14-8907a7764064_2880x1620.jpeg

AMD MI355X IOD 互连功耗优化。来源：AMD, ISSCC 2026

由于这是一个大型裸片，芯片上任意两点间存在多种布线路径可选，因此 AMD 必须投入大量工作来优化导线与互连。通过对导线进行定制化工程设计，AMD 成功将互连功耗降低了约 20%。
