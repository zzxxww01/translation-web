https://substackcdn.com/image/fetch/$s_!L-SD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffc1e02d7-2ca4-4129-9200-e99084fa4cfc_1792x1265.jpeg

英特尔 M3DProc 18A 与英特尔 3 芯片布局规划图。来源：英特尔，ISSCC 2026

英特尔首次披露了其采用混合键合技术的芯片 M3DProc。该芯片由一个英特尔 3 工艺的底层芯片和一个 18A 工艺的顶层芯片构成。每个芯片分别包含 56 个网格瓦片（mesh tile）、核心和深度神经网络（DNN）加速器瓦片。两个芯片通过间距为 9 微米的 Foveros Direct 混合键合技术互联。

https://substackcdn.com/image/fetch/$s_!Ysv3!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F636479de-4917-48f9-b513-7c57fe81968e_2494x1403.jpeg

英特尔 M3DProc 3D 网格架构。来源：英特尔，ISSCC 2026

这些网格单元以 14×4×2 的 3D 网格形式排列，SRAM（静态随机存取存储器）由上下两片芯片共享。

https://substackcdn.com/image/fetch/$s_!6vZe!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc2a08665-501d-4c3b-a54a-0bfae0dc5258_2412x910.jpeg

英特尔 M3DProc 2D 与 3D 架构的吞吐量及能效对比。来源：英特尔，ISSCC 2026

英特尔发现，3D网格架构能降低延迟，并将吞吐量提升近40%。他们还测试了数据传输的能效，其中2D架构的数据传输发生在底部芯片的56个网格单元内，而3D架构则跨越两个芯片上的28个相邻网格单元。结果显示，其混合键合互连（Hybrid Bonding Interconnect, HBI）对能效的影响微乎其微。

https://substackcdn.com/image/fetch/$s_!aWNv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4877bf3c-30c1-4278-b85e-65ddbc343f1b_1362x1400.jpeg

英特尔 M3DProc 单元键合布局规划图。来源：英特尔，ISSCC 2026

每个单元拥有552个焊盘，其中略少于一半用于数据传输，略少于四分之一用于供电。

在封装方面，M3DProc 与 Clearwater Forest (CWF) 类似。CWF 采用英特尔 3 工艺的基础芯片，通过9微米间距的 Foveros Direct 技术与 18A 工艺的计算芯片相连。

M3DProc 实现了 875 GB/s 的 3D 带宽，而每个 CWF 计算芯片仅能实现 210 GB/s。这款芯片的三维片上网络（3D NoC）拥有显著更高的带宽密度。具体而言，CWF 使用 Foveros Direct 技术，通过每个顶部芯片上6个集群（每个集群提供35GB/s的连接带宽）实现了CPU核心集群的L2缓存与基础芯片L3缓存的解耦，每个顶部芯片总带宽为210GB/s。相比之下，M3DProc 的 875GB/s 3D 带宽是通过56个垂直单元连接聚合实现的，每个连接在远小于（CWF方案中）单个连接的占位面积上提供了 15.6GB/s 的带宽。
