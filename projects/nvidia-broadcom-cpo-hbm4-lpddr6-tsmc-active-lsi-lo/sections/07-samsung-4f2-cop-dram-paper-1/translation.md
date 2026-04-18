我们已广泛探讨了持续微缩 DRAM 所面临的挑战。

- 内存墙：DRAM 的过去、现在与未来 - Dylan Patel, Jeff Koch 等 · 2024年9月3日

在 VLSI 2025 上，SK海力士详细介绍了其 4F² 外围电路位于单元之下（Peri-Under-Cell, PUC）DRAM。到了 ISSCC，三星则披露了其 4F² 单元位于外围电路之上（Cell-on-Peripheral, COP）DRAM 的实现方案。PUC 和 COP 是同一架构的不同名称。

https://substackcdn.com/image/fetch/$s_!R4vq!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1d73da51-6e13-4c3f-a013-11188a56fcaf_2880x1620.jpeg

4F² 垂直沟道晶体管（VCT）DRAM 存储单元架构。来源：三星，ISSCC 2026

该 4F² 存储单元的架构与 SK海力士的相同，均采用垂直沟道晶体管（VCT），且电容器位于漏极上方。

https://substackcdn.com/image/fetch/$s_!4BMO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb889dd90-99fa-42d6-acc7-c8198d858390_2880x1620.jpeg

单元位于外围电路之上（COP）DRAM 堆叠架构。来源：三星，ISSCC 2026

三星展示的垂直架构与SK海力士所采用的架构基本相同，都是通过混合键合将存储单元晶圆堆叠在外围电路晶圆之上。采用这种架构，便可以为存储单元晶圆使用DRAM制程节点，同时为外围电路使用更先进的逻辑制程节点。

https://substackcdn.com/image/fetch/$s_!cEvZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff2c22653-7ddd-4eb8-87da-131a04a44314_2880x1620.jpeg

DRAM与NAND的COP架构对比。来源：三星，ISSCC 2026

三星指出，COP（单元位于外围电路之上）的混合键合技术已在NAND闪存中得到应用。这一点对其他NAND制造商成立，但三星尚未将用于NAND的混合键合技术投入大规模生产，且距离实现量产仍有数年之遥。

此外，DRAM所需的晶圆间连接数量比NAND高出一个数量级，且要求更紧密的节距。为了减少晶圆间互连的数量，三星采用了两种新颖的方法。

https://substackcdn.com/image/fetch/$s_!vZzA!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F058cc85d-e7c7-4d2c-bafe-43cdc55f9607_2880x1620.jpeg

COP NOR型子字线驱动器优化。来源：三星，ISSCC 2026

https://substackcdn.com/image/fetch/$s_!Q4d0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F148125f3-7781-496c-9df5-f4ef6dd56b70_2880x1620.jpeg

COP奇偶列选择多路复用器优化。来源：三星，ISSCC 2026

首先，他们将子字线驱动器（SWD）从每个存储单元块128个重组为16组（每组8个），从而使SWD所需的信号数量减少了75%。

其次，他们将列选择路径拆分为奇数和偶数两条路径。这虽然需要两倍数量的多路复用器（MUX），但将每数据引脚的列选择线（CSL）数量减半至32条。

https://substackcdn.com/image/fetch/$s_!-Vrx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F76c17f7b-d3ae-4595-bee1-b49403715d62_2880x1620.jpeg

COP存储单元阵列下方的核心电路布局。来源：三星，ISSCC 2026

借助混合键合技术，核心电路——即位线感测放大器（BLSA）和子字线驱动器（SWD）——得以置于存储单元阵列下方。其目标是让核心电路占据与存储单元阵列相同的面积，从而提高整体密度。

https://substackcdn.com/image/fetch/$s_!2ZFO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe3f4b60f-a3f5-4985-a5f6-d3a804ae9a69_2880x1620.jpeg

COP核心电路布局方案。来源：三星，ISSCC 2026

三星采用了“三明治”结构，以最大化核心电路的面积效率，并减少未被任何存储单元覆盖的边缘区域面积。

https://substackcdn.com/image/fetch/$s_!NQFx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb1824aa4-f1c3-4174-94c7-320067ca2401_2880x1620.jpeg

COP三明治结构的面积效率。来源：三星，ISSCC 2026

核心电路所占用的面积从17.0%大幅降低至仅2.7%，这一显著改进直接转化为整体芯片尺寸的缩减。

在传统DRAM中，增加每条位线上的存储单元数量会导致芯片面积显著增加；而对于VCT DRAM，由于核心电路全部位于存储单元下方，这种面积增加几乎可以忽略不计。

https://substackcdn.com/image/fetch/$s_!cPId!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3bfef447-2020-4611-af35-496a0f7926c9_2880x1620.jpeg

三星4F² COP DRAM总结与芯片显微照片。来源：三星，ISSCC 2026

三星并未提供该芯片的任何具体密度数据，仅说明这是一款基于10纳米DRAM工艺的16 Gb芯片。

三星指出，VCT DRAM存在浮体效应问题，这会增加漏电流并缩短数据保持时间。如何抑制这一效应，仍是4F²技术得以广泛应用所面临的关键挑战。

尽管存在这些挑战，我们仍然预计采用混合键合的4F² DRAM将在本十年晚些时候到来，最早可能是在1d制程节点之后的下一代产品中。我们的内存模型详细追踪了每个制程节点的时间表和量产进度。当前的内存定价环境在很大程度上激励着厂商推进并引入具有更高比特密度的新制程节点，以提高每座晶圆厂的比特产出。另一方面，对于许多应用场景，内存的性价比比容量本身更受重视。
