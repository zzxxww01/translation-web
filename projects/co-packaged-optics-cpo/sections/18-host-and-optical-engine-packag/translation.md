顾名思义，“共封装光学（co-packaged optics，CPO）”本质上是一项封装和组装挑战。

**修订后的译文：**

光引擎兼具光学与电学组件。光电探测器和调制器是集成于“PIC”（光子集成电路）的光学组件，驱动器和跨阻放大器则是集成于“EIC”（电集成电路）的电学电路。PIC与EIC必须合为一体，光引擎（Optical Engine，OE）方能正常工作。目前有多种封装方法可实现这一PIC–EIC集成。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_031.png)

来源：ID TechEx

光学引擎可采用单片集成方式，在同一晶圆上同时制造 PIC 和 EIC。从寄生参数、延迟和功耗角度看，单片集成是最优雅的方法。Ayar Labs 的第二代 TeraPHY 芯粒就采用了这一方案（不过其下一代芯粒已转向台积电 COUPE）。GlobalFoundries、Tower 和 Advanced Micro Foundry 等晶圆代工厂可提供单片 CMOS 与 SiPho 工艺。然而，单片工艺在约三十五纳米以下节点便无法继续推进，因为光子工艺无法像传统 CMOS 那样持续缩放。这限制了 EIC 的性能，尤其是在 CPO 系统所需更高通道速率的情况下。尽管单片集成本身简洁优雅，但这一限制使其难以实现规模化扩展。

因此，Ayar Labs 也在将其路线图转向异构集成的光引擎，以期进一步扩容。

**修订后的译文：**

异构集成正成为主流方案，即采用 SiPho 工艺制造 PIC，再通过先进封装将其与 CMOS 晶圆的 EIC 集成一体。目前存在多种封装方案，其中更先进的封装方案能带来更高性能。在这些方案中，3D 集成可提供最佳带宽与能效。EIC 与 PIC 通信的最大障碍是寄生参数，大幅缩短互连长度可显著降低寄生效应当，从而大幅提升耦合效率。从带宽和功耗角度看，3D 集成是实现共封装光学（CPO）性能目标的唯一途径。
