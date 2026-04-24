一旦不再需要将电信号驱动到相对较长的距离，我们就可以彻底摆脱串行接口，转而采用宽接口，在短距离内提供远优于串行接口的**边缘带宽密度**。

其中一个典型例子是UCIe接口。UCIe-A可提供高达约10 Tbit/s/mm的边缘带宽密度，专为先进封装设计（即通过中介层互连、传输距离小于2mm的芯片let）。在一枚掩膜版尺寸芯片的长边上，这可实现高达330 Tbit/s（41TByte/s）的封装外带宽。若考虑芯片两侧长边，则双向封装外带宽可达660 Tbit/s。相比之下，Blackwell仅拥有23.6 Tbit/s的封装外带宽，相当于约0.4 Tbit/s/mm的边缘带宽密度，两者差距巨大。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_029.png)

来源：SemiAnalysis

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_030.png)

来源：SemiAnalysis

**修订后的译文：**

当然，这并非同类比较，因为这些封装外PHY需要驱动长距离信号。但这正是本文想阐明的要点：采用共封装光学 (Co-packaged Optics, CPO) 后，传输距离不再是考虑因素，因为信号无需通过长距离电互连驱动。在10 Tbit/s/mm的带宽密度下，瓶颈不再位于电气接口，而是链路的其他部分，即光纤另一端能够承载多少带宽。

**修订后的译文：**

要达到这一瓶颈状态，距离当前技术现实仍十分遥远，光引擎（Optical Engine, OE）必须与主机芯片共享中介层。将共封装光学（CPO）直接集成在中介层上，在路线图上的位置比在基板上可靠集成光引擎还要更远。基板上的PHY性能自然较低，UCIe-S可提供约1.8Tbit/s/mm的边缘带宽密度，但这仍比我们认为224G SerDes所能达到的约0.4Tbit/s/mm有显著提升。

然而，尽管宽接口具有明显优势，Broadcom和英伟达仍在路线图中坚持采用电气SerDes。主要原因是他们相信SerDes仍可继续扩展，并且需要针对铜缆进行设计，尤其是光学方案的采用速度较慢。同时，混合的共封装铜缆和共封装光学解决方案预计将长期存在，这要求他们同时针对两者进行优化。这样也能避免为不同方案多次流片。
