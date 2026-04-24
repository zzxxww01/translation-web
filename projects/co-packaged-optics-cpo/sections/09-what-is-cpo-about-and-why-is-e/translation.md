共封装光学（CPO）将光引擎直接集成于高性能计算或网络ASIC的同一封装或模块内。这些光引擎负责将电信号转换为光信号，从而实现光链路的高速数据传输。传输距离超过几米时，必须采用光链路，因为铜缆高速电通信无法逾越几米。

目前，大多数电光转换通过可插拔光收发器完成。在这种方案中，电信号从交换机或处理器芯片出发，历经数十厘米乃至更长的PCB走线，抵达机箱前面板或后面板的可插拔收发器笼。可插拔光收发器安装在该笼内，接收电信号后，由数字信号处理器（DSP）芯片进行信号重整，再发送至光学引擎组件，将电信号转换为光信号。

随后，光信号经光纤传至链路另一端，对端收发器逆向运作，将光信号重新转为电信号，最终送达目标芯片。

在这个过程中，电信号需在铜介质上经历较长距离、多个转换节点才能抵达光链路。这会导致信号劣化，需要大量功耗和复杂电路（即SerDes）来驱动与恢复。为改善这一状况，必须缩短电信号的传输距离。这便引出了“共封装光学”的概念，即将原本置于可插拔收发器中的光引擎与主机芯片共同封装。这一改变可将电走线长度从数十厘米缩短至数十毫米，因为光引擎已非常靠近XPU或交换ASIC。

这大幅降低功耗、提升带宽密度，并通过缩短电互连距离、缓解信号完整性问题来降低延迟。

下方的示意图展示了一种共封装光学（CPO）实现方式，其中光引擎（OE）与计算芯片或交换芯片同封装共置。初期光引擎（OE）将置于基板之上，未来则进一步集成至中介层（interposer）上。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_014.png)

来源：SemiAnalysis

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_015.png)

来源：SemiAnalysis

目前，前置可插拔光学方案（如下图所示）已十分普遍。该图核心在于，电信号需跨越15–30厘米长的铜走线或飞线，才能抵达收发器中的光学引擎。如前所述，这也要求必须采用长距（LR）SerDes来驱动可插拔模块。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_016.png)

来源：SemiAnalysis

此外，在CPO与传统前置可插拔光学之间，还存在一些中间实现方案，例如近封装光学（NPO）和板上光学（OBO）。

近年来，近封装光学（NPO）已成为迈向共封装光学（CPO）的中间过渡方案。NPO存在多种定义，其核心特征是光引擎（OE）不直接安装在ASIC的基板上，而是共同封装于另一块基板。光引擎仍可插拔，能够与基板分离。电信号仍需从XPU封装内的SerDes出发，经一段铜通道才能抵达光引擎。

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_017.png)

来源：SemiAnalysis

此外还有板上光学（OBO），它将光引擎集成在机箱内的系统PCB上，使其更靠近主ASIC。不过，OBO继承了共封装光学（CPO）的诸多复杂性，却在带宽密度和功耗节省方面提供的益处更少。我们视OBO为“两头不讨好”的方案，因为它兼具CPO的复杂性，又未能摆脱前置可插拔光学的部分局限。

https://substack-post-media.s3.amazonaws.com/public/images/faa2a72c-e270-4e1f-a13f-a0fe827c9b66_1024x276.png

来源：SemiAnalysis
