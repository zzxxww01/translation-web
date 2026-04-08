在 DeepSeek R1 FP8 1k1k 负载下，我们发现 MI355X 在单节点场景中与竞品 B200 旗鼓相当，尽管其在 FP4 多节点场景下被全方位碾压。在较低的交互性下，MI355X (SGLang) 的吞吐量性能甚至反超了 B200 (SGLang)。此外，从性能与 TCO 的维度来看，MI355X (SGLang) 在大多数情况下都击败了 B200（无论是运行 TRT 还是 SGLang）。

遗憾的是，现在已经是 2026 年了，大多数前沿实验室和推理服务提供商既不运行 FP8，也不搞单节点推理。

这一结果充分说明，AMD 的芯片非常出色，只要他们在软件层面能迭代得更快，就完全具备与英伟达一较高下的绝对实力。速度就是护城河。

https://substackcdn.com/image/fetch/$s_!F-j0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa4e8da6f-c4ee-4d39-96ae-9143459d3ea9_2102x1236.png

来源：SemiAnalysis InferenceX

https://substackcdn.com/image/fetch/$s_!w0x6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7ce2b96f-840d-411b-9c6c-2f821219fba5_2130x1444.png

来源：SemiAnalysis InferenceMAX

正因如此，我们看到 MI355X 在 FP4 性能上被 B200 远远甩在身后：

https://substackcdn.com/image/fetch/$s_!O75w!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdbc1dd2c-e15c-45b7-acf7-508d38ad1913_2406x1430.png

来源：SemiAnalysis InferenceX

在对比 H200（SGLang）与 MI325X（SGLang）运行 DeepSeek R1 FP8 的性能时，我们发现，自去年 10 月首次发布 InferenceXv1 以来，整体格局并无太大变化。MI325X 的数据采集于 2026 年 2 月 12 日（使用 SGLang 0.5.8），而 B200 的数据采集于 2026 年 1 月 23 日（使用 SGLang 0.5.7）。

值得注意的是，MI325X 的交互性区间比 H200 窄得多：H200 的交互性在 30 到 90 tok/s/user 之间，而 MI325X 仅有 13 到 35 tok/s/user。对于希望在更宽泛的交互性区间内为用户提供服务的供应商而言，这无疑是个棘手的难题。

https://substackcdn.com/image/fetch/$s_!SI_q!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff3ba43db-8f65-4b28-a4a2-66282670449f_2117x1236.png

来源：SemiAnalysis InferenceX
