我们之前曾撰文探讨过 SRAM 在存储层级中的作用，简而言之，SRAM 速度极快（低延迟且高带宽），但这是以牺牲密度为代价的，因此成本高昂。

因此，像 Groq 的 LPU 这样的 SRAM 机器能够实现极快的首个 token 生成时间和每用户每秒 token 数，但这以牺牲总吞吐量为代价。因为它们有限的 SRAM 容量很快就会被权重占满，几乎没有剩余空间留给随着批处理用户增多而不断增长的 KVcache。正如我们所展示的，GPU 在吞吐量和成本方面胜出。这就是为什么英伟达决定将这两种架构结合以实现优势互补：在像 LPU 这样低延迟、搭载大量 SRAM 的芯片上，加速那些对延迟更敏感且内存需求不大的解码部分；而将极其消耗内存的注意力机制交由配备大量快速（尽管不及 SRAM 快）内存容量的 GPU 来执行。

https://substackcdn.com/image/fetch/$s_!6Cix!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa939a961-40da-4762-b7d2-1ebb2423e9a2_2188x350.png

来源：SemiAnalysis

这就引出了 Groq 3 LPU 或 LP30，而第二代 LPU 则被直接跳过。这款芯片没有英伟达的设计参与。影响第二代的 SerDes 问题似乎已得到修复。在付费内容中，我们将揭晓 SerDes IP 供应商，这可能会让人感到意外。英伟达还发布了 LP35，这是 LP30 的小幅更新版本，它将继续采用 SF4，并需要重新流片。它将集成 NVFP4 数值格式，但考虑到英伟达目前优先保证上市时间，我们预计不会有其他重大的设计变更。

https://substackcdn.com/image/fetch/$s_!iPH0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F39025ad5-927c-4619-b929-88d5555be853_1590x860.jpeg

来源：英伟达

LPU 3 接近光罩极限尺寸的裸片布局与 LPU 1 非常相似。很大一部分面积被 500MB 的片上 SRAM 占据，只有极少部分面积分配给提供 1.2 PFLOPs FP8 算力的 MatMul 核心——这仅为英伟达 GPU 算力的一小部分。相比之下，LPU 1 拥有 230MB 的 SRAM 和 750 TFLOPs 的 INT8 算力，性能的提升主要得益于从 GF16 到 SF4 的制程节点迁移。由于采用单片式裸片设计，因此不需要先进封装。

依赖 SF4 的好处之一是它不会像台积电的 N3 制程那样受到产能限制，这种限制给加速器产量设定了上限，也是整个行业仍然面临算力瓶颈的关键原因。此外，该设计也不需要使用同样受限于产能的 HBM。这使得英伟达能够扩大 LPU 的生产规模，而无需牺牲或挤占其宝贵的台积电或 HBM 产能配额。这代表了其他任何人都无法获取的真正增量收入与产能。

既然英伟达已经接手，下一代 LP40 将采用台积电 N3P 制程制造并使用 CoWoS-R 封装。英伟达将注入更多自有 IP，例如支持 NVLink 协议而非 Groq 的 C2C。这将是首款与 Feynman 平台进行深度协同设计的 LPU。Groq 原计划的第四代 LPU 同样由台积电代工，并由 Alchip 作为后端设计合作伙伴。由于英伟达能够自行完成后端设计，Alchip 的参与现已显得多余。计划中的一项技术创新是采用混合键合 DRAM 来扩展片上内存，与 SRAM 相比，其延迟和带宽仅有轻微下降，但性能远高于传统 DRAM。SK海力士已被选定为用于 3D 堆叠的 DRAM 供应商。

所有这些以及更多细节，早在此前的加速器模型中就已有详述。

https://substackcdn.com/image/fetch/$s_!4-mW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbf0a9df3-57f3-43b2-a090-67f9dbdee3d9_2218x1215.png

来源：Nvidia, SemiAnalysis Accelerator 模型
