Celestial AI 是一家专注于AI纵向扩展网络光互连解决方案的IP、产品和系统公司。该公司技术的主要目标是将光子器件（调制器、光电探测器、波导等）集成到中介层中，并通过与外部世界的接口（带光纤阵列单元（FAU）的光栅耦合器）实现连接。下图清晰展示了Celestial AI的光子基互连解决方案组合，即其所称的“Photonic FabricTM”（简称PF）。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_072.png)

来源：Celestial AI

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_073.png)

来源：Celestial AI

**修订后的译文：**
光子织物TM（PF）芯粒是基于台积电5nm工艺的芯粒，集成了UCIe和MAX PHY等die-to-die接口，可实现XPU-to-XPU、XPU-to-Switch以及XPU-to-Memory的连接。客户可将其与自身XPU共封装，与基于电气SerDes接口的共封装光学（CPO）产品相比，能够提供更高的带宽密度和更低的功耗。Celestial AI根据客户具体需求开发这些芯粒，以适配特定的D2D接口和协议。第一代PF芯粒支持16 Tbit/s带宽，第二代将达到64 Tbit/s。

与传统铜互连相比，光学芯粒在功耗上具有显著优势。采用224G线性SerDes的传统铜缆每比特功耗约为5 pJ/bit。由于需要两端，总功耗约为10 pJ/bit。而Celestial AI的解决方案整个电-光-电链路仅需约2.5 pJ/bit（外部激光器额外消耗约0.7 pJ/bit）。

**修订后的译文：**

接下来，光子织物TM光学多芯片互连桥TM（OMIBTM）本质上是一种CoWoS-L或EMIB风格的封装解决方案。它将光子技术直接集成到中介层中的嵌入式桥接器上，使桥接器能够将数据直接传输到使用端。与PF芯粒相比，它能够提供更高的整体芯片带宽，因为不受岸线限制（beachfront constraints）的制约。

在传统的采用金属互连的中介层或基板中，将I/O置于芯片中心是不切实际的，因为这会极大增加布线复杂度，同时高密度信号拥塞还会引发严重的串扰问题。不过，借助OMIB光互连中介层，Celestial AI能够将中介层直接置于ASIC正下方，从而绕过边缘限制，实现更快、更高效且串扰极低的数据传输。

光互连中介层允许I/O被放置在芯片上的任意位置，因为光学波导在传输过程中信号衰减极小，从而彻底消除了我们所熟知的边缘限制。同时，由于不同波导中的光信号被高度限制在波导芯内，仅在包层中有极小的渐逝场，因此不会像密集排布的铜迹线中的电信号那样产生串扰。这种从根本上重新设计的I/O架构和布局，充分释放了光学技术所带来的潜力。

![A screen shot of a computer](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_074.png)

来源：Celestial AI

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_075.png)

来源：Celestial AI, Marvell

光学中介层或通过先进封装传输光信号的理念与Lightmatter的方案有几点相似之处：两者都将光信号路由到逻辑芯片下方，从而避免边缘限制，但也存在一些关键差异。Celestial AI采用的是类似于硅桥（类似CoWoS-L硅桥）的光子桥，而Lightmatter则使用一个大型多重曝光光子中介层，置于多个独立芯片下方。Lightmatter的概念在规模上更为宏大——其M1000 3D光子超级芯片的目标是实现4000 mm²的中介层尺寸，同时还计划在中介层内支持光路交换，并提供高达114 Tbit/s的总聚合带宽。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_076.png)

来源：Celestial AI, Marvell

最后，Celestial AI还提供光子织物TM内存设备（PFMA），这是一种基于台积电5nm工艺构建的高带宽、低延迟纵向扩展织物，内置网络内存，总带宽115.2 Tbit/s，可将16个ASIC以每个ASIC 7.2T的纵向扩展带宽连接起来。值得注意的是，PFMA是全球首款在芯片中心集成片上光学I/O的硅器件，从而将宝贵的边缘物理I/O留给内存控制器。这使得PFMA成为主机CPU内存与存储之间用于KV缓存卸载的“温”内存层。

