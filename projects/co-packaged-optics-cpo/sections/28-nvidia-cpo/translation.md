在GTC 2025大会上，英伟达发布了其首款基于共封装光学（CPO）的横向扩展网络交换机。共发布了三款不同的CPO交换机。我们将逐一介绍这三款交换机，首先用一张表格汇总其关键规格：

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_045.png)

来源：SemiAnalysis

### **Quantum-X光子学**

预计2025年下半年率先上市的首款CPO交换机是Quantum X800-Q3450。它配备144个物理MPO端口，可支持144个800G逻辑端口或72个1.6T逻辑端口，聚合带宽达到115.2T。其外观酷似意大利面怪物，让作者们看了都有些饿了。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_046.png)

来源：英伟达

Quantum X800-Q3450通过四颗Quantum-X800 ASIC芯片（每颗带宽28.8 Tbit/s）以多平面配置实现如此高的端口密度和聚合带宽。在这种多平面配置中，每个物理端口均同时连至四颗交换ASIC，任意两个物理端口通信时，数据会经四个不同交换ASIC分流，每个ASIC使用200G通道。

在三层网络的最大集群规模上，这与理论上使用四倍数量的28.8T交换机盒子、却采用200G逻辑端口的结果完全一致——两者均支持最大746,496个GPU的集群规模。不同之处在于，使用X800-Q3400交换机时，数据混洗在交换机盒子内部一气呵成，而用离散的28.8T交换机盒子搭建相同网络，则需大量单独光纤电缆连接更多目的地。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_047.png)

来源：SemiAnalysis

Quantum X800-Q3450中的每颗ASIC周围环绕着六个可拆卸的光学子组件，每个子组件内含三个光引擎（OE）。每个光引擎提供1.6 Tbit/s带宽，因此每颗ASIC共包含18个光引擎（OE），聚合光学带宽达到28.8 Tbit/s。需要注意的是，这些子组件可拆卸，因此严格来说，纯粹主义者可能会认为这属于“NPO”而非严格意义上的“CPO”。尽管可拆卸OE会带来少量额外信号损耗，但我们认为这实际上不会对性能造成显著影响。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_048.png)

来源：英伟达

每个引擎采用8个电通道和8个光通道，电侧由200G PAM4 SerDes驱动，光侧则以8个微环调制器（MRM）通过PAM4调制实现每调制器200G速率。这一设计选择是本次发布的一大亮点：英伟达与台积电能在量产中推出200G MRM。这与当今最快的MZM性能相当，一举打破业界认为MRM仅限于NRZ调制的固有认知。这是英伟达达成的一项令人印象深刻的工程成就。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_049.png)

来源：英伟达

每个光学引擎集成了一个基于成熟N65制程节点的光子集成电路（PIC）和一个采用先进N6节点制造的电子集成电路（EIC）。PIC采用较老制程，是因为它包含调制器、波导和探测器等光学组件，这些器件无法从制程缩小中获益，通常在较大几何尺寸下表现更佳。相比之下，EIC包含驱动器、跨阻放大器（TIA）和控制逻辑，这些部分能显著受益于更高的晶体管密度和先进制程带来的功耗效率提升。这两颗芯片随后通过台积电的COUPE平台进行混合键合，在光子和电子域之间实现超短、高带宽的互连。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_050.png)

来源：英伟达

Quantum X800-Q3450中的两块铜质冷板置于交换机ASIC之上，构成闭环液冷系统，可高效散去每颗交换机ASIC产生的热量。连接冷板的黑色管路负责循环冷却液，以维持热稳定。该冷却系统对于维持ASIC以及相邻温度敏感的共封装光学（Co-packaged Optics，CPO）的热稳定性都至关重要。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_051.png)

来源：英伟达

### **Spectrum-X Photonics**

（当前译文已为专有名词，无需任何润色，直接保留）

Spectrum-X Photonics预计2026年下半年发布，将推出两款不同配置的交换机产品：一款是基于X800-Q3450 CPO交换机的以太网Spectrum-X变体，即Spectrum 6810，提供102.4T聚合带宽；另一款是其更大版本Spectrum 6800，采用四个独立的Spectrum-6多芯片模块（MCM），实现409.6T聚合带宽。

Quantum X800-Q3450 CPO交换机采用四个独立交换机封装，以多平面配置连接物理端口，每个交换机封装均为单芯片，包含28.8T交换机ASIC以及所需的SerDes和其他电气组件。相比之下，Spectrum-X Photonics的交换机硅片采用多芯片模块（MCM）设计，中心为尺寸更大的102.4T交换机ASIC，周围环绕八颗224G SerDes I/O芯粒——每边各两颗。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_052.png)

来源：英伟达

每个Spectrum-X Photonics多芯片模块交换机封装将在单个102.4T交换机封装中集成36个光引擎。该封装采用英伟达第二代光引擎，带宽3.2T，每个光引擎拥有16条200G光通道。其中32个光引擎正常工作，另外4个作为冗余备份，以防单个光引擎故障。这是因为光引擎被焊接在基板上，不易更换。

每个I/O芯粒可提供12.8T单向总带宽，包含64条SerDes通道，并与4个光学引擎接口。这使得Spectrum-X得以交付远超Quantum-X Photonics的聚合带宽，同时拥有更多SerDes岸线与面积。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_053.png)

来源：SemiAnalysis

Spectrum-X 6810交换机机箱采用一个上述交换机封装，即可交付102.4T聚合带宽。更大的Spectrum-X 6800交换机机箱SKU则为高密度机箱，通过四个上述Spectrum-X交换机封装实现409.6T聚合带宽，这些封装同样以多平面配置方式连接至外部物理端口。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_054.png)

来源：英伟达

与四颗ASIC、总带宽115.2T的Quantum X800-Q3450一样，Spectrum-X 6800通过内部分线，将每个端口物理直连全部四个ASIC。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_055.png)

来源：SemiAnalysis
