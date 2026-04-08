VR NVL72 将液冷技术推向了新高度。VR NVL72 计算托盘实现了 100% 液冷，而 GB200 和 GB300 计算托盘则采用 85% 液冷与 15% 风冷的混合散热方案。因此，计算托盘彻底移除了风扇，并扩大了冷板的覆盖范围，以带走机箱前半部分的热量。机箱中部将设置内部歧管，用于向各个模块分配进水冷却液，并收集回水冷却液。计算托盘内的每个模块均将贴附冷板模块。各冷板模块通过 MQD（英伟达针对计算托盘内紧凑空间应用而制定的较小尺寸快速接头规范标准）与内部歧管相连。

https://substackcdn.com/image/fetch/$s_!Ra3T!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2397b285-cb78-4081-8813-51a223db97bb_1354x2343.png

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

冷却液从机箱左后侧通过 UQD 快速接头进入计算托盘。随后，冷却液经由管道进入内部歧管，并在此被分配至所有模块。冷却液在吸收不同模块的热量后，重新流回内部歧管。最后，冷却液从机箱右后侧通过 UQD 快速接头流出计算托盘。

https://substackcdn.com/image/fetch/$s_!DhHR!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fce22913e-61af-49e3-9487-fad91f7a8af7_2012x722.png

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

VR NVL72的冷板也进行了多项升级。对于每个Strata 模块，冷板将作为单一模块提供，覆盖整块Strata主板，包括两颗 Rubin GPU、一颗 Vera CPU、SOCAMM以及各种电压调节模块组件。Rubin GPU 的冷板升级为“微通道冷板”（MCCP）。本质上，冷板内部通道的间距从150微米缩小至100微米。这增加了表面积，从而提升了冷板的散热能力。此外，在与 Rubin GPU 接触的表面将镀有一层金。这样做的原因是防止液态金属铟（TIM2）对铜造成腐蚀。

https://substackcdn.com/image/fetch/$s_!P-4a!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F78fa8a53-ba67-4917-96be-3d5da6051095_1876x584.png

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

除了 Strata 模块，机箱前端的模块也将安装冷板模块。每个 Orchid 模块都将配备一个冷板模块，以覆盖 CX-9、E1.S SSD、光模块笼以及各类电压调节模块。由于两个 Orchid 模块在 1U 机箱内上下堆叠，其冷板与电路板的总高度将不到 0.5U。每对 Orchid 模块仅共享来自歧管的一对快速接头。系统内还会设置另一组歧管，负责将冷却液分配至这对 Orchid 模块的顶部与底部冷板。在我们的 VR NVL72 组件物料清单与功耗预算模型 中，我们详细列出了所有散热组件的具体内容，包括冷板模块、歧管以及快速接头。

https://substackcdn.com/image/fetch/$s_!Z-zU!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8e1b96be-6742-4679-8180-275aaad0521d_3164x999.png

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

此前，冷板通常在L10级组装阶段进行安装，即在该阶段将各类组件装配至机箱内。鉴于目前的模块化设计，冷板需要与模块本身实现更紧密的集成。因此，冷板将在PCBA流程之后的L6级组装阶段直接进行安装。这提升了整体的组装效率，因为L10级组装由此被简化为只需将成品模块插入对应的连接器与快速接头即可。