Celestial AI技术的关键差异化优势在于其采用了电吸收调制器（Electro Absorption Modulator，EAM）。本文第三部分已详细说明了EAM的工作原理，并讨论了其优势与权衡。此处我们再次概要复述相关讨论，因为理解EAM的优缺点对于把握Celestial AI的市场策略至关重要。

与微环调制器（MRM）和马赫-曾德尔干涉仪（MZI）相比，EAM具有多项显著优势：

- 显然，EAM和MRM都配备了控制逻辑和加热器来稳定温度变化，但EAM对温度的敏感度从根本上更低。与MRM相比，EAM在50°C以上表现出更好的热稳定性，而MRM对温度极为敏感。MRM典型的温度稳定性为70-90 pm/°C，这意味着2°C的温度变化就会导致谐振波长偏移0.14nm，远远超出0.1nm这一MRM性能崩溃的临界偏移值。相比之下，EAM能够承受高达35°C的瞬时温度突变。这一耐受性对Celestial AI的方案尤为重要，因为其EAM调制器位于中介层内，而上方的高功耗XPU计算引擎会散发数百瓦的功率。此外，EAM还能承受约80°C的高环境温度范围，这适用于放置在XPU旁而非下方的芯粒应用。

- 与MZI相比，EAM的尺寸要小得多且功耗更低，因为MZI相对较大的尺寸需要较高的电压摆幅，需要通过SerDes放大才能达到0-5V的摆幅。马赫-曾德尔调制器（MZM）的面积约为12,000µm²，而锗硅EAM约为250µm²（5×50µm），MRM则在25µm²至225µm²之间（直径5-15µm）。MZI还需要为加热器消耗更多功率，以将如此大的器件维持在所需的偏置点。

另一方面，在共封装光学（CPO）中使用锗硅EAM也存在一些缺点：

- 构建在硅或氮化硅上的物理调制器结构（如MRM和MZI）一直被认为比基于锗硅的器件具有更高的耐久性和可靠性。的确，许多人担心锗硅器件的可靠性，因为集成锗基器件难度较大。但Celestial AI指出，锗硅EAM本质上是光探测器的逆向结构，而光探测器已在当今的光模块中广泛使用，因此其可靠性是一个已知量。

- 锗硅调制器的带边天然位于C波段（即1530nm-1565nm）。设计量子阱将其迁移到O波段（即1260-1360nm）是一个极具挑战性的工程难题。这意味着基于锗硅的EAM很可能只能用于封闭式的CPO系统，难以参与开放的芯粒生态系统。

- 围绕C波段激光光源构建激光生态系统，与利用已高度成熟的O波段连续波激光光源生态系统相比，可能面临规模不经济的问题。大多数数据通信激光器都是为O波段设计的，但Celestial AI指出，目前已有相当规模的1577nm XGS-PON激光器在量产。这些激光器主要用于消费级的家庭和企业光纤接入应用。

- SiGe EAM的插入损耗约为4-5dB，而MRM和MZI的插入损耗均为3-5dB。虽然MRM可用于直接复用不同波长，但EAM需要额外的复用器来实现CWDM或DWDM，这会略微增加整体损耗预算。

总体而言，Celestial AI一直致力于创新其定制链路——它们不依赖任何齿轮箱组件，从而提供更好的延迟和能效，并且能够适配不同类型的协议。如前所述，Celestial AI是唯一主要采用EAM进行调制的厂商。关键影响之一是，他们还需要投入精力将EAM设计集成到晶圆代工厂工艺中，而其他共封装光学（CPO）厂商则可以依托台积电COUPE，其中MRM及相关加热器已纳入工艺设计套件（PDK）。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_077.png)

来源：Celestial AI

短期内，Celestial AI承诺为芯粒发布制定雄心勃勃的时间表。Marvell在交易摘要中宣布，预计到2028年1月底（即Marvell 2028财年结束，也称F1/28），来自Celestial的营收运行率将达到5亿美元。在巴克莱全球科技会议上，他们进一步表示，该运行率预计到2028年日历年年底将翻番至10亿美元（大部分2028日历年落在Marvell截至2029年1月的财年，即F1/29），这意味着从当前到2027年底约两年的时间内，产品需要实现商业化。

