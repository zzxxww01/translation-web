Lightmatter以其光互连中介层（Optical Interposer）产品——Passage™ M1000 3D光子超级芯片而广为人知，同时也在为共封装光学（CPO）路线图的各个阶段推出多种解决方案，其中多个芯粒已在台积电完成流片。

**修订后的译文：**

首个将推向市场的解决方案是2026/2027年的近封装光学（NPO）光引擎。在NPO方案中，光引擎将焊接到底板上，通过铜线将XPU上的LR SerDes连接至光引擎。Lightmatter的光引擎最多支持3个FAU，每个FAU含40根光纤，总计120根光纤。NPO策略基于以下前提：超大规模云服务商在采用共封装光学（CPO）前，会先通过NPO积累运营经验。此举可降低产品风险，因为他们无需“承诺”采用CPO，最终仍可选择使用光学或铜缆纵向扩展方案来对接XPU或交换机上的LR SerDes。

由于Lightmatter的光引擎方案基于台积电COUPE和GF 45nm SPCLO工艺，存在多种扩展路径。除了通过100Gbaud PAM4实现每通道200Gbit/s（单向）之外，它还支持通过DWDM8在PAM4下实现每通道200Gbit/s，或通过DWDM16在PAM4下实现每通道100Gbit/s，进而使每根光纤达到3.2T带宽。

虽然其他一些共封装光学（CPO）公司选择使用商用激光源生态系统，但Lightmatter开发了名为GUIDE的自主外部激光源，目前正在送样。其他激光源通常将InP晶圆切割成独立的激光二极管，而GUIDE是业界首个超大规模光子学（VLSP）激光器，属于一类新型激光器，可将数百个InP激光器集成到单颗硅芯片上，最高支持50 Tbit/s带宽。Lightmatter声称其独有的控制技术能够管理这些大量InP激光器，同时通过超量配置InP激光器数量并允许通过切换仍在工作的二极管实现“自修复”，从而显著提升整体可靠性。

英伟达Quantum-X共封装光学（CPO）交换机具备144个800G端口，需要18个外部激光源（ELS），而Lightmatter宣称仅需两个GUIDE激光源即可满足相同的整体带宽需求。

Lightmatter计划与台积电COUPE路线图保持同步，于2027年和2028年正式推出共封装光学（CPO）解决方案，随后在2029年及以后重点推进其旗舰产品Passage™ M1000。

Lightmatter的M1000 3D光子超级芯片是一块4000 mm²的光互连中介层，置于主机计算引擎下方，负责电信号到光信号的转换。M1000已在SC25展会上进行了机架级实时演示demonstrated in a live rack-scale demonstration at SC25，Lightmatter已将其作为参考设计对外提供。Passage利用TSV在XPU和光引擎之间传输电信号和电源，并使用SerDes连接两者。通过将ASIC直接置于光互连中介层上，Passage消除了对大功耗SerDes的需求，转而采用1024个紧凑、低功耗的SerDes（体积约为传统SerDes的1/8），从而实现总计114Tbit/s的I/O带宽（每个SerDes工作在112Gbit/s）。

将ASIC直接置于光互连中介层上方，也缓解了芯片岸线资源的限制。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_084.png)

来源：Lightmatter

该系统集成了内置的光学电路交换（OCS），用于管理冗余——如果某条通信路径发生故障，流量可通过备用路径重新路由，从而确保在如此大规模系统中运行不中断。此外，相邻的tile通过电气方式拼接在一起，能够使用UCIe等接口进行电子通信。

Passage采用直径约15 µm的微环调制器（MRM），每个均集成电阻加热器，可实现56 Gbit/s NRZ调制。该模块包含16条水平总线，每条总线可承载最多16种颜色（波长）。这些颜色将由GUIDE提供，每根光纤在200 GHz间隔上可传送16个波长。

Passage使用了256根光纤，每根光纤通过DWDM单向承载16个波长（或双向承载8个波长），每根光纤可提供1 Tbit/s至1.6 Tbit/s的带宽。为提高良率，他们将连接到芯片的光纤数量降至最低，从而降低了复杂度和制造难度。此外，他们还实施了一套光纤连接系统，允许将故障光纤从面板上轻松断开并更换，提升了可靠性和可维护性。下表反映了Passage当前支持的不同模式。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_085.png)

来源：Lightmatter

关于PASSAGE的一个关键争议在于其所用微环调制器（MRM）的热稳定性，因为光互连中介层直接位于温度很高的XPU下方。相比之下，其他共封装光学（CPO）方案并未将调制器直接置于XPU下方，因此热管理更为容易。针对这一问题，Lightmatter解释称，PASSAGE中用于MRM的控制环路能够承受2000°C/s的温度变化率，并可在0至105°C的温度范围内工作——也就是说，60至80°C的温度跃变可在10毫秒内发生，而不会中断光链路。

SC25演示视频展示了一幅温度在25°C至105°C之间变化的示意图，表明其工作温度范围很宽，不过该演示中80°C的温度跃变耗时约一分钟，变化速率仅为较低的1.33°C/秒。而在SC25的另一场演示中，使用片上热干扰源达到了2000°C/秒的速率，此时MRM稳定加热器可将MRM本身的温度变化控制在-2至+2°C/秒的极小范围内。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_086.png)

来源：Lightmatter
