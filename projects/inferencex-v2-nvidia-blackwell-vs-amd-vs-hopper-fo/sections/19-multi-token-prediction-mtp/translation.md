投机解码通过使用一个小巧且成本低廉的草稿模型提前预测几个 token，从而降低自回归生成的成本。随后，大模型在一次类似预填充计算的前向传播中，对这些预测的 token 进行校验。对于给定的输入序列长度，当输入增加 N 个 token 时，单次前向传播的耗时基本不变。投机解码正是利用了这一特性，先在较小的模型上运行推理，为大模型起草多个 token，大模型只需一次前向传播即可完成校验，从而在相近的时间预算内最多额外生成 N 个 token。

https://substackcdn.com/image/fetch/$s_!V6f0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb2b2aa12-c308-4f4b-84f7-969228600ce5_2296x1126.png

来源：Brendan Bycroft

这种“在相同时间预算内生成额外 token”的假设在稠密模型中最为成立，因为批处理校验可以在多个位置复用同一权重流。而对于混合专家（MoE）模型，不同的 token 可能会被路由到不同的专家，因此校验多个草稿 token 激活的专家数量会多于单 token 解码，迫使系统从内存中读取更多专家权重。正如 EAGLE 论文中 Mixtral 8x7B Instruct 模型的结果所示，这种额外的内存流量吞噬了省下的带宽红利，甚至可能导致校验阶段的耗时与标准解码步骤相差无几。

多 Token 预测（MTP）追求类似的收益，但无需单独的草稿模型。通过在模型架构中加入辅助预测头，单一模型就能基于相同的底层表示预测未来几个 token。这改善了分布对齐，因为预测结果和最终评分均出自同一模型。MTP 还能在支持多 token 生成策略的同时，避免部署额外模型带来的运维复杂性，不过它要求 MTP 预测头必须与主模型一起进行预训练。

https://substackcdn.com/image/fetch/$s_!KL8_!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F27ee5a46-78b5-40dd-b76d-1f096e0ae06d_1755x1154.png

来源：SemiAnalysis InferenceX

在所有 SKU 上，启用 MTP 都能带来性能提升。通过利用通常闲置的 Logits 来校验额外的 token，该方法仅引入微乎其微的计算开销，却能在解码期间省下昂贵的额外权重加载成本。

https://substackcdn.com/image/fetch/$s_!HkQ0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffb5fc8fa-d129-475c-bb87-664e08bc6179_1773x1151.png

来源：SemiAnalysis InferenceX

在大 Batch Size 下，推理过程受内存带宽的限制弱于低 Batch Size 场景。投机解码（包含 MTP）的本质是用冗余算力换取更少的访存受限解码步数。因此，投机 Token 带来的额外校验工作可能无法完美填补算力空隙（slack）。这导致在大 Batch Size 下的性能提升幅度较小。

成本方面，MTP 能带来巨幅节省。下表显示，使用 Dynamo TRT 以 FP4 精度运行 DeepSeek-R1-0528 时，每百万总 Token 成本为 0.251 美元。一旦启用 MTP，该成本便一路陡降至仅 0.057 美元。

https://substackcdn.com/image/fetch/$s_!_ljZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdcf44984-9cb9-49ae-b35a-aeb5b5d14244_1566x1778.png

来源：SemiAnalysis InferenceX

在所有配置下，只要控制其他变量不变，搭配 DeepSeek R1 使用 MTP 均能提升交互性。且该操作对模型精度并无显著影响。这与 DeepSeek V3 技术报告的结论高度吻合。

https://substackcdn.com/image/fetch/$s_!MXVB!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1143164c-b38f-4ca9-888a-e9e270d6ef48_1757x1187.png

来源：SemiAnalysis InferenceX

关于 MTP 性能数据的有效性，有人可能会质疑合成数据集的分布偏离真实数据。然而，对比 MTBench 与我们的 1k1k 基准测试中的 MTP 接受情况，我们发现两者分布高度一致。这印证了 InferenceX 基准测试是衡量真实生产环境性能的可靠参照。话虽如此，InferenceX 仍非完美，我们始终在持续迭代。如果你想参与这项使命，欢迎在此申请加入我们的特别项目团队。

https://substackcdn.com/image/fetch/$s_!d8l8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6c4a7c01-3d56-486d-b959-cb4b6468f56f_2408x1390.png

来源：SemiAnalysis InferenceX