根据交易条款，额外22.5亿美元的支付将支付给Celestial AI的股权持有人，其前提是公司在2029年1月（Marvell 2029财年结束，即F1/29）前实现累计营收至少20亿美元。其中第一个里程碑是在2029年1月前实现5亿美元累计营收，即可获得总支付额的三分之一。预计F1/29财年末10亿美元的营收运行率仅为earn-out金额的一半——这意味着Celestial AI需要增加更多客户订单，才能达成20亿美元的earn-out目标。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_078.png)

来源：Celestial AI, Marvell

在收购Celestial AI的相关事宜中，Marvell于2025年12月2日提交了8-K报告，发行了亚马逊认股权证，行权价格为87.0029美元，行权期至2030年12月31日。这些认股权证的归属“基于亚马逊在2030年12月31日前直接或间接购买光子织物（Photonic Fabric）产品的数量”，强烈表明AWS的Trainium将是目标产品，因为该产品预计将于2027年底开始量产。在Marvell的行业分析师日活动中，Celestial AI谈到一家大型超大规模云厂商选择他们为其下一代处理器中的先进AI系统提供光互连，该产品将进入量产阶段。

结合 earn-out 时间安排以及交易摘要中的产品营收指引，这表明Celestial AI的目标是将解决方案部署在Trainium 4中。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_079.png)

来源：Marvell SEC 文件

让我们通过进一步阐述其即将面市的首个纵向扩展解决方案来结束对Celestial AI的讨论。该方案将围绕其16Tbit/s光子链路构建，并连接到一个芯粒。FAU通过光栅耦合器与通道波导相连。一个纵向扩展网络交换机ASIC（可能是Marvell的115.2T纵向扩展ASIC）将通过光子链路和PF芯粒与XPU实现光学连接。虽然Celestial AI预计其初期上市营收主要来自芯粒，但它将自身定位为一家系统公司，并已提出几种基于光学的内存扩展解决方案，这些方案可在首个纵向扩展网络解决方案之后推向市场。

利用光学技术通过多层交换机来扩大纵向扩展世界规模并非新概念，尽管它距离真正产品化仍有差距。这种概念可能采用类似于GB200的NVL576的拓扑结构，其中存在两层交换机，每层交换机之间通过OSFP收发器模块和光纤连接。Celestial AI采用多层交换机的方法与之类似，但省去了实际收发器的使用。

然而，与NVL576概念最大的不同在于，纵向扩展ASIC可以同时兼任路由器和内存端点，而NVSwitch仅在GPU之间路由高带宽链路。这一区别非常重要，因为Celestial AI的核心主张是，其纵向扩展解决方案能够规避前沿约束（beachfront constraint），该约束限制了可连接到XPU的HBM堆叠数量。

为实现这一目标，连接到XPU的HBM堆叠被替换为一个芯粒，该芯粒连接到光子织物，后者是一个共享HBM池。共享HBM池即光子织物设备（Photonic Fabric Appliance，PFA），这是一个可安装在2U机架上的系统，由16个光子织物ASIC组成，每个ASIC包含一个端口。

每个ASIC采用2.5层封装，集成两颗36GB HBM3E内存和八个外部DDR5。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_080.png)

来源：Celestial AI

光学I/O（光子织物IP）安装在ASIC中央，而非前沿位置，从而将岸线资源释放出来，用于其他用途。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_081.png)

来源：Celestial AI

从整体来看，每个PFA模块都是一个16基数交换机，最多可支持16个XPU。系统并非让每个XPU都扇出到全部16个端口，而是将所有对所有连接发生在交换机机箱内部，其中连接到每个交换机ASIC的光纤连接单元（Fiber Attach Unit，FAU）扇出至16个交换机I/O。因此，每个XPU仅需一条光纤链路连接到机箱外的一个交换机端口。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_082.png)

来源：Celestial AI

通过将内存置于XPU外部并置于共享交换接口内，数据得以聚合，随后由共享内存池通过all-reduce通信集体被每个XPU访问。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_083.png)

来源：Celestial AI
