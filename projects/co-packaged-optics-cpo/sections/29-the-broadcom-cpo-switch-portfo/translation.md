![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_056.png)

来源：SemiAnalysis

博通是最早推出真正CPO系统的公司之一，因此被视为CPO领域的领军者。博通的第一代CPO器件名为Humboldt，主要用作概念验证。该器件被称为“TH4-Humboldt”，是一款25.6Tbit/s以太网交换机，其总容量在传统电连接和CPO之间平分秋色。其中，12.8Tbit/s由四个3.2Tbit/s光引擎（Optical Engine，OE）处理，每个光引擎提供32条100Gbit/s通道。这种铜缆与光学的混合设计拥有若干突出用例。在其中一种场景中，顶置机架（ToR）交换机依靠电接口通过短距离铜缆连接附近服务器，而其光端口则上联至下一层交换设备。

在另一种场景中，汇聚层以电端口互连机架内各类交换机，光链路则延伸至该层上下交换层。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_057.png)

来源：Broadcom

在该设计中，博通采用硅锗（SiGe）电集成电路（EIC），下一代产品（即Bailly）则改用CMOS工艺。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_058.png)

来源：Broadcom

博通第二代CPO器件Bailly是一款51.2 Tbit/s以太网交换机，与前代半光学设计不同，它完全依赖光学I/O。它由八个6.4 Tbit/s光引擎组成，每个引擎提供64条100 Gbit/s通道。另一显著变化是，它不再使用SiGe EIC，而是采用7nm CMOS EIC。转向CMOS EIC后，设计得以更加复杂集成，并新增控制逻辑，从而将通道数从之前的32条提升至新光引擎中的64条。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_059.png)

来源：Broadcom

**修订后的译文：**

从第一代到第二代的另一显著转变，是封装工艺从TSV转向扇出型晶圆级封装（FOWLP）。在此设计中，EIC借助模塑料通孔（TMV）将信号上引至光集成电路（Photonic Integrated Circuit，PIC），再以铜柱凸块将其连接至基板。采用FOWLP的主要原因在于，该技术已在手机市场获得验证，并得到OSAT广泛支持，因而具备更强的可扩展性。ASE/SPIL是该FOWLP工艺的OSAT合作伙伴。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_060.png)

来源：Broadcom

博通在2024年Hot Chips大会上展示了一种实验性设计，将6.4Tbit/s光学引擎与一个逻辑芯片、两个HBM堆叠以及一个SerDes tile集成在同一封装中。他们提出采用扇出型方案，将HBM置于基板的东西边缘，从而为同一封装内的两个光学引擎腾出空间。从CoWoS-S转向CoWoS-L后，基板尺寸将超过100mm边长。这样，他们得以容纳最多四个光学引擎，并实现51.2Tbit/s的带宽。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_061.png)

来源：Broadcom

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_062.png)

来源：Broadcom

今年，博通推出基于Tomahawk 6的Davisson共封装光学（CPO）交换机，集成十六个6.4T光引擎（OE）。交换机ASIC采用台积电N3制程节点制造，每封装提供102.4 Tbit/s带宽。博通委托Micas、Celestica等合同制造商（CM）进行机箱组装。此外，据称NTT Corp（日本）正在采购博通TH6裸芯片，并采用自家专有的光引擎与光解决方案构建CPO系统，而非取用博通方案。此举扩大了基于TH6的CPO系统的潜在商机，并推动更开放的供应商生态系统。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_063.png)

来源：SemiAnalysis

随着CPO在规模化组网中展现更大价值，我们认为博通率先量产交付的CPO系统将用于其客户的AI ASIC。博通在CPO领域的深厚积累，使其成为中短期内计划将CPO纳入ASIC路线图的客户的理想设计伙伴。我们了解到，这也是OpenAI选择博通的关键因素之一。有趣的是，博通最大的ASIC客户谷歌，却是对在数据中心部署CPO最为犹豫的超大规模云服务商。谷歌的基础设施理念更注重可靠性而非绝对性能，而CPO的可靠性对他们而言成了难以逾越的障碍。我们预计谷歌短期内不会采用CPO。

博通未来几代CPO端点也将转向台积电的COUPE平台——这清晰表明COUPE所提供的特性为带宽扩展指明了路径。这不仅会改变光引擎（OE）的封装方式，博通前几代产品一直采用边缘耦合以及MZM，这两种选择实施较为简便，但正如前文所述，可扩展性较差。COUPE则倾向于采用光栅耦合和MRM，这与博通现有技术路线形成显著差异。尽管博通拥有最丰富的CPO经验，但这种技术路线的转变意味着其必须在技术的某些方面从头再来。关键在于台积电能在多大程度上为博通提供协助，降低设计难度。
