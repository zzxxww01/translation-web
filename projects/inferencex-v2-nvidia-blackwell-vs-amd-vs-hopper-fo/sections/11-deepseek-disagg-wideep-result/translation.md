在几乎所有的交互性下，就单卡总 token 吞吐量而言，Disagg (分离) 架构的表现均超越了聚合式推理（灰线）。多节点分离式预填充对单节点聚合式服务实现了全方位的性能碾压。

https://substackcdn.com/image/fetch/$s_!aeCq!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7ace6118-029a-44df-b0ef-2e7595e6f388_2032x1339.png

来源：SemiAnalysis InferenceX

英伟达仍在持续为 B200/GB200 FP8 推送更新。最新数据对比了 DeepSeek FP8 B200 TRT 单节点（开启/关闭 MTP）与 GB200 Dynamo+TRT Disagg (分离)（开启/关闭 MTP）的性能表现。这表明其在优化机架级推理软件与 WideEP（宽专家并行）算子方面，投入了持之以恒的工程心血。

https://substackcdn.com/image/fetch/$s_!s0zP!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F29485790-238d-4e1d-aa48-0559c79c9855_2132x1247.png

来源：SemiAnalysis InferenceX

在对比 MI355X 的分离式推理与聚合式推理时，我们观察到了类似的规律。只有在低交互性、大 Batch Size 的场景下，分离式推理才能反超聚合式推理。这一现象在 FP4 精度下依然成立，其罪魁祸首很可能是算子优化严重拉胯。

https://substackcdn.com/image/fetch/$s_!wwi4!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F25a7c41e-fa99-4117-8e49-ac121a22bf0f_2092x1241.png

来源：SemiAnalysis InferenceX

在 MI355X 上将 Disagg (分离) 预填充与宽专家并行（WideEP）结合并运行 FP4 时，我们发现其性能表现堪忧。

尽管理论建模表明，MI355X 上的 Disagg 推理性能理应远超单节点，但在要求更高交互性的场景下，Disagg 的实际表现反而更差。究其原因，当叠加使用多种 SOTA (业界领先) 推理优化技术时，ROCm 软件栈缺乏相应的 Kernel 与集合通信优化。

https://substackcdn.com/image/fetch/$s_!PqhO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2d82d32f-089b-405d-b4ef-94b4956676ed_2078x1233.png

来源：SemiAnalysis InferenceX

### 英伟达 TensorRT LLM 与 NVL72

TensorRT LLM 已经在 TogetherAI 等全球先进服务商中，每小时处理着数十亿个 Token。它真正让 GB200 NVL72 和 GB300 NVL72 大放异彩，在高吞吐量场景下实现了两倍以上的性能跃升。MTP 则进一步推高了这一成绩，充分榨取了芯片的全部潜能。

https://substackcdn.com/image/fetch/$s_!NgC9!,w_720,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd4628887-37be-4563-ad68-091282e20ddf_2350x1486.png

来源：SemiAnalysis InferenceX

观察成本图表，NVL72 系列凭借更大的 World Size 带来的优势同样显而易见。在 60 tok/s/user 的固定交互性下，单张 GB200 NVL GPU 产出的 tokens/s 略低于单张 B200 的三倍。

SemiAnalysis InferenceX 是免费开源软件，由读者提供支持。如需接收最新文章并支持我们的工作，请考虑成为免费或付费订阅者。

https://substackcdn.com/image/fetch/$s_!_KKs!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F36087d46-94e1-4629-90cb-4b0dfad1a8c1_1856x827.png

来源：SemiAnalysis InferenceX

随着交互性的提升，这一差距不断缩小。在 130 tok/s/user 时，GB200 NVL72 几乎毫无优势，按每百万 Token 成本计算甚至更为昂贵。在低 Batch Size 下，推理工作负载大幅缩减，足以塞进单个 HGX 节点的 NVLink 域（即 8 张 GPU）内，此时 GB200 NVL72 更大的横向扩展 (Scale-out) 优势便开始消退。

https://substackcdn.com/image/fetch/$s_!RyLb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3e287d0e-947f-4fd7-9dc8-d697fad9ac7d_1781x822.png

来源：SemiAnalysis InferenceX
