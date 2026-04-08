宽专家并行（WideEP）与分离式 Prefill 是两项独立的技术，但业界常将其组合使用以实现帕累托最优性能。本节我们将剖析 InferenceX 的实际测试结果，帮助大家建立直观认知：在不同的交互性水平下，究竟该如何合理搭配并行策略、宽 EP 与分离式 Prefill。

首先需要厘清，在单节点配置下，不同的并行策略分别落在帕累托前沿的哪个区间。以采用 TRT-LLM 框架、运行在单个 8-GPU B200 节点上的 DeepSeek R1 FP4 8k/1k 为例。随着我们在帕累托前沿上移动，最优策略也会随之切换，这主要由 Batch Size 及其对专家激活密度的影响所驱动。

在最高交互性区间（Batch Size 1-16），纯张量并行 (TP) 的表现全方位碾压任何包含专家并行 (EP) 的配置。在小 Batch Size 下，每步仅有极小比例的专家被激活。若采用 EP，这些激活负载在各 GPU 间的分布极不均衡：当 Batch Size 为 4 时，256 个专家中仅有 32 个被激活，在任意给定层中，单块 GPU 接收不到任何路由 token 的概率高达 10% 出头。TP 则通过将每个专家切分至所有 GPU 来规避此问题，因此无论路由器选中哪些专家，8 块 GPU 都能均等参与每一次专家计算。我们在对 DeepSeek R1 进行性能分析时，收集了专家激活率与 Batch Size 的对比数据，结果印证了当 Batch Size 在 16 及以下时，单层专家激活率确实极低。

https://substackcdn.com/image/fetch/$s_!M1tW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5ca10b5a-f80e-45b4-8d22-e3134d30b54d_2232x1446.png

来源：SemiAnalysis

随着我们下探至交互性稍降的区间，Batch Size 依然偏小，专家权重仍通过 TP 而非 EP 进行切分。真正的转折点出现在 Batch Size 32 附近，此时单层约有 50-60% 的专家被激活。达到该密度后，EP 的负载不均衡已在可容忍范围内，且其 token 路由开销要低于 TP 强制要求的单专家全归约 (All-reduce) 成本。这一区间的配置开始采用张量-专家并行 (TEP)：注意力机制走张量并行（所有 GPU 协同完成每次注意力计算），混合专家 (MoE) 层走专家并行（专家被分配至特定 GPU，并辅以全对全 (All-to-all) 路由）。

在帕累托前沿上吞吐量最高、交互性最低的区间，Batch Size 极大（128+），配置全面转向完整的数据-专家并行 (DEP)：注意力权重作为独立的数据并行 Rank 在所有 GPU 上被完全复制，专家则通过 EP 进行分布式部署。系统以牺牲单 token 延迟为代价，将批处理容量压榨到极限；注意力权重在所有 DP Rank 上的完全复制，最终实现了吞吐量的最大化。

https://substackcdn.com/image/fetch/$s_!Qbqv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd13280a5-ddc2-4610-84bb-bf470301cc8e_2086x1233.png

来源：SemiAnalysis InferenceX

当我们将分离式 Prefill 扩展到宽专家并行 (WideEP) 场景时，也观察到同样的通用模式。Prefill 和 decode 阶段采用各自独立的并行策略和节点数量，两者都针对具体的工作负载和目标交互性进行精细调优。以帕累托前沿上高吞吐、低交互性的一端为例，处理一个 8k/1k 工作负载（预填充任务繁重）。此时，Prefill 阶段是瓶颈，因为每个请求都需要对 8192 个输入 token 进行前向传播，计算开销极大。因此，该区间的方案会分配比 decode 节点更多的 prefill 节点（如 4P1D (4个Prefill节点，1个Decode节点)、7P2D、4P3D），以维持高 prefill 吞吐量。这些 prefill 节点运行数据-专家并行 (DEP) 配置，将注意力权重复制到各个独立的数据并行 Rank 上，从而实现对多个长上下文 prefill 请求的并行处理。

Decode 节点的数量较少，但其运行原理与单节点配置相同，即采用宽数据-专家并行 (wide DEP) 模式来处理大批量请求。

在帕累托前沿上追求高交互性的一端，并发请求数量较少，因此单个 prefill 实例就能跟上输入需求。然而，每个请求仍需要 1024 个 decode 步骤，而要实现高交互性，这些步骤就必须快。因此，该区间的方案转向分配比 prefill 节点更多的 decode 节点（如 1P3D、1P4D），每个 decode 实例都以小批量 (low batch size) 方式运行张量-专家并行 (TEP)。注意力计算上的张量并行通过将计算分片到实例内的所有 GPU 上，最大限度地降低了每一步的延迟；与此同时，在中等 Batch Size 这一负载均衡已足够高效的区间，专家并行 (EP) 负责处理混合专家 (MoE) 的路由。最终，通过采用多个小批量 decode 实例，而非少数几个大批量实例，既保持了较低的单 token 延迟，又提供了足够的并发服务能力。

https://substackcdn.com/image/fetch/$s_!LpAb!,w_474,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F61e2a61e-1b95-4ecb-a03d-061d15615c40_2086x1214.png

来源：SemiAnalysis InferenceX
