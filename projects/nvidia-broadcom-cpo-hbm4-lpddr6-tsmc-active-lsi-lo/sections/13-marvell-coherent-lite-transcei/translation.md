https://substackcdn.com/image/fetch/$s_!B76F!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc24a930f-d8f1-4622-96e6-9a39a7388ea5_2880x1620.jpeg

直接检测、精简相干与相干光模块对比。来源：Marvell，ISSCC 2026

Marvell 展示了一款用于精简相干（Coherent-Lite）应用的 800G 光模块。传统光模块的传输距离有限，通常小于 10 公里。相干光模块则支持远得多的距离，但其设计复杂、功耗更高且成本更昂贵。Marvell 的精简相干光模块旨在功耗、成本和传输距离之间取得平衡，这对于链路跨度最多数十公里的大型数据中心园区而言堪称完美。

https://substackcdn.com/image/fetch/$s_!1xhk!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9995a322-bad8-4a3c-97e1-b84fde0aa424_2880x1620.jpeg

相干与精简相干光模块的光波段对比。来源：Marvell，ISSCC 2026

相干光模块主要使用C波段波长，正是看中其低衰减特性。然而，使用相干传输的长距离链路通常色散非常高，需要大量的数字信号处理器（DSP）处理。对于建筑物之间仅相隔数十公里的数据中心园区而言，传统相干光学的超长传输距离往往显得大材小用。

精简相干光模块则转而使用 O 波段波长，该波段在数据中心园区相对较短的距离上色散近乎为零。这使得所需的 DSP 处理降至最低，从而节省了功耗并降低了延迟。

https://substackcdn.com/image/fetch/$s_!oACP!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0faa6bfc-c1c4-44bc-b8c8-c3b14f466c32_2880x1620.jpeg

Marvell 精简相干光模块架构。来源：Marvell，ISSCC 2026

精简相干光模块是一种基于数字信号处理器（DSP）的可插拔模块，包含两个 400G 通道。每个 400G 通道运行双偏振正交幅度调制（Dual-Polarization Quadrature Amplitude Modulation, DP-QAM），并由 X 和 Y 两个并行的调制流组成。

https://substackcdn.com/image/fetch/$s_!qDgr!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcc181023-63b7-4e6e-8769-eb69fdc1ca81_682x375.jpeg

Marvell 精简相干光模块实测链路性能。来源：Marvell，ISSCC 2026

本次演示的核心，在于展示其他几种专为园区应用优化的通道带宽扩展方法。

高阶调制结合使用 X 和 Y 轴的双偏振技术，实现了 400G 的通道带宽。如上图所示，每个通道有 8 比特，总共构成 32 个星座点。这 8 比特乘以 62.5 GBd 的信号速率，总计约 400G 的总带宽。

这种调制方案对业界来说并不陌生，但如今正被引入数据中心园区，用于那些距离较短的链路。

https://substackcdn.com/image/fetch/$s_!jtsE!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F79b51c03-3812-498e-8f41-b9465e2c8164_2880x1620.jpeg

Marvell 精简相干光模块性能与先前相干收发器的对比。来源：Marvell，ISSCC 2026

Marvell 的方案显著降低了功耗，在不包含硅光部分的情况下，功耗仅为 3.72 皮焦耳/比特，仅为其他全功能相干收发器的一半。其测量是在 40 公里光纤长度上进行的，延迟低于 300 纳秒。
