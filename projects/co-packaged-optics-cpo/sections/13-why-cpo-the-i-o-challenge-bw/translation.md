除了摆脱功耗高且昂贵的数字信号处理器（DSP），并最小化或消除LR SerDes的使用之外，采用共封装光学（CPO）还能带来另一大优势——在相同能耗下实现更高的互连带宽密度。

带宽密度衡量的是单位面积或通道所能传输的数据量，反映了在有限空间内实现高速数据传输的效率。能效则量化了传输单位数据所需的能量。

因此，相对于能耗的互连带宽密度，是评估特定互连技术客观质量时非常重要的品质因数（FoM）。当然，最优的互连方案还必须同时满足距离和成本参数的要求。

观察下方的图表可以发现一个明显趋势：随着距离增加，电互连的这一品质因数会呈指数级恶化。此外，从纯电气接口转向需要进行光电转换的接口时，效率会大幅下降——可能达到一个数量级。这种下降是因为需要消耗能量将信号从芯片驱动到前面板收发器所在的位置，而为光学数字信号处理器（DSP）供电则需要更多能量。CPO的品质因数曲线则明显优于可插拔方案。如图所示，在相同距离范围内，CPO能在单位面积和单位能耗下提供更高的带宽密度，因此从客观上讲是一种更优的互连技术。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_023.png)

来源：G Keeler，DARPA 2019，SemiAnalysis

这张图表也印证了一句老话：“能用铜缆的地方就用铜缆，必须时才用光学。”在可行的范围内，较短距离的铜缆通信性能更优。英伟达深谙此道，其机架级GPU架构专门为了突破机架内密度极限，最大化通过铜缆互联的GPU数量。这正是GB200 NVL72所采用的纵向扩展网络架构背后的逻辑，英伟达在其Kyber机架中将这一理念进一步发扬光大。然而，随着CPO技术逐渐成熟，其对应的FoM曲线部分终将变得可用，从性能与总拥有成本（TCO）的角度来看也将值得采用。

- GB200 Hardware Architecture - Component Supply Chain & BOM

- NVIDIA GTC 2025 - Built For Reasoning, Vera Rubin, Kyber, CPO, Dynamo Inference, Jensen Math, Feynman

### **修订后的译文：**

I/O 瓶颈与障碍

（说明：根据 readability 问题及中文科技文章标题习惯，采用建议的简化形式“I/O瓶颈与障碍”，保留英文缩写在前，符合目标读者的专业阅读预期，同时消除原译文“输入/输出（I/O）”的冗余翻译腔。）

尽管晶体管密度和计算能力（以FLOPS为代表）已经实现了良好扩展，但I/O的扩展速度却慢得多，从而在整体系统性能上形成了瓶颈：芯片外部I/O可用的边缘面积非常有限，因为数据必须通过有机封装基板上数量有限的I/O引出。

此外，提升单个I/O的信号速率正变得越来越困难且功耗更高，进一步限制了数据搬运。这也是过去数十年间互连带宽相比其他计算趋势扩展如此缓慢的关键原因。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_024.png)

来源：Amir Gholami

用于HPC应用的封装外I/O密度已趋于平稳，主要受限于单颗倒装芯片BGA封装所能容纳的凸点数量。这直接制约了逃逸带宽的扩展。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_025.png)

来源：台积电

### 电气SerDes扩展瓶颈

在I/O数量受限的情况下，要实现更高的逃逸带宽，就必须提高每个I/O的信号频率。目前英伟达和博通处于SerDes IP的最前沿。英伟达在布莱克韦尔（Blackwell）中已量产224G SerDes，这使其能够实现极快的NVLink。同样，博通自2024年底开始在其光DSP中提供224G SerDes样品。这绝非巧合——两家出货AI FLOPS最多的公司，同时也在高速SerDes IP领域处于领先地位。这进一步印证了AI性能与吞吐量之间的根本联系——最大化数据搬运效率与提供原始计算能力同等关键。

然而，在期望的传输距离上提供更高线速正变得越来越具挑战性。随着频率升高，插入损耗也会上升，如下图所示。我们可以看到，在更高的SerDes信号速率下，尤其当信号路径变长时，损耗会显著增加。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_026.png)

来源：Broadcom

SerDes扩展正接近平台期。更高速率只有在极短距离内才能维持，而无需额外信号恢复组件——但这些组件又会增加复杂度、成本、延迟和功耗。要达到224G SerDes已相当不易。

展望448G SerDes，能够驱动超过几厘米距离的可行性仍存在较大不确定性。英伟达在鲁宾（Rubin）中通过采用双向SerDes技术，实现了每电气通道448G的连接性。而要实现真正的448G单向SerDes，还需要进一步发展。我们可能需要转向更高阶的调制方式，如PAM6或PAM8，而不是自56G SerDes时代以来一直广泛使用的PAM4调制。使用PAM4（每个信号编码2比特）来达到448G将需要244Gbaud的波特率，由于过高的功耗和插入损耗，这很可能难以实现。

### SerDes扩展平台期成为NVLink扩展的障碍

在NVLink协议中，NVLink 5.0的带宽相比NVLink 1.0提升了超过11倍。然而，这一增长并非主要来自通道数量的大幅增加——通道数仅从NVLink 1.0的32条略微增加到NVLink 5.0的36条。扩展的关键驱动力是SerDes通道速率提升了10倍，从20G提高到200G。而在NVLink 6.0中，英伟达预计仍将采用200G SerDes，这意味着它必须实现通道数量翻倍——其巧妙地通过双向SerDes技术，在使用相同数量物理铜线的情况下，有效将通道数翻倍。

除此之外，进一步提升SerDes速率或克服有限边缘空间以容纳更多通道将变得越来越困难，总逃逸带宽也将因此受限。

对处于技术前沿的企业而言，扩展逃逸带宽至关重要，因为吞吐量是重要的差异化因素。对于英伟达来说，其NVLink规模化互连架构是一道重要护城河，这一瓶颈可能会让AMD以及超大规模云厂商等竞争对手更容易迎头赶上。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_027.png)

来源：英伟达（NVIDIA），SemiAnalysis

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_028.png)

来源：英伟达（NVIDIA），SemiAnalysis

解决这一困境的方案——或者说必要的折中——是尽可能缩短电气I/O距离，并将数据传输卸载到尽可能靠近主机ASIC的光学链路上，以实现更高的带宽。这正是共封装光学（Co-packaged Optics, CPO）被视为互连技术“圣杯”的原因。CPO允许光学通信在ASIC封装内实现，无论是通过基板还是中介层。电气信号只需在封装基板中传输几毫米距离，理想情况下甚至可以通过质量更高的中介层实现更短距离，而无需经过数十厘米具有高损耗的覆铜箔层压板（Copper Clad Laminate, CCL）。

SerDes因此可以针对更短传输距离进行优化，所需电路远少于等效的长距离SerDes。这不仅简化了设计，还降低了功耗和硅面积。这种简化使得更高速度的SerDes更容易实现，并延长了SerDes扩展路线图。尽管如此，我们仍受限于传统的带宽模型，即带宽密度继续与SerDes速率成比例扩展。

为了实现更高的带宽密度，在极短距离上采用宽接口PHY是比极端高速SerDes更好的选择，它能提供优于SerDes接口的每功耗带宽密度。宽接口也需要更为先进的封装。然而，在CPO的情况下，这一点已不再是问题：封装本身已经高度先进，因此集成宽接口PHY几乎不会增加额外的封装复杂度。
