今年早些时候，在 GTC 2025 上，英伟达（NVIDIA）CEO 黄仁勋强调，仅收发器产生的巨大功耗便是推动 CPO 的关键动力。结合上表的单机架功耗预算，一个采用三层网络架构、规模达 20 万颗 GPU 的 GB300 NVL72 GPU集群（GPU cluster）（单机架包含 72 个 GPU 封装与 144 个计算小芯片），其关键 IT 功耗将高达 435 MW，其中仅光收发器就会消耗 17 MW。显然，若能剔除大部分收发器组件，必将节省巨量功耗。

将单个 800G DSP 收发器的功耗与 CPO 系统内部光引擎及激光源的功耗（按每 800G 带宽折算）进行对比，这一点便一目了然。单个 800G DR4 光收发器的功耗约为 16-17W，而据我们测算，英伟达 Q3450 CPO 交换机所采用的光引擎及外部激光源，每 800G 带宽功耗仅约为 4-5W，降幅高达 73%。

这些数据与 Meta 在 ECOC 2025 大会上发表并展示的论文数据极为接近。该报告指出，单个 800G 2xFR4 可插拔收发器的功耗约为 15W，而博通 Bailly 51.2T CPO 交换机内部的光引擎与激光源，每提供 800G 带宽的功耗约为 5.4W，功耗降幅达 65%。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_004.png)

来源：Meta

我们将把分析拓展至集群层面。以基于三层网络搭建的GB300 NVL72集群为例，不难发现：若后端网络从数字信号处理器（Digital Signal Processor，DSP）收发器改用线性驱动可插拔光学（Linear-drive Pluggable Optics，LPO）收发器，总光收发器功耗可降低36%，网络总功耗可降低16%。相比DSP光器件，全面转向共封装光学（co-packaged optics，CPO）可实现更大幅度的功耗节省——光收发器功耗降幅可达84%，不过部分功耗节省会被新增功耗抵消：交换机需要加装光引擎（optical engines，OE）和外部光源（external light sources，ELS），因此交换机总功耗会上升23%。在下述示例中，CPO方案下每台服务器的光收发器功耗底线为1000W，这是因为我们假设前端网络仍采用DSP收发器。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_005.png)

来源：SemiAnalysis AI Networking 模型

采用英伟达（NVIDIA）的 CPO 横向扩展交换机，实际上意味着默认采用高基数网络。不过，这一底层细节对最终用户而言被“抽象化”屏蔽了。在使用非 CPO 高基数交换机时，链路交织（shuffle）通常需要借助配线架或一分多分支线缆在交换机外部完成；而在 CPO 架构下，交织直接在交换机内部完成。取而代之的是，这些英伟达 CPO 交换机直接呈现出极高的端口数量——例如，Quantum 3450 提供 144 个 800G 端口，Spectrum 6800 提供 512 个 800G 端口。

我们之所以使用“默认”一词，是因为英伟达非 CPO 架构的 InfiniBand Quantum Q3400 交换机同样提供 144 个 800G 端口，而 QM9700 等其他 InfiniBand 交换机仅提供 32 个 800G 端口——只有前者通过“单机高基数”（high radix in a box）设计实现了海量有效端口。这种高端口数有望让客户将三层网络扁平化为两层，同时免去部署交织盒、配线架或笨重的一分多分支线缆的繁琐，这可能成为一大核心卖点。在两层网络架构下，与传统 DSP 光模块相比，光模块功耗降低 84%，交换机功耗下降 21%，整体网络功耗可减少 48%。

与 Spectrum 6810 相比，Spectrum 6800 交换机正是凭借其庞大的端口数量（在两种可用的逻辑配置下均为 512 个 800G 端口）实现了这一点。作为对比，Spectrum 6810 提供 128 个 800G 端口、256 个 400G 端口或 512 个 200G 端口。如果使用 Spectrum 6810 的 128 个 800G 端口配置，两层网络最多可连接 8,192 块 GPU；而配备 512 个 800G 端口的 Spectrum 6800 则可连接 131,072 块 GPU。

简单补充说明：在L层网络中，端口数为k的交换机可支持的最大主机数量由下式给出：

\(2(\frac{k}{2})^L\hspace{2cm}2(\frac{512}{2})^2\)

其中的奇妙之处在于，端口数 k 会以网络层数为指数进行幂运算。因此，对于两层网络而言，将每个端口的带宽减半（即把一个 800G 端口拆分为两个 400G 端口）以使逻辑端口数量翻倍——无论是采用内部重排（如 Spectrum 6800 那样）、分支线缆还是双端口光模块——都意味着所支持的主机数量将增至四倍！

截至目前本节讨论的功耗节省效果——三层CPO网络可节省23%，精简为两层CPO网络可节省48%——听起来十分可观，但问题在于，对于三层网络架构而言，网络部分本身仅占集群总功耗的9%。因此，切换为CPO对整体功耗的影响会被大幅稀释，至少在横向扩展网络中是如此。三层网络改用CPO后，网络功耗降低23%，但仅能带来2%的集群总功耗节省；精简为两层CPO网络后，网络功耗降低48%，也仅能带来4%的集群总功耗节省。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_006.png)

来源：SemiAnalysis AI Networking 模型

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_007.png)

来源：SemiAnalysis AI Networking 模型

从集群总资本成本的角度来看，情况也类似。
