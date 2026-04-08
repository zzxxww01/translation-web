LPU 网络可分为纵向扩展的“C2C”网络，以及通过 Spectrum-X 与英伟达 GPU 交互的横向扩展网络。首先探讨纵向扩展网络，该网络可分为三部分：节点内、节点间/机架内、机架间。针对机架内的 C2C 连接，英伟达宣布单机架纵向扩展总带宽为 640TB/s，具体计算如下：256 LPUs x 90 lanes x 112Gbps/8 x 2 directions = 645TB/s。请注意，英伟达采用的是 112G 的线路速率，而非 100G 的有效数据速率。

#### 托盘内拓扑

https://substackcdn.com/image/fetch/$s_!i4Vn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff5b18381-6c96-4d0f-912e-e7978cc30446_1414x1617.png

来源：SemiAnalysis Networking 模型

在每个托盘或节点内，所有 16 个 LPU 均以全互联网状拓扑相互连接。每个 LPU 模块通过 4x100G 的 C2C 带宽与节点内的其他 15 个 LPU 相连。需要注意的是，这里的“C2C”与 NVLink 无关，而是 Groq 自有的纵向扩展互联架构。这些连接全部通过 PCB 走线实现，因此需要规格极高的 PCB 来支持如此庞大的布线密度。这也正是采用正反面贴装的原因：它缩短了所有 LPU 之间在“X”和“Y”轴上的距离，转而利用“Z”轴空间进行布线。

此外，每个 LPU 还有 1x100G 链路连接至一个 FPGA，而每个 FPGA 负责与 8 个 LPU 对接。这两个 FPGA 各自通过 8x PCIe Gen 5 链路连接至 CPU。由于 LPU 没有用于直接通信的 PCIe PHY，因此必须经过 FPGA 才能与 CPU 对接。

#### 节点间/机架内

https://substackcdn.com/image/fetch/$s_!xA-t!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F25d7c5ea-dce9-4703-9d95-eda3887a2e72_1066x1155.png

来源：SemiAnalysis Networking 模型

每个 LPU 连接到服务器中其他 15 个节点各一个 LPU。每条节点间链路的带宽为 2x100G，因此每个 LPU 引出 15x2x100G 的节点间链路。这些节点间链路通过铜缆背板实现连接。此外，每个 FPGA 也与其他每个节点中的一个 FPGA 相连，单条链路带宽为 25G 或 50G，总计 15x25G/50G。这同样通过背板进行路由。这意味着每个节点拥有 16 x 15 x 2 条用于节点间 C2C 的通道（lane），以及 2 x 15 条用于节点间 FPGA 的通道，总计 510 条通道，即 1020 对差分对（分别用于接收 Rx 和发送 Tx）。因此，背板共有 16 x 1020/2 = 8,160 对差分对——这里除以 2，是因为一个设备的发送（Tx）通道正好对应另一个设备的接收（Rx）通道。

#### 机架间

https://substackcdn.com/image/fetch/$s_!Wn2b!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Feaf1f2a7-972d-4d67-b1e8-aa596dcca070_3060x4100.png

来源：SemiAnalysis Networking 模型

最后是机架间 C2C 连接。每个 LPU 拥有 4x100G 通道，这些通道连接至 OSFP 笼（cages），用于跨 4 个机架连接 LPU。这种机架间向上扩展（scale-up）可以采用多种配置。一种方案是，每个 LPU 的 4x100G 通道接入同一个 OSFP 笼，每个 OSFP 接口引出来自 2 个 LPU 的 800G C2C 带宽。然而，为了实现更大的扇出（fan out），首选配置似乎是将 LPU 的每条 100G 通道分别接入 4 个独立的 OSFP 笼，每个 OSFP 笼引出来自 8 个 LPU 的 800G C2C 带宽。至于机架之间的网络连接方式，似乎采用了菊链配置（daisy chain configuration），每个 Node 0 分别连接到另外两个 Node 0。这些连接完全可以在 100G AEC（有源电缆）的传输距离内实现，当然，如有必要也可以使用光模块。
