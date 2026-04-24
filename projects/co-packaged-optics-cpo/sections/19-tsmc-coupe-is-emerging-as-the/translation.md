**修订后的译文：**

台积电正迅速成为无晶圆厂巨头与初创企业下一代光引擎的首选晶圆代工厂合作伙伴。以共封装光学端点为核心的首批高量产产品，正以“COUPE”——即“紧凑通用光子引擎”的名称推出。这包括EIC与PIC的制造，以及台积电COUPE方案下的异构集成。英伟达在GTC 2025上展出其COUPE光引擎，这些将成为首批出货的COUPE产品。尽管现有几代光引擎采用其他供应链伙伴，博通仍将COUPE纳入其未来技术路线。

如前所述，此前依托Global Foundries Fotonix平台打造单片光学引擎的Ayar Labs，如今也已将COUPE纳入其技术路线。

**修订后的译文：**
与在传统CMOS逻辑领域的主导地位不同，台积电此前在硅光子领域存在感较弱，当时Global Foundries和Tower Semi是更受欢迎的晶圆代工厂合作伙伴。然而近年来，台积电在光子能力上迅速追赶。同时，台积电还为其EIC组件带来了无可争议的先进CMOS逻辑制程优势，以及领先的封装能力——台积电是唯一一家已在合理规模上展示芯片到晶圆混合键合能力，并量产多种AMD混合键合芯片的晶圆代工厂。混合键合是性能更优的PIC与EIC键合方式，尽管其成本显著更高。

英特尔正着力开发同类能力，但在开拓这项技术上已遭遇重大挑战。

总体而言，尽管此前台积电独立的硅光子能力相对较弱，但如今它已成为共封装光学领域的重要玩家。与其他主要玩家一样，台积电旨在尽可能多地占据价值链。采用台积电COUPE方案的客户，实际上等于承诺使用台积电制造的PIC，因为台积电不代工其他晶圆厂的SiPho晶圆。许多专注CPO的公司已果断转向，将台积电COUPE作为未来几年的主力上市方案。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_032.png)

来源：台积电

Die fabrication: 台积电为芯片制造提供一套完整解决方案。EIC采用N7制程节点打造，集成高速光调制器驱动器与TIA，并内置加热器控制器以实现波长稳定等功能。PIC则在SOI N65制程节点上制造，台积电为其提供光子电路设计、光子版图设计与验证，以及光子电路仿真与建模（涵盖RF、噪声和多波长等方面）的全面支持。

台积电采用SoIC键合工艺将EIC与PIC键合一体。正如我们之前提到的，走线越长，寄生效应越大，性能也就越差。台积电的SoIC是一种无凸块接口，能在非单片集成的前提下提供最短走线，因而是异构集成EIC与PIC的性能最优方案。如图所示，在同等功耗下，基于SoIC的光引擎所提供的带宽密度，是采用凸块集成的光引擎的23倍以上。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_033.png)

来源：台积电

COUPE支持整个光引擎的设计与集成流程。在光学I/O方面，它支持µLens设计，可在晶圆级或芯片级集成微透镜，并提供涵盖反射镜、µLens、光栅耦合器（GC）和反射器的光学I/O路径仿真。在3D堆叠方面，它支持3D布局规划、SoIC-X/TDV/C4凸块布局实现、接口物理检查，以及高频通道模型提取与仿真。为确保开发顺畅，COUPE平台提供完整的PDK和EDA工作流程，用于COUPE的设计与验证，使设计师能够高效实现其技术。

【耦合方式】：正如我们后续将详细说明的，存在两种主要耦合方法——光栅耦合（GC）和边缘耦合（EC）。COUPE采用一种通用的EIC-on-PIC无凸块堆叠结构，同时支持GC和EC。然而，COUPE-GC结构会特别使用硅透镜（Si lens）和金属反射镜（MR），而COUPE-EC则独有EC端面（用于将边缘耦合终止至光纤）。在GC情况下，硅透镜设计在770µm厚的硅载体（Si-carrier）上，金属反射镜则直接置于光栅耦合器正下方，并搭配优化后的介电层以实现最佳光学性能。随后，该硅载体通过WoW（晶圆对晶圆）键合方式键合至CoW（芯片对晶圆）晶圆上。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_034.png)

来源：台积电

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_035.png)

来源：台积电

【光纤连接单元（FAU）】：FAU需要根据COUPE的光路进行协同设计。其目的是以低插入损耗将来自硅透镜的光耦合进光纤。随着I/O数量增加，制造难度也会上升，但如果业界能遵循特定标准，开发时间和成本将显著降低。总体而言，每个组件都需要经过优化设计，才能实现最佳光学性能。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_036.png)

来源：台积电

【产品路线图】：COUPE的第一代迭代将采用基板上的光学引擎，最终目标是能够将光学引擎（OE）置于中介层上。中介层可提供高得多的I/O密度，从而在光学引擎与ASIC PHY之间实现更大的带宽，单个光学引擎有望达到12.8Tbit/s的带宽，相当于约4 Tbit/s/mm。将光学引擎集成到中介层面临的挑战在于扩大中介层尺寸（其成本远高于封装基板），以容纳光学引擎。

这正是Broadcom转向台积电COUPE作为其CPO解决方案的原因，尽管它已用SPIL开发的扇出型晶圆级封装（FOWLP）迭代了多代CPO产品。值得注意的是，Broadcom已承诺在其未来的交换机和客户加速器路线图中采用COUPE。我们了解到，FOWLP方案因电信号必须穿过模塑通孔（TMV）才能抵达EIC，寄生电容过大，无法将单通道速率扩展至100G以上。为保持竞争力，Broadcom必须转向COUPE，后者能提供更优的性能和可扩展性。这凸显了台积电的技术优势，使其即使在过去被视为相对薄弱的光学领域也能斩获订单。

https://substack-post-media.s3.amazonaws.com/public/images/52efaf06-fa1a-4c3d-95b3-c4510f59128c_1312x738.png

来源：Broadcom

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_037.png)

来源：Broadcom
