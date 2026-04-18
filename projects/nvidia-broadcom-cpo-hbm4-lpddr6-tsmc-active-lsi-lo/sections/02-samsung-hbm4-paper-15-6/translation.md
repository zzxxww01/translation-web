在三大存储器厂商中，三星是唯一一家就HBM4发表技术论文的。在ISSCC之前，我们曾在加速器与HBM模型中指出，三星在其HBM4代产品上相比HBM3E取得了巨大改进。ISSCC上公布的数据证实了我们的分析，三星展示了同类最佳的性能——我们数月前也在模型更新说明中详细阐述了这一进展。

ISSCC上披露的技术细节，结合我们收集到的业界讨论，清晰地表明三星的HBM4已具备与同行竞争的实力。值得注意的是，它能够在电压低于1V的同时，满足Rubin所需的引脚速度。尽管三星在可靠性和稳定性方面仍落后于SK海力士，但该公司在技术层面已取得显著进步，缩小了差距，并可能挑战SK海力士在HBM领域的统治地位。其基于1c制程的HBM4搭配SF4逻辑基础芯片，看来在引脚速度上表现更优。

https://substackcdn.com/image/fetch/$s_!8SFa!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F515a99f4-5397-4b1a-9f95-d9a3dff37521_2880x1620.jpeg

三星HBM3E与HBM4规格对比。来源：三星，ISSCC 2026

https://substackcdn.com/image/fetch/$s_!t-2P!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F773189fd-1dd5-434a-aa0c-694db785b9c9_2880x1620.jpeg

三星HBM4芯片照片与截面图。来源：三星，ISSCC 2026

三星展示了一款36 GB、12层堆叠的HBM4产品，拥有2048个I/O引脚和3.3 TB/s的带宽。该产品采用第六代10纳米级（1c）DRAM核心芯片，并搭配了SF4逻辑基础芯片。

从HBM3E到HBM4，最明显的架构变化在于核心DRAM芯片与基础芯片采用了不同的工艺技术。HBM4仅对核心芯片使用DRAM制程节点，而基础芯片则采用先进的逻辑制程节点制造。这与前几代HBM对两者使用相同工艺的做法不同。

随着AI工作负载对HBM的带宽和数据速率提出更高要求，关键的架构挑战也随之产生。通过将基础芯片转移到SF4逻辑制程，三星实现了更高的运行速度和更低的功耗。其工作电压（VDDQ）从HBM3E的1.1V降至HBM4的0.75V，降幅32%。与采用DRAM工艺制造的基础芯片相比，基于逻辑制程的基础芯片能提供更高的晶体管密度、更小的器件尺寸以及更好的面积效率，这得益于其更小的晶体管和更丰富的金属层堆叠可用性。这帮助三星的HBM4不仅达到，而且显著超越了JEDEC的HBM4标准——我们将在本节末尾对此进行更详细的解释。

https://substackcdn.com/image/fetch/$s_!SBki!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff3e96393-ade6-49e3-82fa-8127beff5ad4_2880x1620.jpeg

三星HBM4自适应体偏置控制与工艺波动。来源：三星，ISSCC 2026

结合能缓解堆叠核心芯片间工艺波动的自适应体偏置（ABB）控制，翻倍的TSV数量进一步提升了时序裕量。三星的论文宣称，ABB和高达4倍的TSV数量共同使其HBM4能够实现每引脚高达13 Gb/s的运行速度。

然而，SF4基础芯片和1c DRAM核心芯片带来的性能提升是有代价的。三星选择SF4工艺制造逻辑基础芯片，这一决策导致其成本高于竞争对手的方案，尽管三星晶圆代工厂能为内部使用提供折扣。相比之下，SK海力士为其HBM4基础芯片采用台积电的N12逻辑制程，而美光则依赖其内部CMOS基础芯片技术。这两种方案的成本都低于接近前沿的SF4制程节点，即使考虑到垂直整合带来的成本优势也是如此。

事实证明，1c前端制造工艺在整个2025年对三星而言都颇具挑战，尤其是考虑到该公司跳过了1b节点，直接从基于1a的HBM3E过渡到1c世代。去年，1c节点的前端良率仅约为50%，尽管随着时间的推移已逐步改善。较低的良率对其HBM4的利润率构成了风险。

从历史上看，三星HBM的利润率一直低于其主要竞争对手SK海力士。我们在我们的**内存模型**中对所有厂商的这一动态进行了全面建模，详细列出了各厂商在不同制程节点下HBM、DDR和LPDDR的晶圆产量、良率、密度、销货成本等数据。

三星的策略似乎是激进地采用更先进的制程节点来制造基础芯片，以实现卓越性能并超越竞争对手。尤其是在英伟达等主要客户对HBM的要求持续提高的背景下，这一策略显得尤为突出。

HBM中另一个需要解决的关键问题是tCCDR，即在不同堆栈ID（SID）间连续发出读取命令所需的最小时间间隔。对于严重依赖跨多个通道并行内存访问的AI工作负载而言，tCCDR直接影响可实现的存储器吞吐量。

