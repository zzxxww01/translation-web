Ayar Labs的产品是其TeraPHY光引擎芯粒，可封装到XPU、交换机ASIC或内存中。第一代TeraPHY可在仅消耗10W功耗的情况下提供2Tbit/s单向带宽。第二代TeraPHY则提供4Tbit/s单向带宽。它是全球首个支持UCIe的光重定时器芯粒，能在芯粒内部完成电光（E/O）转换，直接将主机信号以光信号形式向外传输。选择UCIe接口使其对客户更具吸引力，因为这是一种标准化接口，可轻松集成到他们的主机芯片中。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_065.png)

来源：Ayar Labs

Ayar Labs前两代TeraPHY采用GlobalFoundries 45nm工艺，以单片式集成方案制造，集成了电子电路和硅光子器件，而第三代TeraPHY则转向采用台积电COUPE。这种将微环调制器、波导和控制电路紧密集成的方式有助于降低电损耗。不过，前两代所使用的成熟单片工艺节点限制了电子集成电路（EIC）的性能，这也是前几代TeraPHY采用较低调制速率的主要原因。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_066.png)

来源：Ayar Labs

在代号为“Eagle”的第二代4 Tbit/s单向TeraPHY中，TeraPHY集成了八个512 Gbit/s的I/O端口，每个端口基于32 Gbit/s NRZ × 16波长架构，由微环调制器（MRM）负责调制。其外部激光光源名为SuperNova，由瑞典Sivers公司提供。该激光器使用DWDM技术将16个波长（“颜色”）合并到一根光纤中。每个端口使用一对单模光纤分别进行发送（Tx）和接收（Rx），意味着每个4T芯粒总共需要连接24根光纤——16根用于Rx/Tx，8根用于激光输入。公司在封装工艺中采用边缘耦合（EC），但也支持光栅耦合（GC）。

在提升单芯粒带宽方面，公司指出，随着连接器技术的进步，目前每个芯粒24根光纤的密度在未来几年内有望实现翻倍。此外，通过提高单波长数据速率，每个端口/光纤的带宽也能翻倍，从而在近期路线图中实现整体4倍的带宽扩展。

SuperNova激光器符合MSA（Multi-Source Agreement，多源协议）标准，可与其他符合CW-WDM标准的光学组件互操作。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_067.png)

Souce: Ayar Labs

Ayar Labs第三代TeraPHY转向采用台积电COUPE，每个光引擎可提供超过第二代3倍的带宽，达到13.5 Tbit/s单向带宽。8个光引擎可为XPU解决方案提供约108 Tbit/s的总封装纵向扩展带宽，该方案是Ayar Labs与Alchip合作推出的。这一约13.5+Tbit/s的带宽是通过每个波长约200 Gbit/s、采用PAM4调制实现的。

虽然Ayar Labs尚未披露确切的端口架构（即DWDM波长数量、每个FAU的光纤数等），但其采用双向光链路意味着它最多需要约64根光纤用于Tx和Rx，另外还需要数十根光纤连接外部激光光源。不过，Ayar Labs始终坚持采用WDM技术，因此每个FAU的总光纤数有望低至32根。与前两代一样，第三代TeraPHY继续使用微环调制器，使光芯粒保持较小尺寸，同时以CWDM或DWDM作为未来带宽扩展的手段。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_068.png)

来源：Ayar Labs，Alchip

Ayar Labs 还与 Alchip 和 GUC 合作，将其芯粒集成到 Alchip 和 GUC 的 XPU 解决方案中。上图展示了一个包含两个掩膜版尺寸计算芯片和 8 个 TeraPHY 光引擎的 XPU，该方案可提供高达 108 Tbit/s 单向带宽。

在 Hot Chips 2025 大会上，Ayar Labs 分享了慢速热循环链路测试结果——在约 5°C/min 的速率下进行了超过四小时的热循环，整个过程中链路误码率始终保持良好。

https://substack-post-media.s3.amazonaws.com/public/images/362d0b77-974d-435d-acca-af5d8464b34c_3030x1684.png

来源：Ayar Labs

然而，研究 MRM 对温度快速变化的适应能力，与证明链路在宽温度范围内长期稳定同样重要。在同一场 Hot Chips 演讲中，Ayar Labs 解释了他们如何通过扫描激光波长来模拟快速温度变化，而非使用一个真正能在 0~500W 功耗阶跃的封装内 ASIC。控制电路会检测环形谐振是否发生漂移——这可能是由于输入激光波长改变或环温度变化所致，因此他们以对应等效温度变化的速率扫描激光波长。例如，20nm/s 的扫描速率可模拟 0.2 秒内 64°C 的温度变化，相当于 320°C/s。

该研究显示，在高达 800°C/s 的温度变化下仍未出现误码。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_069.png)

来源：Ayar Labs

Ayar Labs 拥有广泛的战略投资者，包括 GlobalFoundries、Intel Capital、NVIDIA、AMD、TSMC、Lockheed Martin、Applied Materials 和 Downing。
