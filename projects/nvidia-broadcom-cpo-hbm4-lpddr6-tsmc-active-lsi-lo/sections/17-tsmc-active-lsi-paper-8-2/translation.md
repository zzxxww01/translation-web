https://substackcdn.com/image/fetch/$s_!kR_h!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F903517c9-6ff3-4ac5-9d4a-c0130cb9cbea_2880x1620.jpeg

台积电（TSMC）无源与有源本地硅互连（aLSI）对比。来源：台积电，ISSCC 2026

台积电（TSMC）的先进封装部门展示了其有源本地硅互连（Active Local Silicon Interconnect, aLSI）方案。与标准的CoWoS-L或EMIB不同，aLSI改善了信号完整性，并降低了顶层裸片上物理层（PHY）和串行器/解串器（SerDes）的复杂度。

https://substackcdn.com/image/fetch/$s_!Gjwp!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa8f473a9-3f0e-4b7a-b717-2bc9999adae6_2880x1620.jpeg

台积电（TSMC）有源本地硅互连（aLSI）裸片到裸片链路概览。来源：台积电，ISSCC 2026

台积电展示的器件采用了32 Gb/s、类似UCIe的收发器。由于aLSI改善了信号完整性，收发器的面积得以减小，凸点间距也能从45微米缩减至38.8微米。更紧密的间距结合转向曼哈顿网格（Manhattan grid）的布局，使得物理层（PHY）的深度从1043微米降至850微米，从而节省了空间。设计者可将这些空间重新分配给计算、内存或输入/输出（IO）单元，或用于缩小裸片尺寸。需要指出的是，该收发器只是“类似UCIe”，并非真正的UCIe标准实现，因为UCIe标准强制要求六边形凸点排布，而非此处使用的曼哈顿网格。

随着设计者为下一代AI加速器竭力榨取每一寸裸片空间，转向aLSI技术已不可避免。

aLSI的‘有源’部分，体现在用有源晶体管构成的边沿触发收发器（Edge-Triggered Transceiver, ETT）电路，取代了桥接裸片中的无源长距离金属通道，从而在更长距离上维持信号完整性。这也降低了对顶层裸片发送/接收端口信号驱动能力的要求。aLSI内部的ETT电路仅额外增加0.07皮焦/比特（pJ/b）的能耗，最大限度地缓解了在堆叠裸片中加入有源电路可能引发的散热担忧。通过将信号调理电路移至桥接裸片，顶层裸片的发送/接收物理层（PHY）面积得以减小，这得益于可以使用更小的预驱动器和时钟缓冲器，并且接收端不再需要信号放大。

边沿触发收发器（ETT）集成了驱动器、交流耦合电容（Cac）、一个兼具负反馈与正反馈的放大器以及输出级。信号通过Cac时，会在其转换边沿引入峰值，随后由双环路放大器拾取，这便是其‘边沿触发’名称的由来。该放大器利用正负反馈环路来稳定电压水平。在此设计中，针对1.7毫米的通道长度，Cac设定为180 fF，裸片A和裸片B上的电阻分别为2kΩ和3kΩ。

https://substackcdn.com/image/fetch/$s_!wpmP!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc151958f-7fdb-4903-b06a-38a0eace27d5_2667x1500.jpeg

台积电（TSMC）集成eDTC的CoWoS-L供电方案。来源：台积电

这些aLSI桥接芯片还能在前端集成嵌入式深沟槽电容（eDTC），以改善对物理层（PHY）和裸片到裸片（D2D）控制器的供电。aLSI配合eDTC技术，不仅没有因为桥接芯片的存在而损害电源配送网络，反而能同时优化沿D2D接口的供电与信号布线。

https://substackcdn.com/image/fetch/$s_!Yp1W!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7d837ed3-5395-4e1a-b579-c95f1d9497cc_2880x1620.jpeg

台积电（TSMC）有源本地硅互连（aLSI）布线能力与横截面。来源：台积电，ISSCC 2026

仅需388微米的互连接口宽度，即可容纳64条发送（TX）和64条接收（RX）数据通道，总面积仅为0.330平方毫米。信号布线仅需占用最顶部的两层金属层，其余金属层可用于前端电路。

https://substackcdn.com/image/fetch/$s_!7zt3!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa2747466-8e4c-4447-ad94-6c2e8b71ea4a_2880x1620.jpeg

台积电（TSMC）有源本地硅互连（aLSI）在已知合格裸片（KGD）与已知合格封装（KGP）阶段的舒姆图。来源：台积电，ISSCC 2026

台积电介绍了有源本地硅互连（aLSI）的多阶段测试方案。首先是已知合格裸片（KGD）阶段，仅测试LSI裸片本身以进行裸片验证。其次是已知合格堆叠（KGS）阶段，此时系统级芯片（SoC）已通过LSI连接，以测试堆叠功能。最后是已知合格封装（KGP）阶段，对完整组装体进行全面测试，以验证其功能、性能和可靠性。

他们展示了在KGD和KGP阶段的舒姆图。两张图均显示，该互连技术在0.75V电压下达到了32 Gb/s的速度，在0.95V电压下则达到了38.4 Gb/s。

https://substackcdn.com/image/fetch/$s_!jY_b!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff44de7d8-9b9f-4086-a305-6c16677e9895_2880x1620.jpeg

台积电（TSMC）有源本地硅互连（aLSI）芯片显微照片与功耗分解。来源：台积电，ISSCC 2026

该封装体展示了两颗系统级芯片（SoC）裸片和两颗输入/输出（IO）裸片。有趣的是，这个测试载具的设计似乎与AMD的MI450图形处理器（GPU）相符，包含两颗相互连接的基础裸片、12个HBM4堆栈以及两颗集成有源本地硅互连（aLSI）的IO裸片。其特点是，并非每个HBM4堆栈都拥有独立的aLSI，而是每两个共享一个。

在功耗方面，在0.75V电压下，总功耗仅为0.36皮焦耳/比特（pJ/b），其中有源本地硅互连（aLSI）中的嵌入式硅桥（ETT）部分仅消耗0.07 pJ/b。下图是与其他裸片到裸片（D2D）解决方案的对比。

https://substackcdn.com/image/fetch/$s_!GHcE!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd194a9ff-d0ee-4e74-98a9-1f426f98205c_2880x1620.jpeg

台积电（TSMC）有源本地硅互连（aLSI）与其他裸片间互连技术的对比。来源：台积电，ISSCC 2026