在堆叠式DRAM架构中，多个核心芯片垂直集成在基础芯片之上。这自然会引入整个堆栈内的微小延迟差异，其驱动因素包括核心芯片与基础芯片间的工艺波动、硅通孔（TSV）传输延迟差异以及局部通道差异。

堆叠高度和通道数量从16层增至32层，加剧了这一挑战。随着通道数和堆叠高度的增加，芯片间的差异会累积，导致跨通道和跨芯片的时序失配更严重，从而影响可实现的tCCDR和HBM整体性能。

https://substackcdn.com/image/fetch/$s_!YCM6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe56f1735-adbc-4038-8473-b27f5ae002fb_1611x1352.jpeg

三星HBM4每通道TSV RDQS自动校准方案。来源：三星，ISSCC 2026

为解决此问题，三星引入了一种“每通道TSV RDQS时序自动校准方案”。上电后，系统使用一个复制真实信号路径时序行为的RDQS复制路径来测量各通道的延迟差异。时间数字转换器（TDC）将这些时序差异量化，随后通过为每个通道配置的延迟补偿电路（DCDL）进行补偿。

该校准方案同时考虑了堆叠核心芯片间的全局延迟差异和局部每通道差异，从而对齐整个堆栈的时序。通过补偿这些失配，三星显著提升了有效时序裕量，并在满足所需tCCDR限制的同时，提高了最大可实现数据速率。仅此一项方案就将数据速率从7.8 Gb/s提升至9.4 Gb/s。

我们一些精通存储器技术的读者可能会问：如何有足够的芯片面积来容纳大幅增加的TSV数量？这正是1c制程节点变得重要的原因。与之前的1a节点相比，1c进一步缩小了DRAM存储单元面积，从而释放出芯片空间，可用于集成HBM4所需的大量TSV。

https://substackcdn.com/image/fetch/$s_!FNwT!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F35b20c2b-2f00-4d4c-b05a-578d695a51c1_2880x1620.jpeg

三星HBM4 PMBIST测试模式操作。来源：三星，ISSCC 2026

https://substackcdn.com/image/fetch/$s_!06LM!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fec777954-f7fa-44fb-a8b3-f295d57f3e59_2880x1620.jpeg

三星HBM4 PMBIST与HBM3E MBIST对比。来源：三星，ISSCC 2026

逻辑基础芯片带来的另一项关键创新是三星的可编程内存内建自测试（PMBIST）架构。PMBIST允许基础芯片生成完全可编程的内存测试模式，同时支持完整的JEDEC行与列命令集。这意味着测试引擎能够发出与实际系统完全相同的命令，且可在任意时钟沿、以全接口速度执行这些命令。实际上，这使得工程师能够复现复杂的真实世界内存访问模式，并在实际运行条件下对HBM接口进行压力测试，而这是传统固定模式测试引擎难以做到的。

这种方法与HBM3E相比有显著不同。如前文所述，HBM3E的基础芯片采用DRAM工艺制造，这给其MBIST（内存内建自测试）引擎带来了严格的功耗和面积限制，并且，鉴于DRAM工艺在功耗和面积效率方面天然逊色于逻辑工艺，其测试只能局限于一小部分预定义的模式。通过将基础芯片转移到三星晶圆代工厂的SF4逻辑工艺，三星得以实现一个完全可编程的测试框架，能够运行复杂的测试算法和灵活的访问序列。

这为HBM带来了更强大的调试能力和更好的良率学习效果。工程师可以创建有针对性的压力测试模式，以验证tCCDR和tCCDS等关键时序参数，在制造早期识别极端情况下的故障，并加速晶圆上芯片（CoW）和系统级封装（SiP）测试阶段的特性表征。简而言之，随着HBM堆栈变得更复杂、运行速度更高，PMBIST提升了测试覆盖率、调试效率，并最终提高了生产良率。

https://substackcdn.com/image/fetch/$s_!E1zF!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8a03c69a-dc9b-4dfb-a6d2-ad4315760852_2880x1620.jpeg

三星HBM4舒姆图。来源：三星，ISSCC 2026

三星还展示了强劲的引脚速度结果——其HBM4能够在低于1V的核心电压（VDDC）下达到11 Gb/s，并在更高电压下达到13 Gb/s。我们尚未看到三星的同行展示出可比的性能，尽管后者在可靠性和稳定性上确实更具优势。

三星的实现方案大幅超越了官方JEDEC HBM4标准（JESD270-4）的基线规范，该规范规定的最大引脚数据速率为6.4 Gb/s，总带宽约为2 TB/s。三星展示的引脚速度是JEDEC标准的两倍多，达到13 Gb/s，可提供3.3 TB/s的带宽。即使在VDDC/VDDQ电压分别为1.05V和0.75V时，该器件仍能维持11.8 Gb/s的数据速率。
