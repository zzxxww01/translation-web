# ISSCC 2026：英伟达与博通共封装光学、HBM4 与 LPDDR6、台积电主动硅中介层、逻辑 SRAM、UCIe-S 等前瞻

## Introduction

### ISSCC 2026 前瞻综述

作者：[Afzal Ahmad](https://substack.com/@afzalahmad)、[Gerald Wong](https://substack.com/@geraldwong116502)、[Daniel Nishball](https://substack.com/@danielnishball730869) 等 7 人

2026 年 4 月 15 日 · 付费文章

每年有三个主要的半导体会议：[国际电子器件会议（IEDM）](https://newsletter.semianalysis.com/p/interconnects-beyond-copper-1000)、[超大规模集成电路（VLSI）研讨会](https://newsletter.semianalysis.com/p/vlsi2025)，以及 ISSCC。过去几年，我们已经详细报道了前两个会议。今天，我们终于通过对 ISSCC 2026 的综述，完成了对这半导体会议“三巨头”的系列报道。

与国际电子器件会议和超大规模集成电路研讨会相比，ISSCC 更侧重于集成与电路。几乎每篇论文都附带了某种形式的电路图，并配有清晰的测量数据。

过去几年，ISSCC 的研究成果对产业界的影响时好时坏。今年则有所不同，有相当数量的论文和演示与市场趋势直接相关。涵盖的主题范围广泛，从高带宽内存第四代（HBM4）、低功耗双倍数据率第六代（LPDDR6）、图形用双倍数据率第七代（GDDR7）以及 NAND 闪存的最新进展，到共封装光学、先进的裸片到裸片互连接口，再到联发科、AMD、英伟达和微软等公司推出的先进处理器。

本综述将涵盖内存、光网络、高速电气互连和处理器等主要技术领域。

## Memory

在今年国际固态电路会议（ISSCC）上，一个引起我们关注的关键主题是存储器，具体涵盖了三星的 HBM4、三星与 SK 海力士的 LPDDR6，以及 SK 海力士的 GDDR7。除了动态随机存取存储器（DRAM），基于逻辑的静态随机存取存储器（SRAM）和磁阻随机存取存储器（MRAM）也同样吸引了我们的目光。

## Samsung HBM4 - Paper 15.6

在三大存储器厂商中，三星是唯一一家就 HBM4 发表技术论文的。在 ISSCC 之前，我们曾在[加速器与HBM模型](https://semianalysis.com/institutional/hbm4-samsung-incremental-progress-micron-execution-risk-rising-hbm3e-pricing-revised-up/)中指出，三星在其 HBM4 代产品上相比 HBM3E 取得了巨大改进。ISSCC 上公布的数据证实了我们的分析，三星展示了同类最佳的性能——我们数月前也在[模型更新说明](https://semianalysis.com/institutional/samsung-hbm4-performance-leadership-sk-hynix-hbm4-issues/)中详细阐述了这一进展。

ISSCC 上披露的技术细节，结合我们收集到的业界讨论，清晰地表明三星的 HBM4 已具备与同行竞争的实力。值得注意的是，它能够在电压低于 1V 的同时，满足 Rubin 所需的引脚速度。尽管三星在可靠性和稳定性方面仍落后于 SK 海力士，但该公司在技术层面已取得显著进步，缩小了差距，并可能挑战 SK 海力士在 HBM 领域的统治地位。其基于 1c 制程的 HBM4 搭配 SF4 逻辑基础芯片，看来在引脚速度上表现更优。

![](https://substackcdn.com/image/fetch/$s_!8SFa!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F515a99f4-5397-4b1a-9f95-d9a3dff37521_2880x1620.jpeg)

*三星 HBM3E 与 HBM4 规格对比。来源：三星，ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!t-2P!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F773189fd-1dd5-434a-aa0c-694db785b9c9_2880x1620.jpeg)

*三星 HBM4 芯片照片与截面图。来源：三星，ISSCC 2026*

三星展示了一款 36 GB、12 层堆叠的 HBM4 产品，拥有 2048 个 I/O 引脚和 3.3 TB/s 的带宽。该产品采用第六代 10 纳米级（1c）DRAM 核心芯片，并搭配了 SF4 逻辑基础芯片。

从 HBM3E 到 HBM4，最明显的架构变化在于核心 DRAM 芯片与基础芯片采用了不同的工艺技术。HBM4 仅对核心芯片使用 DRAM 制程节点，而基础芯片则采用先进的逻辑制程节点制造。这与前几代 HBM 对两者使用相同工艺的做法不同。

随着 AI 工作负载对 HBM 的带宽和数据速率提出更高要求，关键的架构挑战也随之产生。通过将基础芯片转移到 SF4 逻辑制程，三星实现了更高的运行速度和更低的功耗。其工作电压（VDDQ）从 HBM3E 的 1.1V 降至 HBM4 的 0.75V，降幅 32%。与采用 DRAM 工艺制造的基础芯片相比，基于逻辑制程的基础芯片能提供更高的晶体管密度、更小的器件尺寸以及更好的面积效率，这得益于其更小的晶体管和更丰富的金属层堆叠可用性。这帮助三星的 HBM4 不仅达到，而且显著超越了 JEDEC 的 HBM4 标准——我们将在本节末尾对此进行更详细的解释。

![](https://substackcdn.com/image/fetch/$s_!SBki!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff3e96393-ade6-49e3-82fa-8127beff5ad4_2880x1620.jpeg)

三星 HBM4 自适应体偏置控制与工艺波动。来源：三星，ISSCC 2026

结合能缓解堆叠核心芯片间工艺波动的自适应体偏置（ABB）控制，翻倍的 TSV 数量进一步提升了时序裕量。三星的论文宣称，ABB 和高达 4 倍的 TSV 数量共同使其 HBM4 能够实现每引脚高达 13 Gb/s 的运行速度。

然而，SF4 基础芯片和 1c DRAM 核心芯片带来的性能提升是有代价的。三星选择**SF4 工艺制造逻辑基础芯片，这一决策导致其成本高于竞争对手的方案**，尽管三星晶圆代工厂能为内部使用提供折扣。相比之下，SK 海力士为其 HBM4 基础芯片采用**台积电的 N12 逻辑制程**，而美光则依赖其**内部 CMOS 基础芯片技术**。这两种方案的成本都低于接近前沿的 SF4 制程节点，即使考虑到垂直整合带来的成本优势也是如此。

事实证明，1c 前端制造工艺在整个 2025 年对三星而言都颇具挑战，尤其是考虑到该公司跳过了 1b 节点，直接从基于 1a 的 HBM3E 过渡到 1c 世代。去年，1c 节点的前端良率仅约为 50%，尽管随着时间的推移已逐步改善。较低的良率对其 HBM4 的利润率构成了风险。

从历史上看，三星 HBM 的利润率一直低于其主要竞争对手 SK 海力士。[我们在我们的**内存模型**中对所有厂商的这一动态进行了全面建模](https://semianalysis.com/memory-model/)详细列出了各厂商在不同制程节点下 HBM、DDR 和 LPDDR 的晶圆产量、良率、密度、销货成本等数据。

三星的策略似乎是激进地采用更先进的制程节点来制造基础芯片，以实现卓越性能并超越竞争对手。尤其是在英伟达等主要客户对 HBM 的要求持续提高的背景下，这一策略显得尤为突出。

HBM 中另一个需要解决的关键问题是 tCCDR，即在不同堆栈 ID（SID）间连续发出读取命令所需的最小时间间隔。对于严重依赖跨多个通道并行内存访问的 AI 工作负载而言，tCCDR 直接影响可实现的存储器吞吐量。

在堆叠式 DRAM 架构中，多个核心芯片垂直集成在基础芯片之上。这自然会引入整个堆栈内的微小延迟差异，其驱动因素包括核心芯片与基础芯片间的工艺波动、硅通孔（TSV）传输延迟差异以及局部通道差异。

堆叠高度和通道数量从 16 层增至 32 层，加剧了这一挑战。随着通道数和堆叠高度的增加，芯片间的差异会累积，导致跨通道和跨芯片的时序失配更严重，从而影响可实现的 tCCDR 和 HBM 整体性能。

![](https://substackcdn.com/image/fetch/$s_!YCM6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe56f1735-adbc-4038-8473-b27f5ae002fb_1611x1352.jpeg)

**三星 HBM4 每通道 TSV RDQS 自动校准方案。来源：三星，ISSCC 2026**

为解决此问题，三星引入了一种“每通道 TSV RDQS 时序自动校准方案”。上电后，系统使用一个复制真实信号路径时序行为的 RDQS 复制路径来测量各通道的延迟差异。时间数字转换器（TDC）将这些时序差异量化，随后通过为每个通道配置的延迟补偿电路（DCDL）进行补偿。

该校准方案同时考虑了堆叠核心芯片间的全局延迟差异和局部每通道差异，从而对齐整个堆栈的时序。通过补偿这些失配，三星显著提升了有效时序裕量，并在满足所需 tCCDR 限制的同时，提高了最大可实现数据速率。仅此一项方案就将数据速率从 7.8 Gb/s 提升至 9.4 Gb/s。

我们一些精通存储器技术的读者可能会问：如何有足够的芯片面积来容纳大幅增加的 TSV 数量？这正是 1c 制程节点变得重要的原因。与之前的 1a 节点相比，1c 进一步缩小了 DRAM 存储单元面积，从而释放出芯片空间，可用于集成 HBM4 所需的大量 TSV。

![](https://substackcdn.com/image/fetch/$s_!FNwT!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F35b20c2b-2f00-4d4c-b05a-578d695a51c1_2880x1620.jpeg)

三星 HBM4 PMBIST 测试模式操作。来源：三星，ISSCC 2026

![](https://substackcdn.com/image/fetch/$s_!06LM!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fec777954-f7fa-44fb-a8b3-f295d57f3e59_2880x1620.jpeg)

三星 HBM4 PMBIST 与 HBM3E MBIST 对比。来源：三星，ISSCC 2026

逻辑基础芯片带来的另一项关键创新是三星的可编程内存内建自测试（PMBIST）架构。PMBIST 允许基础芯片生成完全可编程的内存测试模式，同时支持完整的 JEDEC 行与列命令集。这意味着测试引擎能够发出与实际系统完全相同的命令，且可在任意时钟沿、以全接口速度执行这些命令。实际上，这使得工程师能够复现复杂的真实世界内存访问模式，并在实际运行条件下对 HBM 接口进行压力测试，而这是传统固定模式测试引擎难以做到的。

这种方法与 HBM3E 相比有显著不同。如前文所述，HBM3E 的基础芯片采用 DRAM 工艺制造，这给其 MBIST（内存内建自测试）引擎带来了严格的功耗和面积限制，并且，鉴于 DRAM 工艺在功耗和面积效率方面天然逊色于逻辑工艺，其测试只能局限于一小部分预定义的模式。通过将基础芯片转移到三星晶圆代工厂的 SF4 逻辑工艺，三星得以实现一个完全可编程的测试框架，能够运行复杂的测试算法和灵活的访问序列。

这为 HBM 带来了更强大的调试能力和更好的良率学习效果。工程师可以创建有针对性的压力测试模式，以验证 tCCDR 和 tCCDS 等关键时序参数，在制造早期识别极端情况下的故障，并加速晶圆上芯片（CoW）和系统级封装（SiP）测试阶段的特性表征。简而言之，随着 HBM 堆栈变得更复杂、运行速度更高，PMBIST 提升了测试覆盖率、调试效率，并最终提高了生产良率。

![](https://substackcdn.com/image/fetch/$s_!E1zF!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8a03c69a-dc9b-4dfb-a6d2-ad4315760852_2880x1620.jpeg)

三星 HBM4 舒姆图。来源：三星，ISSCC 2026

三星还展示了强劲的引脚速度结果——其 HBM4 能够在低于 1V 的核心电压（VDDC）下达到 11 Gb/s，并在更高电压下达到 13 Gb/s。我们尚未看到三星的同行展示出可比的性能，尽管后者在可靠性和稳定性上确实更具优势。

三星的实现方案大幅超越了官方 JEDEC HBM4 标准（JESD270-4）的基线规范，该规范规定的最大引脚数据速率为 6.4 Gb/s，总带宽约为 2 TB/s。三星展示的引脚速度是 JEDEC 标准的两倍多，达到 13 Gb/s，可提供 3.3 TB/s 的带宽。即使在 VDDC/VDDQ 电压分别为 1.05V 和 0.75V 时，该器件仍能维持 11.8 Gb/s 的数据速率。

## Samsung LPDDR6 - Paper 15.8

三星和 SK 海力士均展示了各自的 LPDDR6 芯片。我们将首先讨论三星的芯片，稍后再转向 SK 海力士的。

![](https://substackcdn.com/image/fetch/$s_!Odn_!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb15266c9-bc1e-4365-9316-28d2a6e36fac_2880x1620.jpeg)

*LPDDR5X 与 LPDDR6 对比。来源：三星，ISSCC 2026*

三星介绍了其 LPDDR6 架构，并详细阐述了所采用的节能技术。

![](https://substackcdn.com/image/fetch/$s_!Ysn8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0098a613-71de-4d6c-b446-2a203e66fef7_2880x1620.jpeg)

*LPDDR6 子通道与存储体结构。来源：三星，ISSCC 2026*

LPDDR6 采用了每颗芯片两个子通道的架构，每个子通道包含 16 个存储体。它还具备两种模式：正常模式和能效模式。在能效模式下，第二个子通道会断电，由主子通道控制全部 32 个存储体。然而，访问第二个子通道中的数据会带来延迟惩罚。

双子通道架构也意味着外围电路（如命令解码器、串行化与控制电路）的数量翻倍。根据三星和 SK 海力士提供的芯片照片，这一面积惩罚约占芯片总面积的 5%，导致每片晶圆的总比特数有所减少。

![](https://substackcdn.com/image/fetch/$s_!79tH!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F68f2f392-7912-4f69-9c53-ef6c4f6942b6_2880x1620.jpeg)

*LPDDR6 信号方案。来源：三星，ISSCC 2026*

与采用三电平脉冲幅度调制（PAM3）信号的 GDDR7 不同，LPDDR6 将继续使用不归零制（NRZ）。然而，它并不使用标准的 NRZ，因为其信号眼图裕量会不足。LPDDR6 采用的是宽不归零制（Wide NRZ），每个子通道有 12 个数据（DQ）引脚，且每次操作的突发长度为 24。

![](https://substackcdn.com/image/fetch/$s_!GQm1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1737c518-8a4f-4042-a536-513a9f769cb8_2880x1620.jpeg)

*LPDDR6 每次突发的元数据与数据总线翻转（DBI）位分配。来源：三星，ISSCC 2026*

这里有个细节值得注意：12×24 等于 288，并非 2 的幂次方。剩余的 32 位被分配给了两种用途：16 位用于元数据（如纠错码 ECC），另外 16 位则用于数据总线翻转（DBI）。

数据总线翻转（DBI）是一种节能和信号完整性机制。在发送一个突发数据之前，控制器会检查与前一次突发相比，是否有超过一半的比特位将发生状态翻转。如果是，控制器就会将所有比特位取反，并设置一个 DBI 标志位，以便接收端知道需要再次取反才能得到真实数据。这一机制将同时发生翻转的输出信号最大数量限制在总线宽度的一半，从而降低了功耗和电源噪声。

计算有效带宽时，必须考虑这些元数据和 DBI 位，公式如下：带宽 = 数据速率 × 突发长度（24 位） × 数据位（32 位） / 数据包总位数（36 位）。因此，在 12.8 Gb/s 的数据速率下，有效带宽为 34.1 GB/s；而在 14.4 Gb/s 下，则为 38.4 GB/s。

![](https://substackcdn.com/image/fetch/$s_!bjV0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F986010c2-7d39-4d5f-b195-76d6c653c5ea_2880x1620.jpeg)

三星 LPDDR6 高频电源域优化。来源：三星，ISSCC 2026

LPDDR6 有两个恒定电源域：VDD2C 为 0.875V，VDD2D 为 1.0V。通过精心选择外围逻辑电路所使用的电源域，读取功耗降低了 27%，写入功耗降低了 22%。

![](https://substackcdn.com/image/fetch/$s_!QJ_x!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8741b331-6528-4e4f-a064-722f271f43a0_2880x1620.jpeg)

三星 LPDDR6 在低数据速率下的 I/O 电源切换。来源：三星，ISSCC 2026

![](https://substackcdn.com/image/fetch/$s_!iMMC!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F06109578-4db8-490e-b963-1968a2ebacb0_2880x1620.jpeg)

三星 LPDDR6 额外的低功耗 DQ/CA 路径。来源：三星，ISSCC 2026

LPDDR 在空闲时主要运行于 3.2 Gb/s 及以下的低数据速率。三星将重点放在这些较低数据速率下的功耗节省上，通过精心利用电压域，同时降低了待机功耗和读写功耗。

![](https://substackcdn.com/image/fetch/$s_!Tycr!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F931c917e-8cf5-4e59-9b07-45faa91aeee0_2880x1620.jpeg)

LPDDR6 重布线层时序与布局优势。来源：三星，ISSCC 2026

通过使用重布线层，三星可以将相关电路在物理上布局得更近。这缩短了关键延迟路径，并降低了其对电压和温度变化的敏感性。在 LPDDR6 的高频下，更严格的时序控制和更小的变化至关重要。

![](https://substackcdn.com/image/fetch/$s_!UXaU!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F295c4906-10e2-4877-909b-d7c76e61a6f4_2880x1620.jpeg)

三星 LPDDR6 规格参数与芯片显微照片。来源：三星，ISSCC 2026

![](https://substackcdn.com/image/fetch/$s_!003E!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6c037b47-34b6-41db-b615-2e62e41bba05_2880x1620.jpeg)

三星 LPDDR6 舒姆图。来源：三星，ISSCC 2026

三星的 LPDDR6 可在 0.97V 电压下实现 12.8 Gb/s 的数据速率，在 1.025V 电压下最高可达 14.4 Gb/s。每个 16 Gb 芯片的面积为 44.5 mm²，基于未知的 10 纳米级工艺，其密度为 0.360 Gb/mm²。这一密度显著低于采用 1b 节点的 LPDDR5X（0.447 Gb/mm²），仅略高于采用 1a 节点的 LPDDR5X（0.341 Gb/mm²）。虽然双子通道架构确实带来了一定的面积代价，但 LPDDR6 本身似乎也存在其他问题。所描述的存储密度让我们相信，这款 LPDDR6 原型芯片是在其 1b 工艺上制造的。

## Samsung SF2 LPDDR6 PHY - Paper 37.3

![](https://substackcdn.com/image/fetch/$s_!EUBE!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F46165883-4137-4a8e-8fbd-76ee3b9dafd5_2880x1620.jpeg)

三星 LPDDR6 物理层测试芯片规格参数与芯片显微照片。来源：三星，ISSCC 2026

三星还展示了与 LPDDR6 接口的逻辑芯片上的物理层。这些物理层采用其全新的 SF2 工艺制造，最高支持 14.4 Gb/s 速率。其接口长度为 2.32 毫米，面积为 0.695 平方毫米，对应的带宽密度分别为每毫米 16.6 Gb/s 和每平方毫米 55.3 Gb/s。

![](https://substackcdn.com/image/fetch/$s_!NkaV!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffa36890f-e205-4a23-8281-71bf8c199448_2880x1620.jpeg)

三星 LPDDR6 物理层能效模式功耗降低效果。来源：三星，ISSCC 2026

这些物理层也支持 LPDDR6 芯片实现的能效模式，该模式可将读取功耗降低 39%，写入功耗降低 29%。

物理层还能通过门控非活跃的次子通道的高速时钟路径，来增强这一能效模式。结合时钟门控技术，读写功耗降低幅度接近 50%，空闲功耗则可降低 41%。

## SK Hynix 1c LPDDR6 - Paper 15.7

![](https://substackcdn.com/image/fetch/$s_!Mi3M!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4c8da198-d711-4b0a-8fcd-0d7fce1aa327_2880x1620.jpeg)

*SK 海力士 LPDDR6 规格参数与芯片显微图。来源：SK 海力士，ISSCC 2026*

SK 海力士首次展示了其采用 1c 工艺的 DRAM 产品，包括 LPDDR6 和 GDDR7 两种封装。其 LPDDR6 的最高数据速率可达 14.4 Gb/s，比最快的 LPDDR5X 提升了 35%，且功耗更低。

尽管 SK 海力士未公布 LPDDR6 芯片的面积或密度，但根据其 GDDR7 产品的相对密度提升幅度，我们估计其位密度将达到 0.59 Gb/mm²。

![](https://substackcdn.com/image/fetch/$s_!s1zW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd451b064-d3c9-43a0-b92b-e26efd5df094_2880x1620.jpeg)

SK 海力士 LPDDR6 舒姆图。来源：SK 海力士，ISSCC 2026

在其展示的舒姆图中，SK 海力士表明其产品可在 1.025V 电压下达到 14.4 Gb/s 的数据速率，这与三星相同。然而，在 0.95V 电压下，其速率仅能达到 10.9 Gb/s，而三星产品在 0.97V 下可达 12.8 Gb/s。这表明，在较低的引脚速率下，与三星相比，SK 海力士的能效可能较差，需要运行在更高电压以维持可靠性。

![](https://substackcdn.com/image/fetch/$s_!_oDZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9c3722fa-72c1-4ad3-9df8-2910380ab1d2_2880x1620.jpeg)

SK 海力士 LPDDR6 能效模式架构图。来源：SK 海力士，ISSCC 2026

![](https://substackcdn.com/image/fetch/$s_!io7g!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F001bcb01-81d3-42d2-b0a2-832688185377_2880x1620.jpeg)

SK 海力士 LPDDR6 能效模式节能效果。来源：SK 海力士，ISSCC 2026

与三星的 LPDDR6 类似，SK 海力士的 LPDDR6 也具备两种模式：普通模式和能效模式。在能效模式下，单个子通道以 12.8 Gb/s 的速率运行，其待机电流和工作电流相比普通模式分别降低了 12.7%和 18.9%。

## SK Hynix 1c GDDR7 - Paper 15.9

![](https://substackcdn.com/image/fetch/$s_!02R2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F75df5c4b-d65e-4d6e-ad17-46db43d1c124_2880x1620.jpeg)

SK 海力士 1c GDDR7 规格参数与芯片显微照片。来源：SK 海力士，ISSCC 2026

尽管 LPDDR6 凭借新存储技术实现了代际飞跃，但 SK 海力士在其 1c 工艺节点上开发的 GDDR7 进步更为显著，其在 1.2V/1.2V 电压下的时钟频率最高可达 48 Gb/s。即使在仅 1.05V/0.9V 的电压下，其频率也能达到 30.3 Gb/s，高于 RTX 5080 显卡中使用的 30 Gb/s 显存。

![](https://substackcdn.com/image/fetch/$s_!M7-j!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb54fd8fd-325c-495b-bd98-4187c051138b_2880x1620.jpeg)

三星 1z GDDR7 舒姆图与芯片显微照片。来源：三星，ISSCC 2024

![](https://substackcdn.com/image/fetch/$s_!zcG2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5fcf00cd-4001-4a32-8220-0846b9baa526_2880x1620.jpeg)

三星 1b GDDR7 规格参数与芯片显微照片。来源：三星，ISSCC 2025

其实现的位密度为 0.412 Gb/mm²，远高于三星 1b 工艺的 0.309 Gb/mm²和更早 1z 工艺的 0.192 Gb/mm²。

![](https://substackcdn.com/image/fetch/$s_!tQdH!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa8119950-b6d0-424a-af28-90305882aae1_1731x703.png)

各厂商 LPDDR5X 与 GDDR7 位密度对比。来源：SemiAnalysis

GDDR7 的位密度低于 LPDDR5X，通常约为后者的 70%。尽管其数据传输速率要高得多，但这在功耗和面积方面都付出了代价。

GDDR7 密度较低，是因为为了实现高访问速度，其外围电路面积显著增加。因此，实际的存储阵列在芯片面积中所占比例较小。这种更复杂的逻辑控制电路，是 GDDR7 所采用的三电平脉冲幅度调制（PAM3）和四倍数据速率（QDR，每个时钟周期传输 4 个符号）信号技术所必需的。

GDDR7 主要用于游戏 GPU 应用，这类应用需要高内存带宽，但与 HBM 相比，对成本和容量的要求较低。英伟达（NVIDIA）曾在 2025 年宣布其 Rubin CPX 大上下文 AI 处理器将配备 128GB GDDR7，但随着英伟达将重心转向推广其 Groq LPX 解决方案，该配置在 2026 年的路线图上已近乎绝迹。

我们在[内存模型](https://semianalysis.com/memory-model/)中详细分析了 HBM、DDR 和 LPDDR 在不同制程节点上的晶圆产量、良率、密度、销售成本（COGS）等数据。

## Samsung 4F² COP DRAM - Paper 15.10

我们已广泛探讨了持续微缩 DRAM 所面临的挑战。

- [内存墙：DRAM 的过去、现在与未来](https://newsletter.semianalysis.com/p/the-memory-wall) - Dylan Patel, Jeff Koch 等 · 2024 年 9 月 3 日

在 [VLSI 2025 上，SK海力士详细介绍了其 4F² 外围电路位于单元之下（Peri-Under-Cell, PUC）DRAM](https://newsletter.semianalysis.com/i/174558662/dram-4f2-and-3d)。到了 ISSCC，三星则披露了其 4F² 单元位于外围电路之上（Cell-on-Peripheral, COP）DRAM 的实现方案。PUC 和 COP 是同一架构的不同名称。

![](https://substackcdn.com/image/fetch/$s_!R4vq!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1d73da51-6e13-4c3f-a013-11188a56fcaf_2880x1620.jpeg)

*4F² 垂直沟道晶体管（VCT）DRAM 存储单元架构。来源：三星，ISSCC 2026*

该 4F² 存储单元的架构与 SK 海力士的相同，均采用垂直沟道晶体管（VCT），且电容器位于漏极上方。

![](https://substackcdn.com/image/fetch/$s_!4BMO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb889dd90-99fa-42d6-acc7-c8198d858390_2880x1620.jpeg)

*单元位于外围电路之上（COP）DRAM 堆叠架构。来源：三星，ISSCC 2026*

三星展示的垂直架构与 SK 海力士所采用的架构基本相同，都是通过混合键合将存储单元晶圆堆叠在外围电路晶圆之上。采用这种架构，便可以为存储单元晶圆使用 DRAM 制程节点，同时为外围电路使用更先进的逻辑制程节点。

![](https://substackcdn.com/image/fetch/$s_!cEvZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff2c22653-7ddd-4eb8-87da-131a04a44314_2880x1620.jpeg)

*DRAM 与 NAND 的 COP 架构对比。来源：三星，ISSCC 2026*

三星指出，COP（单元位于外围电路之上）的混合键合技术已在 NAND 闪存中得到应用。这一点对其他 NAND 制造商成立，但三星尚未将用于 NAND 的混合键合技术投入大规模生产，且距离实现量产仍有数年之遥。

此外，DRAM 所需的晶圆间连接数量比 NAND 高出一个数量级，且要求更紧密的节距。为了减少晶圆间互连的数量，三星采用了两种新颖的方法。

![](https://substackcdn.com/image/fetch/$s_!vZzA!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F058cc85d-e7c7-4d2c-bafe-43cdc55f9607_2880x1620.jpeg)

*COP NOR 型子字线驱动器优化。来源：三星，ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!Q4d0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F148125f3-7781-496c-9df5-f4ef6dd56b70_2880x1620.jpeg)

COP 奇偶列选择多路复用器优化。来源：三星，ISSCC 2026

首先，他们将子字线驱动器（SWD）从每个存储单元块 128 个重组为 16 组（每组 8 个），从而使 SWD 所需的信号数量减少了 75%。

其次，他们将列选择路径拆分为奇数和偶数两条路径。这虽然需要两倍数量的多路复用器（MUX），但将每数据引脚的列选择线（CSL）数量减半至 32 条。

![](https://substackcdn.com/image/fetch/$s_!-Vrx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F76c17f7b-d3ae-4595-bee1-b49403715d62_2880x1620.jpeg)

COP 存储单元阵列下方的核心电路布局。来源：三星，ISSCC 2026

借助混合键合技术，核心电路——即位线感测放大器（BLSA）和子字线驱动器（SWD）——得以置于存储单元阵列下方。其目标是让核心电路占据与存储单元阵列相同的面积，从而提高整体密度。

![](https://substackcdn.com/image/fetch/$s_!2ZFO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe3f4b60f-a3f5-4985-a5f6-d3a804ae9a69_2880x1620.jpeg)

COP 核心电路布局方案。来源：三星，ISSCC 2026

三星采用了“三明治”结构，以最大化核心电路的面积效率，并减少未被任何存储单元覆盖的边缘区域面积。

![](https://substackcdn.com/image/fetch/$s_!NQFx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb1824aa4-f1c3-4174-94c7-320067ca2401_2880x1620.jpeg)

COP 三明治结构的面积效率。来源：三星，ISSCC 2026

核心电路所占用的面积从 17.0%大幅降低至仅 2.7%，这一显著改进直接转化为整体芯片尺寸的缩减。

在传统 DRAM 中，增加每条位线上的存储单元数量会导致芯片面积显著增加；而对于 VCT DRAM，由于核心电路全部位于存储单元下方，这种面积增加几乎可以忽略不计。

![](https://substackcdn.com/image/fetch/$s_!cPId!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3bfef447-2020-4611-af35-496a0f7926c9_2880x1620.jpeg)

三星 4F² COP DRAM 总结与芯片显微照片。来源：三星，ISSCC 2026

三星并未提供该芯片的任何具体密度数据，仅说明这是一款基于 10 纳米 DRAM 工艺的 16 Gb 芯片。

三星指出，VCT DRAM 存在浮体效应问题，这会增加漏电流并缩短数据保持时间。如何抑制这一效应，仍是 4F²技术得以广泛应用所面临的关键挑战。

尽管存在这些挑战，我们仍然预计采用混合键合的 4F² DRAM 将在本十年晚些时候到来，最早可能是在 1d 制程节点之后的下一代产品中。我们的[内存模型详细追踪了每个制程节点的时间表和量产进度](https://semianalysis.com/memory-model/)。当前的内存定价环境在很大程度上激励着厂商推进并引入具有更高比特密度的新制程节点，以提高每座晶圆厂的比特产出。另一方面，对于许多应用场景，内存的性价比比容量本身更受重视。

## SanDisk/Kioxia BiCS10 NAND - Paper 15.1

闪迪（SanDisk）与铠侠（Kioxia）展示了其 BiCS10 NAND 闪存，该产品拥有 332 层，由 3 个栈（deck）构成。其位密度达到 37.6 Gb/mm²，是目前公开报告中的最高纪录，超越了此前保持领先的[SK海力士321层V9 NAND](https://newsletter.semianalysis.com/i/184077729/3d-nand-hynix-321-layer)。

![](https://substackcdn.com/image/fetch/$s_!xViG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9f240c14-4a4f-4fab-bc19-194185a47c6b_2880x1620.jpeg)

*BiCS10 芯片显微照片及其与 SK 海力士、三星 V9 的密度对比。来源：闪迪/铠侠，ISSCC 2026*

尽管采用了相似的架构（6 个平面、3 个堆叠结构，且层数相近），SK 海力士的位密度却落后了 30%。在 QLC（四层单元）配置下，BiCS10 的位密度为 37.6 Gb/mm²，而 SK 海力士 V9 仅为 28.8 Gb/mm²。在 TLC（三层单元）配置下，两者的密度分别为 29 Gb/mm²和 21 Gb/mm²，这进一步凸显了 SK 海力士在密度上的差距。

![](https://substackcdn.com/image/fetch/$s_!mqol!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6701cf01-e5c3-4aeb-87e6-ab7e99222f7d_2880x1620.jpeg)

*NAND 闪存 1×6 与 2×3 平面配置对比。来源：闪迪/铠侠，ISSCC 2026*

此外，BiCS10 采用了 6 平面配置，使其输入/输出（IO）带宽提升了 50%。实现 6 平面配置有两种方式：1×6 和 2×3。SK 海力士选择了 2×3 配置，而闪迪和铠侠则决定采用 1×6 配置。

1×6 配置的地线焊盘数量更少，能使芯片面积减少 2.1%。然而，地线焊盘和垂直电源走线数量的减少，也对电源分配构成了限制。

![](https://substackcdn.com/image/fetch/$s_!qU7L!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe1c58eb6-654f-4ec5-9d5b-14d27c7f3679_2880x1620.jpeg)

BiCS10 单元键合阵列（CBA）为电源分配增设的额外顶层金属层。来源：闪迪/铠侠，ISSCC 2026

通过采用单元键合阵列（CBA）架构，闪迪和铠侠能够定制 CMOS 晶圆的制造工艺。他们在现有顶层金属层的基础上，并行增设了另一层，从而构建了更强大的电源网格，并克服了电源分配的限制。

![](https://substackcdn.com/image/fetch/$s_!6HeL!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3c965c54-2786-4298-bdfc-f916f5133490_2880x1620.jpeg)

多芯片 NAND 空闲功耗问题及芯片关断解决方案。来源：闪迪/铠侠，ISSCC 2026

虽然堆叠更多芯片对提升存储密度至关重要，但在多芯片架构中，未选中芯片的空闲电流正逐渐接近选中芯片的工作电流。为此，闪迪实现了一套关断系统，能够完全关闭未选中芯片的数据通路，从而将空闲电流降低了两个数量级。

## MediaTek xBIT Logic-based Bitcell - Paper 15.2

![](https://substackcdn.com/image/fetch/$s_!m8pd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa42110ab-a204-4a5f-8977-830bd38e06ea_1283x461.jpeg)

*SRAM 高电流存储单元密度与基于逻辑的多位触发器的跨节点对比。来源：联发科，ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!NbiN!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fda693b39-6780-47ce-ac48-bf8a5b5a489f_2880x1620.jpeg)

*SRAM 存储单元微缩的局限性：面积与电压约束。来源：联发科，ISSCC 2026*

[SRAM微缩已死。](https://newsletter.semianalysis.com/i/174558465/sram-scaling-beating-a-dead-horse) 尽管逻辑面积从 N5 到 N2 减少了 40%，但 8 晶体管高电流 SRAM 存储单元的面积仅减少了 18%。6 晶体管高电流（6T-HC）存储单元的情况更糟，仅减少了 2%。辅助电路的微缩效果更明显，但这并非免费的午餐。

众所周知，[N3E的高密度存储单元相比N3B有所倒退，其密度回落到了N5的水平](https://newsletter.semianalysis.com/i/175660907/n3-technology-nodes)。在这篇论文中，联发科揭示了高电流存储单元的情况。N3E 的高电流存储单元面积相比 N5 增加了 1-2%，其密度则从约 39.0 Mib/mm²降至约 38.5 Mib/mm²。需要指出的是，这些数据并未计入辅助电路的开销。

![](https://substackcdn.com/image/fetch/$s_!_Cbb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe8879827-c259-4dfd-a9ae-79a59dbfc37d_2880x1620.jpeg)

*8 晶体管存储单元在逻辑规则下的 NMOS/PMOS 布局挑战。来源：联发科，ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!oxdV!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd4abf3fe-77e4-4333-a1c8-da1eeedb5789_2520x1408.jpeg)

*联发科 10 晶体管 xBIT 平衡型存储单元电路设计。来源：联发科，ISSCC 2026*

在现代逻辑工艺节点中，6 晶体管存储单元包含 4 个 NMOS 和 2 个 PMOS 晶体管，而 8 晶体管存储单元则分别包含 6 个和 2 个。NMOS 与 PMOS 晶体管数量不相等，这需要特殊的布局规则，从而降低了版图效率。联发科的新型存储单元是一个 10 晶体管单元，命名为 xBIT，其构成为 4 个 NMOS 和 6 个 PMOS 晶体管，或者反之亦然。这两种变体的存储单元可以组合排列成一个矩形块，包含 20 个晶体管，存储 2 比特数据。

![](https://substackcdn.com/image/fetch/$s_!n1LG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa550e975-e262-4350-8c6f-380c90b3ae01_2520x1408.jpeg)

*xBIT 与晶圆代工厂 8 晶体管存储单元密度及功耗对比。来源：联发科，ISSCC 2026*

与工艺设计套件中的标准 8 晶体管存储单元相比，xBIT 的密度提升了 22%至 63%，在字线宽度较低时增益最大。功耗也得到显著改善，平均读写功耗降低了 30%以上，在 0.5V 电压下漏电降低了 29%。在 0.9V 电压下，其性能与 8 晶体管存储单元相当；在 0.5V 电压下，其速度虽比 8T 存储单元慢 16%，但已足以避免成为处理器瓶颈，且其工作电压范围足够宽，适用于电压频率调节。

![](https://substackcdn.com/image/fetch/$s_!xu_9!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6f2a3a1a-a796-4979-8477-fab6bf41c58d_1699x1094.jpeg)

*xBIT 舒姆图。来源：联发科，ISSCC 2026*

联发科还展示了 xBIT 存储单元的舒姆图，其工作频率可从 0.35V 电压下的 100MHz，提升至 0.95V 电压下的 4GHz。

我们将在后续的通讯文章中，对 SRAM 及其微缩化影响因素进行深入探讨。

## TSMC N16 MRAM - Paper 15.4

台积电展示了其基于 N16 制程节点的更新版自旋转移矩磁阻随机存取存储器（STT-MRAM），该工作建立在 2023 年 ISSCC 上先前研究的基础上。台积电将这款 MRAM 定位为嵌入式非易失性存储器，主要面向汽车、工业和边缘应用。这些应用场景并不追求最先进的制程技术，而是将可靠性置于首位。

![](https://substackcdn.com/image/fetch/$s_!AEKe!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb74d1b16-3ff4-4bca-8df1-6e8909f865d1_2880x1620.png)

*台积电 N16 MRAM 设计特性与芯片版图。来源：台积电，ISSCC 2026*

这款 MRAM 具备双端口访问能力，因此读取和写入操作可以同时进行。这一特性对于汽车应用中的空中下载更新至关重要，因为在写入固件时，系统不能中断读取操作。

![](https://substackcdn.com/image/fetch/$s_!mICA!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2bb08e47-26dd-4357-b813-60ec053c33d4_2880x1620.png)

*台积电 N16 MRAM 在-40°C 和 150°C 下的舒姆图。来源：台积电，ISSCC 2026*

其设计特点在于，支持跨模块的交错读取，且各模块拥有独立时钟。这使得在 200MHz 频率下，吞吐量提升至 51.2 Gb/s。在硅芯片上，这个 84 Mb 的宏单元在 0.8V 电压、-40°C 至 150°C 的温度范围内，实现了 7.5 纳秒的读取访问时间。

![](https://substackcdn.com/image/fetch/$s_!qUbb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9ac17a55-6e1f-415f-bebb-b5dd0c966ea9_2880x1620.png)

*台积电 N16 MRAM 模块化宏单元架构。来源：台积电，ISSCC 2026*

该架构采用模块化设计——可配置为 16 Mb、8 Mb 和 2 Mb 的模块，这些模块组合成从 8 Mb 到 128 Mb 不等的宏单元。通过将大型的 16 Mb 模块与少量较小的 2 Mb 和 8 Mb 模块相结合，可以针对任何设计的需求对容量进行微调。例如，5 个 16 Mb 模块和 2 个 2 Mb 模块即可构成一个 84 Mb 的宏单元。

![](https://substackcdn.com/image/fetch/$s_!yxjs!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbe9063a9-d2b4-4d04-9dfd-ebf11aac4259_2880x1620.png)

*台积电 N16 MRAM 的耐久性与可靠性。来源：台积电，ISSCC 2026*

如前所述，可靠性是嵌入式 MRAM 成败的关键。在-40°C 下经过 100 万次耐久性循环后，其硬错误率仍远低于 0.01 ppm——完全处于 ECC（纠错码）的校正范围内。在 150°C 下，典型读取电压时的读取干扰低于 10⁻²² ppm，实际上可忽略不计。这款 168 Mb 的测试芯片通过了回流焊测试，并支持在 150°C 下保持 20 年的数据保存期，满足了严苛的汽车应用要求。

![](https://substackcdn.com/image/fetch/$s_!hLrV!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0ef20058-3a8c-4df0-85e1-5912e2da26ff_2880x1620.png)

*台积电 N16 MRAM 规格与先前工作的对比。来源：台积电，ISSCC 2026*

与同一 N16 节点上的旧款 MRAM 相比，其存储单元面积缩小了 25%，从 0.033 µm²降至 0.0249 µm²，等容量下的宏单元密度则提升至 16.0 Mb/mm²。读取速度在等容量下从 6 ns 降至 5.5 ns，而双端口访问和交错读取功能则完全是新增的。

尽管三星晶圆代工厂今年也发布了基于 8LPP 制程的嵌入式 MRAM（eMRAM）研究成果，但台积电的方案显得更有前景。它不仅瞄准了所需的关键特性，性能表现优异，而且基于成本更低的 N16 制程节点。

![](https://substackcdn.com/image/fetch/$s_!09sO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F87ac2737-caab-46a2-8b88-417507719b1a_2880x1620.png)

*台积电 N16 MRAM Flash-Plus 技术路线图。来源：台积电，ISSCC 2026*

台积电已在规划下一代的“Flash-Plus”变体，其存储单元面积将再缩小 25%，耐久性则提升 100 倍。

## Optical Networking

多家主流光学器件供应商的论文聚焦于光学互连技术，该技术将负责在下一代 AI 加速器之间，以及数据中心内部与数据中心之间传输数据。

## Nvidia DWDM - Paper 23.1

光学信号格式的选择将影响纵向扩展（scale-up）共封装光学（CPO）产品的上市时间表。英伟达正在加速生产其 COUPE 光学引擎，该引擎支持每通道 200G PAM4，旨在短期内用于横向扩展（scale-out）交换。

![](https://substackcdn.com/image/fetch/$s_!gqo1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa1a30ce9-0d17-45f9-9e83-026ba5f0a876_2880x1620.jpeg)

*英伟达 DWDM 架构概览。来源：英伟达，ISSCC 2026*

然而，在 ISSCC 上，英伟达提出了使用每波长 32 Gb/s 的方案，并通过 DWDM 复用 8 个波长。第 9 个波长以半速率（即 16 Gb/s）用于时钟转发。

时钟转发意味着可以通过移除时钟数据恢复（CDR）电路以及其他相关电路，使串行器/解串器设计在一定程度上得以简化，从而提升能效和芯片海岸线（shoreline）效率。

早在今年三月，恰在 OFC 2026 之前，[光学计算互连多源协议（OCI MSA）宣布成立](https://www.businesswire.com/news/home/20260312254951/en/Optical-Scale-up-Consortium-Established-to-Create-an-Open-Specification-for-AI-Infrastructure-Led-by-Founding-Members-AMD-Broadcom-Meta-Microsoft-NVIDIA-and-OpenAI)，该协议将专注于 200 Gb/s 双向链路，其发送和接收均采用 4 个 50G NRZ 波长，并通过同一根光纤双向传输。是不是有人提到了 OCS？

![](https://substackcdn.com/image/fetch/$s_!Eh4Q!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F62c2c764-5aab-4981-aedc-1e6ba3864cf4_2869x1869.jpeg)

*OCI MSA 光学链路规格。来源：[OCI MSA](https://oci-msa.org/)*

有趣的是，光学计算互连多源协议（OCI MSA）并未使用额外的波长进行时钟转发。这似乎表明，将所有波长保留用于实际数据传输是其优先考虑的事项。

英伟达已发表的关于纵向扩展（scale-up）共封装光学（CPO）的研究大多集中在密集波分复用（DWDM）技术上。然而，当今的 CPO 光学引擎主要围绕 200G PAM4 DR 光学构建，这更适合横向扩展（scale-out）网络。OCI MSA 围绕 DWDM 制定纵向扩展光学标准，正好化解了这一矛盾。现在情况已很明确：英伟达及其他厂商将主要采用 DWDM 进行纵向扩展，而采用 DR 光学进行横向扩展。

OCI MSA 还展示了不同的实现方案：一种是板载光学（OBO），另一种是通过基板集成在专用集成电路（ASIC）封装上的 CPO 版本，以及第三种将光学引擎直接集成在硅中介层上的版本。中间图（b）所示的实现方案，在未来几年内将是用于纵向与横向扩展 CPO 的最常见方案。不过，该方案仍需要某种形式的串行化链路来穿过 ASIC 基板，并且两端仍需要某种形式的串行器/解串器（SerDes）。例如，UCIe-S 协议就可以用于此类传输。

![](https://substackcdn.com/image/fetch/$s_!r0uo!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F02eb01f6-1c42-4388-b07d-744346a1d768_2262x1962.jpeg)

*光学引擎集成层级（板载光学、基板 CPO、中介层 CPO）。来源：[OCI MSA](https://oci-msa.org/)*

实现共封装光学（CPO）的“终极挑战”，在于将光学引擎直接集成到硅中介层上，并如上图（c）所示，通过并行化的裸片到裸片（D2D）连接与专用集成电路（ASIC）相连。这有望显著提升海岸线带宽密度，实现更高的端口数（radix），并改善能效。因此，这种实现方案能以其他方案无法企及的方式释放 CPO 的优势。但要实现它，仍需数年时间，并依赖于先进封装技术的进一步发展。

## Marvell Coherent-Lite Transceiver - Paper 23.2

![](https://substackcdn.com/image/fetch/$s_!B76F!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc24a930f-d8f1-4622-96e6-9a39a7388ea5_2880x1620.jpeg)

*直接检测、精简相干与相干光模块对比。来源：Marvell，ISSCC 2026*

Marvell 展示了一款用于精简相干（Coherent-Lite）应用的 800G 光模块。传统光模块的传输距离有限，通常小于 10 公里。相干光模块则支持远得多的距离，但其设计复杂、功耗更高且成本更昂贵。Marvell 的精简相干光模块旨在功耗、成本和传输距离之间取得平衡，这对于链路跨度最多数十公里的大型数据中心园区而言堪称完美。

![](https://substackcdn.com/image/fetch/$s_!1xhk!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9995a322-bad8-4a3c-97e1-b84fde0aa424_2880x1620.jpeg)

*相干与精简相干光模块的光波段对比。来源：Marvell，ISSCC 2026*

相干光模块主要使用 C 波段波长，正是看中其低衰减特性。然而，使用相干传输的长距离链路通常色散非常高，需要大量的数字信号处理器（DSP）处理。对于建筑物之间仅相隔数十公里的数据中心园区而言，传统相干光学的超长传输距离往往显得大材小用。

精简相干光模块则转而使用 O 波段波长，该波段在数据中心园区相对较短的距离上色散近乎为零。这使得所需的 DSP 处理降至最低，从而节省了功耗并降低了延迟。

![](https://substackcdn.com/image/fetch/$s_!oACP!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0faa6bfc-c1c4-44bc-b8c8-c3b14f466c32_2880x1620.jpeg)

*Marvell 精简相干光模块架构。来源：Marvell，ISSCC 2026*

精简相干光模块是一种基于数字信号处理器（DSP）的可插拔模块，包含两个 400G 通道。每个 400G 通道运行双偏振正交幅度调制（Dual-Polarization Quadrature Amplitude Modulation, DP-QAM），并由 X 和 Y 两个并行的调制流组成。

![](https://substackcdn.com/image/fetch/$s_!qDgr!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcc181023-63b7-4e6e-8769-eb69fdc1ca81_682x375.jpeg)

*Marvell 精简相干光模块实测链路性能。来源：Marvell，ISSCC 2026*

本次演示的核心，在于展示其他几种专为园区应用优化的通道带宽扩展方法。

高阶调制结合使用 X 和 Y 轴的双偏振技术，实现了 400G 的通道带宽。如上图所示，每个通道有 8 比特，总共构成 32 个星座点。这 8 比特乘以 62.5 GBd 的信号速率，总计约 400G 的总带宽。

这种调制方案对业界来说并不陌生，但如今正被引入数据中心园区，用于那些距离较短的链路。

![](https://substackcdn.com/image/fetch/$s_!jtsE!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F79b51c03-3812-498e-8f41-b9465e2c8164_2880x1620.jpeg)

Marvell 精简相干光模块性能与先前相干收发器的对比。来源：Marvell，ISSCC 2026

Marvell 的方案显著降低了功耗，在不包含硅光部分的情况下，功耗仅为 3.72 皮焦耳/比特，仅为其他全功能相干收发器的一半。其测量是在 40 公里光纤长度上进行的，延迟低于 300 纳秒。

## Broadcom 6.4T Optical Engine - Paper 23.4

![](https://substackcdn.com/image/fetch/$s_!3q6a!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F47fde40b-9947-4fac-b9db-2ac5e7592aec_2880x1620.jpeg)

*博通 Tomahawk 5 51.2T CPO 光学引擎芯片显微照片与封装。来源：博通，ISSCC 2026*

博通展示了其 6.4T MZM（马赫-曾德尔调制器）光学引擎的进展。该光学引擎由 64 条通道组成，每条通道速率约 100G，采用 PAM4（四电平脉冲幅度调制）调制。这些光学引擎在 Tomahawk 5 51.2T CPO（共封装光学）系统中进行了测试。一个 CPO 封装包含八个 6.4T 光学引擎，每个引擎均由一个光子集成电路和一个电子集成电路组成，采用台积电 N7 工艺制造。

![](https://substackcdn.com/image/fetch/$s_!vT7z!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F021fa5c2-1bfd-455b-84cc-730cabf6362c_2880x1620.jpeg)

*博通 Tomahawk 5 CPO 光学引擎封装。来源：博通，Hot Chips 2024*

英伟达使用 COUPE 方案，而博通则为此光学引擎采用了扇出型晶圆级封装方法。[博通未来将转向 COUPE 方案](https://newsletter.semianalysis.com/i/178153689/tsmc-coupe-is-emerging-as-the-integration-option-of-choice)，但像此光学引擎这样的旧一代产品仍在使用其他供应链合作伙伴。以下是其演示中取得的有前景的结果：

![](https://substackcdn.com/image/fetch/$s_!0Dva!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F179ad311-5e3a-40c0-8fb6-f809fb2f8342_2880x1620.jpeg)

*博通 6.4T 光学引擎发送端性能。来源：博通，ISSCC 2026*

## High-Speed Electrical Interconnects

随着多裸片设计成为常态，裸片间互连已成为关键瓶颈。各大晶圆代工厂和芯片设计公司提出了多种方案，力求在有机基板和先进封装技术上同时提升带宽密度与能效。

## Intel UCIe-S - Paper 8.1

![](https://substackcdn.com/image/fetch/$s_!Ejnk!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc7669995-eecb-4441-843f-bfaa0348e31e_2494x1403.jpeg)

*英特尔 UCIe-S 裸片到裸片互连接口芯片显微照片与概览。来源：英特尔，ISSCC 2026*

英特尔展示了其符合 UCIe-S（通用芯粒互连-标准版）标准的裸片到裸片（D2D）接口。该接口在 UCIe-S 协议下，通过 16 个通道可实现高达 48 Gb/s/通道的速率；若采用定制协议，速率更可提升至 56 Gb/s/通道。它能在标准有机封装上工作，传输距离最远可达 30 毫米。值得注意的是，该接口采用了英特尔的 22 纳米制程节点制造。

![](https://substackcdn.com/image/fetch/$s_!J1Ms!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fccbdc885-60a6-4372-b840-6e6525a06002_2494x1403.jpeg)

*英特尔 UCIe-S 与其他裸片到裸片互连接口对比。来源：英特尔，ISSCC 2026*

在 2025 年超大规模集成电路（VLSI）研讨会上，Cadence 展示了其基于 N3E 制程的 UCIe-S 裸片到裸片互连技术。尽管英特尔在制程节点上处于劣势，但其接口在数据速率、通道长度和单位边缘带宽方面均超越了 Cadence 的方案，仅在能效方面有所不及。

![](https://substackcdn.com/image/fetch/$s_!NLKz!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Febe7307b-d87f-43d1-b7df-4b6cfbc8211a_2786x1606.jpeg)

*英特尔 Diamond Rapids 多裸片架构概览。来源：HEPiX via @InstLatX64*

英特尔此次展示的互连技术，很可能是为其 Diamond Rapids 至强（Xeon）CPU 设计的原型。与这款 22 纳米测试芯片相比，若基于英特尔 3 制程进行设计，其效率应有显著提升，并有望取代 Granite Rapids 上采用的 EMIB 等先进封装方案。正如我们[在《数据中心CPU格局纵览》一文中所述](https://newsletter.semianalysis.com/i/187132686/intel-diamond-rapids-architecture-changes)，Diamond Rapids 由两颗 IMH 裸片和四颗 CBB 裸片构成。考虑到每颗 CBB 裸片与两颗 IMH 裸片之间均存在长距离走线，我们认为该互连技术是实现在标准封装基板上连接各裸片的可行方案，从而无需使用 EMIB。

## TSMC Active LSI - Paper 8.2

![](https://substackcdn.com/image/fetch/$s_!kR_h!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F903517c9-6ff3-4ac5-9d4a-c0130cb9cbea_2880x1620.jpeg)

*台积电（TSMC）无源与有源本地硅互连（aLSI）对比。来源：台积电，ISSCC 2026*

台积电（TSMC）的先进封装部门展示了其有源本地硅互连（Active Local Silicon Interconnect, aLSI）方案。与标准的 CoWoS-L 或 EMIB 不同，aLSI 改善了信号完整性，并降低了顶层裸片上物理层（PHY）和串行器/解串器（SerDes）的复杂度。

![](https://substackcdn.com/image/fetch/$s_!Gjwp!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa8f473a9-3f0e-4b7a-b717-2bc9999adae6_2880x1620.jpeg)

*台积电（TSMC）有源本地硅互连（aLSI）裸片到裸片链路概览。来源：台积电，ISSCC 2026*

台积电展示的器件采用了 32 Gb/s、类似 UCIe 的收发器。由于 aLSI 改善了信号完整性，收发器的面积得以减小，凸点间距也能从 45 微米缩减至 38.8 微米。更紧密的间距结合转向曼哈顿网格（Manhattan grid）的布局，使得物理层（PHY）的深度从 1043 微米降至 850 微米，从而节省了空间。设计者可将这些空间重新分配给计算、内存或输入/输出（IO）单元，或用于缩小裸片尺寸。需要指出的是，该收发器只是“类似 UCIe”，并非真正的 UCIe 标准实现，因为 UCIe 标准强制要求六边形凸点排布，而非此处使用的曼哈顿网格。

随着设计者为下一代 AI 加速器竭力榨取每一寸裸片空间，转向 aLSI 技术已不可避免。

aLSI 的‘有源’部分，体现在用有源晶体管构成的边沿触发收发器（Edge-Triggered Transceiver, ETT）电路，取代了桥接裸片中的无源长距离金属通道，从而在更长距离上维持信号完整性。这也降低了对顶层裸片发送/接收端口信号驱动能力的要求。aLSI 内部的 ETT 电路仅额外增加 0.07 皮焦/比特（pJ/b）的能耗，最大限度地缓解了在堆叠裸片中加入有源电路可能引发的散热担忧。通过将信号调理电路移至桥接裸片，顶层裸片的发送/接收物理层（PHY）面积得以减小，这得益于可以使用更小的预驱动器和时钟缓冲器，并且接收端不再需要信号放大。

边沿触发收发器（ETT）集成了驱动器、交流耦合电容（Cac）、一个兼具负反馈与正反馈的放大器以及输出级。信号通过 Cac 时，会在其转换边沿引入峰值，随后由双环路放大器拾取，这便是其‘边沿触发’名称的由来。该放大器利用正负反馈环路来稳定电压水平。在此设计中，针对 1.7 毫米的通道长度，Cac 设定为 180 fF，裸片 A 和裸片 B 上的电阻分别为 2kΩ和 3kΩ。

![](https://substackcdn.com/image/fetch/$s_!wpmP!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc151958f-7fdb-4903-b06a-38a0eace27d5_2667x1500.jpeg)

*台积电（TSMC）集成 eDTC 的 CoWoS-L 供电方案。来源：台积电*

这些 aLSI 桥接芯片还能在前端集成嵌入式深沟槽电容（eDTC），以改善对物理层（PHY）和裸片到裸片（D2D）控制器的供电。aLSI 配合 eDTC 技术，不仅没有因为桥接芯片的存在而损害电源配送网络，反而能同时优化沿 D2D 接口的供电与信号布线。

![](https://substackcdn.com/image/fetch/$s_!Yp1W!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7d837ed3-5395-4e1a-b579-c95f1d9497cc_2880x1620.jpeg)

*台积电（TSMC）有源本地硅互连（aLSI）布线能力与横截面。来源：台积电，ISSCC 2026*

仅需 388 微米的互连接口宽度，即可容纳 64 条发送（TX）和 64 条接收（RX）数据通道，总面积仅为 0.330 平方毫米。信号布线仅需占用最顶部的两层金属层，其余金属层可用于前端电路。

![](https://substackcdn.com/image/fetch/$s_!7zt3!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa2747466-8e4c-4447-ad94-6c2e8b71ea4a_2880x1620.jpeg)

*台积电（TSMC）有源本地硅互连（aLSI）在已知合格裸片（KGD）与已知合格封装（KGP）阶段的舒姆图。来源：台积电，ISSCC 2026*

台积电介绍了有源本地硅互连（aLSI）的多阶段测试方案。首先是已知合格裸片（KGD）阶段，仅测试 LSI 裸片本身以进行裸片验证。其次是已知合格堆叠（KGS）阶段，此时系统级芯片（SoC）已通过 LSI 连接，以测试堆叠功能。最后是已知合格封装（KGP）阶段，对完整组装体进行全面测试，以验证其功能、性能和可靠性。

他们展示了在 KGD 和 KGP 阶段的舒姆图。两张图均显示，该互连技术在 0.75V 电压下达到了 32 Gb/s 的速度，在 0.95V 电压下则达到了 38.4 Gb/s。

![](https://substackcdn.com/image/fetch/$s_!jY_b!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff44de7d8-9b9f-4086-a305-6c16677e9895_2880x1620.jpeg)

*台积电（TSMC）有源本地硅互连（aLSI）芯片显微照片与功耗分解。来源：台积电，ISSCC 2026*

该封装体展示了两颗系统级芯片（SoC）裸片和两颗输入/输出（IO）裸片。有趣的是，这个测试载具的设计似乎与 AMD 的 MI450 图形处理器（GPU）相符，包含两颗相互连接的基础裸片、12 个 HBM4 堆栈以及两颗集成有源本地硅互连（aLSI）的 IO 裸片。其特点是，并非每个 HBM4 堆栈都拥有独立的 aLSI，而是每两个共享一个。

在功耗方面，在 0.75V 电压下，总功耗仅为 0.36 皮焦耳/比特（pJ/b），其中有源本地硅互连（aLSI）中的嵌入式硅桥（ETT）部分仅消耗 0.07 pJ/b。下图是与其他裸片到裸片（D2D）解决方案的对比。

![](https://substackcdn.com/image/fetch/$s_!GHcE!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd194a9ff-d0ee-4e74-98a9-1f426f98205c_2880x1620.jpeg)

台积电（TSMC）有源本地硅互连（aLSI）与其他裸片间互连技术的对比。来源：台积电，ISSCC 2026

## Microsoft D2D Interconnect - Paper 8.3

![](https://substackcdn.com/image/fetch/$s_!2aNW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7d6415fa-2e4a-4565-af88-6db7a3c95dbc_1309x1267.jpeg)

*微软（Microsoft）裸片到裸片（D2D）测试载具布局与布线。来源：微软，ISSCC 2026*

微软也详细介绍了其裸片到裸片（D2D）互连技术。其测试载具包含两颗裸片和两对用于互连的 D2D 节点。为了模拟时钟门控和串扰效应，设计中还包含了完整的供电网络和布线模型。

![](https://substackcdn.com/image/fetch/$s_!3kjp!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1bc8b78e-9738-4558-a155-efbddcf0dbbe_472x677.jpeg)

*微软（Microsoft）裸片到裸片（D2D）互连芯片显微照片。来源：微软，ISSCC 2026*

其测试芯片上的互连模块占据了 532 微米的芯片边缘长度，深度为 1350 微米。该测试载具采用台积电（TSMC）的 N3P 制程节点制造，互连模块在两种数据速率下进行了测试：0.65V 电压下为 20 Gb/s，0.75V 电压下为 24 Gb/s。

![](https://substackcdn.com/image/fetch/$s_!i2ue!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fffed7179-ed8f-414b-8aeb-2ff273f25784_2880x1620.jpeg)

*微软（Microsoft）裸片到裸片（D2D）功耗分解。来源：微软，ISSCC 2026*

微软（Microsoft）报告了两个功耗数据：一个包含模拟和数字系统的总功耗，另一个则仅包含模拟功耗。后者是大多数裸片间互连（die-to-die interconnects）通常报告的指标。在 24 Gb/s 速率下，系统总功耗为 0.33 皮焦耳/比特（pJ/b），模拟功耗为 0.226 pJ/b；而在 20 Gb/s 速率下，系统总功耗为 0.25 pJ/b，模拟功耗为 0.17 pJ/b。其静态状态下的功耗为 0.05 pJ/b。

![](https://substackcdn.com/image/fetch/$s_!qn-K!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F65fefab9-0819-4c73-8c7b-39b778230934_2880x1620.jpeg)

*微软（Microsoft）裸片到裸片（D2D）互连与其他裸片间互连技术的对比。来源：微软，ISSCC 2026*

与台积电（TSMC）为其 Active LSI 所做的一样，微软也将自家的互连技术与同一批早期研究进行了对比。

正如我们[在之前的文章中所解释的](https://newsletter.semianalysis.com/i/187132686/microsoft-cobalt-200)，微软的 Cobalt 200 CPU（中央处理器）采用了两个通过定制高带宽（high-bandwidth）互连连接的计算芯粒（compute chiplets）。我们认为，本次演讲详细阐述的正是这一具体的互连技术。

## Processors

从移动端的小型 CPU（中央处理器）到大型 AI（人工智能）加速器，本届 ISSCC（国际固态电路会议）首次披露了来自联发科（MediaTek）、英特尔（Intel）、AMD、Rebellions 和微软（Microsoft）的多款产品的架构细节。其中许多甚至提供了芯片裸片（die）照片。

## MediaTek Dimensity 9500 - Paper 10.2

联发科每年都会展示其旗舰移动 CPU（中央处理器）的不同方面。今年也不例外，其移动 CPU 演示的重点在于性能提升与热管理。

![](https://substackcdn.com/image/fetch/$s_!G7l7!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F29b40070-6df4-435c-9621-f7837da8602f_2880x1620.jpeg)

*联发科天玑 9500 C1 Ultra 核心工艺优化。来源：联发科，ISSCC 2026*

台积电为其 N3E 和 N3P 工艺提供了两种不同的接触栅极间距（Contacted Gate Pitch, CGP）选项：48 纳米和 54 纳米。在大多数芯片中，都采用了更窄的 48 纳米 CGP，因为这能带来更小的单元尺寸和更大的芯片面积缩减。然而，由于关键尺寸更小，它也会带来漏电、布线和制造方面的问题。

联发科在其天玑 9500 的 C1 Ultra 高性能核心上采用了更大的 54 纳米 CGP，以提升能效。这使其能在更低的热量惩罚下达到更高性能，具体表现为同漏电下性能提升 4.6%，或同性能下功耗降低 3%。

联发科论文的其余部分重点阐述了如何利用未使用的老化余量和减少热过冲，来实现动态性能优化。总体而言，他们成功将提升时钟频率从 4.21 GHz 提高到了 4.4 GHz。如果您对这些优化技术感兴趣，我们推荐您查阅这篇论文：[10.2 一款基于3nm-Plus工艺的移动CPU中的动态性能增强技术](https://ieeexplore.ieee.org/document/11409197)。

## Intel 18A-on-Intel 3 Hybrid Bonding - Paper 10.6

![](https://substackcdn.com/image/fetch/$s_!L-SD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffc1e02d7-2ca4-4129-9200-e99084fa4cfc_1792x1265.jpeg)

*英特尔 M3DProc 18A 与英特尔 3 芯片布局规划图。来源：英特尔，ISSCC 2026*

英特尔首次披露了其采用混合键合技术的芯片 M3DProc。该芯片由一个英特尔 3 工艺的底层芯片和一个 18A 工艺的顶层芯片构成。每个芯片分别包含 56 个网格瓦片（mesh tile）、核心和深度神经网络（DNN）加速器瓦片。两个芯片通过间距为 9 微米的 Foveros Direct 混合键合技术互联。

![](https://substackcdn.com/image/fetch/$s_!Ysv3!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F636479de-4917-48f9-b513-7c57fe81968e_2494x1403.jpeg)

*英特尔 M3DProc 3D 网格架构。来源：英特尔，ISSCC 2026*

这些网格单元以 14×4×2 的 3D 网格形式排列，SRAM（静态随机存取存储器）由上下两片芯片共享。

![](https://substackcdn.com/image/fetch/$s_!6vZe!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc2a08665-501d-4c3b-a54a-0bfae0dc5258_2412x910.jpeg)

*英特尔 M3DProc 2D 与 3D 架构的吞吐量及能效对比。来源：英特尔，ISSCC 2026*

英特尔发现，3D 网格架构能降低延迟，并将吞吐量提升近 40%。他们还测试了数据传输的能效，其中 2D 架构的数据传输发生在底部芯片的 56 个网格单元内，而 3D 架构则跨越两个芯片上的 28 个相邻网格单元。结果显示，其混合键合互连（Hybrid Bonding Interconnect, HBI）对能效的影响微乎其微。

![](https://substackcdn.com/image/fetch/$s_!aWNv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4877bf3c-30c1-4278-b85e-65ddbc343f1b_1362x1400.jpeg)

英特尔 M3DProc 单元键合布局规划图。来源：英特尔，ISSCC 2026

每个单元拥有 552 个焊盘，其中略少于一半用于数据传输，略少于四分之一用于供电。

在封装方面，M3DProc 与 Clearwater Forest (CWF) 类似。CWF 采用英特尔 3 工艺的基础芯片，通过 9 微米间距的 Foveros Direct 技术与 18A 工艺的计算芯片相连。

M3DProc 实现了 875 GB/s 的 3D 带宽，而每个 CWF 计算芯片仅能实现 210 GB/s。这款芯片的三维片上网络（3D NoC）拥有显著更高的带宽密度。具体而言，CWF 使用 Foveros Direct 技术，通过每个顶部芯片上 6 个集群（每个集群提供 35GB/s 的连接带宽）实现了 CPU 核心集群的 L2 缓存与基础芯片 L3 缓存的解耦，每个顶部芯片总带宽为 210GB/s。相比之下，M3DProc 的 875GB/s 3D 带宽是通过 56 个垂直单元连接聚合实现的，每个连接在远小于（CWF 方案中）单个连接的占位面积上提供了 15.6GB/s 的带宽。

## AMD MI355X - Paper 2.1

![](https://substackcdn.com/image/fetch/$s_!o-hR!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F62444551-a7bc-4619-ae99-74199208f209_2880x1620.jpeg)

*AMD MI300X 与 MI355X XCD 对比图。来源：AMD, ISSCC 2026*

AMD 介绍了其 MI355X GPU。在会议演讲中，AMD 通常只是复述先前的公告，仅引入一两条新信息。但这份论文在这方面要好得多，它详细解释了 MI355X 的 XCD（核心计算芯片）和 IOD（输入输出芯片）相较于 MI300X 是如何改进的。

![](https://substackcdn.com/image/fetch/$s_!zxX3!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb0f76dac-c592-4dd4-ab6d-0d1054fc2f8b_2880x1620.jpeg)

*AMD MI300X 与 MI355X XCD 面积效率对比。来源：AMD, ISSCC 2026*

AMD 详细说明了他们如何在保持总面积不变、计算单元（CU）数量大体相似的情况下，将每个 CU 的矩阵吞吐量提升了一倍。首先，当然是从 N5（5 纳米）制程节点转向 N3P（3 纳米增强版）节点；这带来了晶体管密度提升的主要部分。N3P 提供的额外两层金属层改善了布线能力，从而提高了单元利用率。与之前在 N5 节点上的做法一样，AMD 设计了自家的标准单元，以针对其高性能计算（HPC）应用场景进行优化。

他们还采用了更密集的布局算法，其思路类似于 EPYC Bergamo CPU 中使用的 Zen 4c 核心比 EPYC Genoa CPU 中的 Zen 4 核心更紧凑的设计。

在使用 FP16、FP8、MXFP4 等多种不同数据格式执行相同计算时，有两种方法。第一种是使用共享硬件，所有格式都经过相同的电路。然而，这会带来功耗代价，因为针对每种格式的优化很少。第二种选择是每种数据格式使用完全不同的电路组进行计算。但这会占用大量额外面积。当然，最优方案介于两者之间——这也正是 AMD 优化工作的一个重要焦点。

![](https://substackcdn.com/image/fetch/$s_!tuPF!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2c313972-5315-4d1e-aa02-be6f1ffad996_2880x1620.jpeg)

*AMD MI355X XCD 频率与能效提升。来源：AMD, ISSCC 2026*

作为晶体管性能得到改进的下一代制程节点，N3P 本身就能带来性能提升。然而，在不依赖制程节点改进的情况下，AMD 就已设法在同等功耗下将频率提升了 5%。此外，他们还设计了多种具有不同功耗和性能特性的触发器变体，并根据使用场景和架构需求，将其部署在芯片的不同区域。

![](https://substackcdn.com/image/fetch/$s_!Yxoy!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8b8604cb-0c0d-404c-942a-7b8fe000edd8_2880x1620.jpeg)

*AMD MI355X IOD 合并带来的能效提升。来源：AMD, ISSCC 2026*

MI300X 配备了 4 个 IOD（输入输出裸片）。MI355X 则将其减少至两个。通过这种方式，AMD 节省了用于裸片间互连的面积。更大的单片式裸片改善了延迟，并减少了串行器/解串器（SerDes）及相关的协议转换开销。此外，通过增加互连宽度，高带宽内存（HBM）的效率也得到了提升。由此节省的功耗可以重新分配给计算裸片，以提高性能。

![](https://substackcdn.com/image/fetch/$s_!rkb_!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faee3a34c-c53c-4661-ac14-8907a7764064_2880x1620.jpeg)

*AMD MI355X IOD 互连功耗优化。来源：AMD, ISSCC 2026*

由于这是一个大型裸片，芯片上任意两点间存在多种布线路径可选，因此 AMD 必须投入大量工作来优化导线与互连。通过对导线进行定制化工程设计，AMD 成功将互连功耗降低了约 20%。

## Rebellions Rebel100 - Paper 2.2

Rebellions 是一家专注于 AI 加速器（Artificial Intelligence Accelerator）的韩国初创公司。在 ISSCC（国际固态电路会议）上，他们首次公布了其新型加速器 Rebel100 的架构细节。与其他通常在台积电制造的加速器不同，Rebellions 选择了三星代工厂的 SF4X 制程节点。鉴于英伟达、AMD、博通等公司占据了台积电的大部分产能，这一选择为 Rebellions 提供了更大的灵活性。

![](https://substackcdn.com/image/fetch/$s_!HCo6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff2ea04c2-71cf-4065-98b1-606182921d24_1068x801.jpeg)

*Rebellions Rebel-Quad（现称 Rebel100）在 Hot Chips 2025 上的概要。来源：Rebellions via [ServeTheHome](https://www.servethehome.com/rebellions-rebel-quad-ucie-and-144gb-hbm3e-accelerator-at-hot-chips-2025/)*

在 Hot Chips 2025 上，Rebellions 演示了该芯片运行 Llama 3.3 70B 模型。从 Hot Chips 到 ISSCC，其规格参数保持不变。一个关键点在于使用了 三星 的 I-CubeS 中介层技术。虽然 Hot Chips 的幻灯片提到了使用 台积电 的 CoWoS-S，但我们已经澄清这是幻灯片上的一个错误，实际上一贯使用的是 I-CubeS。

我们最近提到过，[CoWoS-S的产能限制已有所缓解](https://newsletter.semianalysis.com/i/190110359/cowos-tight-but-easing)。尽管如此，三星可能提供了大幅折扣，将其 I-CubeS 先进封装技术与前端制程捆绑销售——这使得这家初创公司无需再寻找并验证另一家独立的先进封装供应商。三星提供其 HBM（高带宽内存）也可能以必须使用 I-CubeS 为前提条件。

I-CubeS 尚未在任何主流的 AI 加速器 中得到采用，这可能是 三星 试图打入该市场的尝试。目前仅有 5 家已确认的 I-CubeS 用户：eSilicon、百度、英伟达、Rebellions 和 Preferred Networks。

第一家是 eSilicon 基于 三星 14LPP 制程并搭载 HBM2 的网络专用集成电路。百度的昆仑 1 加速器类似，使用了 三星 的 14LPP 工艺和 2 颗 HBM2 堆栈。在 2023 年 CoWoS-S 产能非常紧张时，英伟达 将少量 H200 的生产外包给了 I-CubeS。接着是 Rebel100，最后是 Preferred Networks 计划在 SF2 制程节点上开发的加速器。

![](https://substackcdn.com/image/fetch/$s_!Wj1c!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F91f29194-e088-40ef-b134-ac45449d21ae_2880x1620.jpeg)

*Rebellions Rebel100 多芯片架构。来源：Rebellions，ISSCC 2026*

Rebel100 采用了 4 颗计算芯片和 4 个 HBM3E 堆栈。每颗芯片配备了 3 个 UCIe-A（通用芯粒互连扩展-A）接口，但实际每颗芯片仅启用了其中两个，运行速率为 16 Gb/s。

![](https://substackcdn.com/image/fetch/$s_!Rt0c!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff9b5a17f-feb0-4c70-b528-cae2a38c11f3_2880x1620.jpeg)

*Rebellions Rebel100 封装级模块化设计。来源：Rebellions，ISSCC 2026*

Rebellions 宣称该设计在封装级别具备可重构性，能够额外添加输入输出或内存芯粒，并与以太网集成以实现纵向扩展（scale-up）。剩余的 UCIe-A 接口将用于此目的。

Rebellions 表示，输入输出芯粒预计将在 2026 年第一季度完成流片。但并未提供内存芯粒的具体时间表。

![](https://substackcdn.com/image/fetch/$s_!kIab!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcbab43a4-26b7-4011-bfeb-ea01c4902a56_2880x1620.png)

*Rebellions Rebel100 总结与路线图。来源：Rebellions，ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!NxmQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F759c00f2-e242-404b-a841-5e4458a75e4c_2880x1620.png)

Rebellions Rebel100 为 HBM3E 供电质量集成的硅电容器。来源：Rebellions，ISSCC 2026

此外，他们在每个 HBM3E 堆栈旁都集成了硅电容器，以改善 HBM3E 及关键控制模块的供电质量。

## Microsoft Maia 200 - Paper 17.4

微软详细介绍了其 Maia 200 AI 加速器。这篇论文与其说是一篇研究论文，不如说更像一份白皮书，仅包含一张图片和一份将其与 Maia 100 进行比较的规格表。考虑到 Maia 200 的许多性能宣称（例如其每平方毫米浮点运算性能（FLOPS/mm²）和每瓦浮点运算性能（FLOPS/W））本身存疑，这种做法倒也合乎情理。

Maia 100 设计于 GPT 时代之前，而 Maia 200 则是为当前模型时代、特别是为推理任务而设计的。今年早些时候，基于 Maia 200 芯片的计算节点已在 Azure 云平台上普遍可用。

![](https://substackcdn.com/image/fetch/$s_!3VIK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0c381cad-9332-483a-9fd7-8de08cd7d90a_2880x1620.jpeg)

*微软 Maia 200 规格总结。来源：微软，ISSCC 2026*

Maia 200 是光罩尺寸单芯片设计的最后坚守者。所有配备高带宽内存（HBM）的主要训练和推理加速器都已转向多芯片设计，每个封装内包含 2、4 甚至 8 个计算裸片。芯片的每一平方毫米都为实现单一目标而做了极致优化。与英伟达或 AMD 的 GPU 不同，它没有为媒体或向量运算保留的遗留硬件。微软在台积电（TSMC）的 N3P 工艺上将光罩尺寸单芯片方法推向了极限，集成了超过 10 PFLOPs 的 FP4 算力、6 个 HBM3E 堆栈以及 28 条 400 Gb/s 全双工 D2D 链路。

![](https://substackcdn.com/image/fetch/$s_!oV7g!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F98820b64-6a10-4132-b24a-a2122f7417ad_2880x1620.jpeg)

*微软 Maia 200 封装横截面图。来源：微软，ISSCC 2026*

在封装层面，Maia 200 非常标准，模仿了 H100 的设计，采用一个 CoWoS-S 中介层来承载 1 个主裸片和 6 个 HBM3E 堆栈。

![](https://substackcdn.com/image/fetch/$s_!1q24!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4949a336-f267-4f4c-b813-1f6af0d7f629_506x541.jpeg)

*微软 Maia 200 裸片布局图。来源：微软，ISSCC 2026*

芯片的长边各覆盖了 3 个 HBM3E 物理层接口（PHY），而短边则各有 14 条通道，共同组成 28 条速率为 400 Gb/s 的裸片到裸片（D2D）互连接口。芯片中央集成了 272 MB 的 SRAM，其中包括 80 MB 的 TSRAM（作为 L1 缓存）和 192 MB 的 CSRAM（作为 L2 缓存）。

![](https://substackcdn.com/image/fetch/$s_!Wj4l!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F62240549-cf4a-4472-8294-7b7b2bca21fa_2880x1620.jpeg)

*微软 Maia 200 纵向扩展网络与输入/输出接口。来源：微软，ISSCC 2026*

Maia 200 配备两种不同类型的互连接口：一种是用于连接同一节点内其他芯片的固定链路，另一种是用于连接芯片与交换机的交换链路。具体而言，21 条链路被配置为固定链路，分别连接至节点内的其他芯片（例如，连接到其他三个芯片，各使用 7 条）；剩余的 7 条链路则被配置为交换链路，用于连接机架内的四个交换机之一。

我们将为机构订阅用户发布一份关于 Maia 200 的深度分析报告，涵盖其微架构和网络拓扑结构。

## Other Highlight

## Samsung SF2 Temperature Sensor - Paper 21.5

![](https://substackcdn.com/image/fetch/$s_!S6Ri!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5ae89ead-c1e7-409c-912f-bf86d659e2c0_2880x1620.png)

*传统温度传感器的权衡取舍。来源：三星，ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!2aBs!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F66a71ead-cde8-4e94-9ea5-ddf5caebf775_2880x1620.png)

*三星 SF2 基于金属层电阻的温度传感器权衡取舍。来源：三星，ISSCC 2026*

三星在 SF2 工艺上展示了一款紧凑型温度传感器，它用后端金属层（BEOL， Back-End-of-Line）电阻取代了传统的双极结型晶体管方案。这可能不如下一代内存或处理器那样引人注目，但对于芯片的正常工作却至关重要。

该金属电阻的方块电阻比等效布线金属高出 518 倍，因此实现相同电阻值所需面积仅为后者的约 1%。由于它位于上层金属层中，为下方任何电路都留出了充足空间，并消除了前端工艺的面积开销。尽管其分辨率较低，但其带来的优势足以弥补这一不足。

![](https://substackcdn.com/image/fetch/$s_!J1CI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F22987230-7e2a-4317-b244-f4e76930494b_2880x1620.png)

*三星 SF2 温度传感器的堆叠式实现。来源：三星，ISSCC 2026*

该传感器采用全堆叠的电容-电阻-电路结构，总面积仅为 625 μm²。作为一个经过特性表征的工艺设计套件（PDK， Process Design Kit）元件，其行为由晶圆代工厂建模并验证。这种设计更适用于需要严格控制工艺偏差的大规模生产。即使在单个芯片上，热点附近也可能使用数千个此类传感器。

如前所述，金属层电阻的电阻温度系数（TCR）较低，仅为布线金属的 0.2 倍——这限制了传感分辨率。三星通过增大基础电阻值来补偿这一不足。然而，这会导致 RC 时间常数增大，从而拖慢传感速度。为了解决这个问题，三星采用了一种时间偏移压缩技术：首先通过一条低电阻（0.1R）的快速充电路径为 RC 滤波器快速充电，随后电路切换到全电阻值，用于测量波形中对温度敏感的部分。

在时间数字转换器（TDC）部分，他们用一款基于紧凑型环形振荡器（RO， Ring Oscillator）的 TDC 取代了先前工作中使用的大型线性延迟发生器，将延迟发生器的面积削减了 99.1%。该环形振荡器还兼任系统时钟，并通过相位交错计数避免了非单调性问题。

![](https://substackcdn.com/image/fetch/$s_!f54k!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2cd264f4-0a79-4823-8ab5-1cbfd4627f9f_2880x1620.png)

*三星 SF2 温度传感器转换时间与精度对比。来源：三星，ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!nCIv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0d4c4094-3c4e-42fc-a4d5-6087d122c98a_2880x1620.png)

*三星 SF2 温度传感器与先前工作的对比表。来源：三星，ISSCC 2026*

这款新型温度传感器的精度品质因数（FoM）为 0.017 nJ·%²，优于先前基于三星 5LPE、台积电 N3E 和英特尔 4 工艺（JSSC 2025）的工作。此前的温度传感器只能在面积或速度其中一项上进行优化。例如，台积电 N3E 上的传感器面积很小（900 μm²），但转换时间长达 1 毫秒；而三星 5LPE 上的传感器速度很快（12 微秒），但面积巨大（6356 μm²）。
