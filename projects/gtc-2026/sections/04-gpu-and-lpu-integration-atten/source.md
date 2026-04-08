![](https://substackcdn.com/image/fetch/$s_!269y!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F05b555ed-9d4e-45db-ad03-cbc1cc261b17_3064x1497.jpeg)

Source: Nvidia

Now with an understanding of what LPUs are good for we can understand how they fit into inference setups. NVIDIA introduced LPUs to improve the performance of high interactivity scenarios. In those scenarios, LPUs can leverage their low-latency capabilities to improve the decode phase latencies. One way LPUs can improve decode phase latencies is by applying the Attention FFN Disaggregation (AFD) technique, introduced in [MegaScale-Infer](https://arxiv.org/abs/2504.02263) and [Step-3](https://arxiv.org/abs/2507.19427).

As we explained in our [InferenceX article](https://newsletter.semianalysis.com/p/inferencex-v2-nvidia-blackwell-vs), LLM inference involves two phases: prefill and decode. Prefill processes the full input context: It is compute-intensive, which is suitable for GPUs. On the other hand, decode predicts new tokens and is memory-bounded. Decode is latency-sensitive because the model predicts new tokens one by one, and LPU’s high SRAM bandwidth and low-latency capabilities can help accelerate this iterative process.

![](https://substackcdn.com/image/fetch/$s_!xoes!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F97ce6be2-5ef7-4770-85b8-d65ebda7c049_1887x551.jpeg)

Source: SemiAnalysis

Attention and FFN are subsets of operations in a model. In a model forward pass, attention’s output feeds into a token router, and the token router assigns each token to k experts, where each expert is an FFN. Attention and FFN have very different performance properties. During decode phase, the GPU utilization of attention barely improves when scaling batch size due to being bounded by loading KV cache. In contrast, the GPU utilization of FFN scales with batch size comparatively better.

This is something we have worked with certain hardware vendors and memory companies on [with our inference simulator for more than 6 months.](https://semianalysis.com/institutional/inference-simulator/)

![](https://substackcdn.com/image/fetch/$s_!hooB!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc0bd1310-e0d9-4158-8959-b52bc3b65fab_577x409.jpeg)

Source: MegaScale-Infer, SemiAnalysis

As state-of-the-art mixture-of-expert (MoE) models grow increasingly sparse, tokens can choose experts from a larger expert pool. As a result, each expert receives fewer tokens, leading to lower utilization. This motivates attention and FFN disaggregation. If a GPU only performs attention operations, its HBM capacity can be fully allocated to KV cache, increasing the total number of tokens it can process, which then increases the tokens each expert processes on average.

![](https://substackcdn.com/image/fetch/$s_!ZhUl!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc51c24d7-d5a7-4c99-a243-0baa24afbf08_1474x783.jpeg)

Source: SemiAnalysis

Comparing the two operations, we see attention is stateful due to dynamic KV cache loading patterns, whereas FFN is stateless since the computation only depends on the token inputs. Thus, we disaggregate the computation of attention and FFN. We map attention computations to GPUs, which handle dynamic workloads well. For FFNs, we map them to LPUs, since LPU architecture is inherently deterministic and benefits from static compute workloads.

![](https://substackcdn.com/image/fetch/$s_!27kD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F65ead35a-ac7d-4416-b5d8-b2484e3e5a45_1217x372.jpeg)

Source: SemiAnalysis, MegaScale-Infer

With AFD, token routing from GPUs to LPUs can become the bottleneck, especially under strict latency constraints. The token routing flow involves two operations: dispatch and combine. In the dispatch step, we route each token to their top k experts with an All-to-All collective operation. After experts complete their computation, we perform the combine step, where the outputs are sent back to the source location with a reverse All-to-All collective, continuing the next layer’s computation.

![](https://substackcdn.com/image/fetch/$s_!XL7s!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffd5a62c2-81f4-4f64-b101-6a7e9e611fe6_830x1054.jpeg)

Source: SemiAnalysis

To hide the communication latency of dispatch and combine, we employ ping pong pipeline parallelism. In addition to splitting batches into micro-batches and computation pipelining like standard pipeline parallelism, the tokens dispatched to the LPUs are combined back to the source GPUs, so they ping pong between the GPUs and the LPUs.

![](https://substackcdn.com/image/fetch/$s_!oNdF!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F15b11e7c-2540-46c1-92a2-ad4fe5b4e561_1400x673.jpeg)

Source: MegaScale-Infer

![](https://substackcdn.com/image/fetch/$s_!jmpy!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fefbdfe32-e16d-4a9b-bfd8-725d4b880569_1381x1082.jpeg)

Source: SemiAnalysis

![](https://substackcdn.com/image/fetch/$s_!G-iW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1204b3bb-7e16-4820-9a71-4171d79a719e_889x778.jpeg)

Source: SemiAnalysis
