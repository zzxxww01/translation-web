Anthropic 最近在发布 Opus 4.6 的同时推出了“快速模式”。其核心卖点是：在保持模型质量不变的前提下，速度提升约 2.5 倍，但价格也涨了约 6 到 12 倍。这两个数字可能令人咋舌，一些用户甚至猜测这肯定需要新硬件。其实不然。这本质上只是基本的权衡博弈。任何模型都可以提供多种交互性（每用户每秒 Token 数），而每百万 Token 成本 (CPMT) 也会随之变化。顺着我们之前的比喻来说，梅赛德斯既造公交车，也造赛车。这就像是乘坐公交车与驾驶赛车的区别。公交车能服务众多乘客，但频繁停靠会增加时间（分摊成本）；而赛车速度极快，但只服务单人。

精打细算的财务人员可能觉得快速模式更贵，但如果从总体拥有成本的视角来看，在某些场景下快速模式实际上要便宜得多。举个例子，一个 GB200 NVL72 机架的成本可达 330 万美元。因此，如果 Claude Code 的智能体循环（在生产环境中运行于 Trainium）通过工具调用 NVL72 机架，而这些机架的推理速度慢了 2.5 倍，你就需要 2.5 倍数量的机架来提供推理能力。这意味着，如果不开启快速模式，将多出近 500 万美元的额外开销。

https://substackcdn.com/image/fetch/$s_!sIVI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcad37655-7b9a-4c86-81a8-3314ad0526fe_1694x348.png

来源：Anthropic

https://substackcdn.com/image/fetch/$s_!7boM!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4bb71482-fe77-4e33-b5cb-b7db512b61c1_1700x439.png

来源：Anthropic

以在 B200 上使用 TRT-LLM 部署 DeepSeek R1 0528 FP4 的编程工作流为例。当交互性为 50 tok/s/user 时，推理成本约为 0.56 美元/百万输出 Token。当交互性达到 125 tok/s/user 时，成本升至约 4 美元/百万输出 Token。速度提升 2.5 倍，价格上涨约 7 倍，这与我们在 Anthropic 快速模式中看到的情况高度吻合。需要注意的是，这里假设 DeepSeek R1 与 Opus 4.6 类似，但实际并非如此。尽管如此，这一基本原则依然成立。

https://substackcdn.com/image/fetch/$s_!7SFd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F66509f21-d3e5-435f-9163-50d9be56c789_1930x1162.png

来源：SemiAnalysis InferenceX

https://substackcdn.com/image/fetch/$s_!CjTZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6621150f-7da2-44ae-9695-493374487825_1972x1122.png

来源：SemiAnalysis InferenceX

这背后的根本原因在于 LLM 推理中固有的延迟与吞吐量权衡。在高批处理规模下，GPU 的利用率更高，总 token 吞吐量也更大，这意味着可以同时服务更多用户，每个 token 的成本也更低。而在低批处理规模下，虽然每个请求的并行度更高，能为单个用户带来更快的响应速度，但总 token 吞吐量会随之下降。由于无论如何使用，加速器的小时成本 都是固定的，因此吞吐量降低就意味着可用于分摊成本的 token 数量减少，从而导致每个 token 的价格更高。

简而言之，所谓的快速模式本质上与硬件关系不大，它只是在同一批 GPU 上牺牲吞吐量换取延迟的必然结果。

https://substackcdn.com/image/fetch/$s_!pPy0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F132f55e4-43c7-4df3-bb4e-1408d85c2782_2718x1796.png

来源：SemiAnalysis InferenceX

此外我们发现，正如前文所述，像投机解码这类推理优化技术可以直接降低推理成本，完全无需更换新芯片。

以 8k/1k 负载下的 DeepSeek R1 FP4 为例。在 150 tok/sec/user 的交互性下，基准 GB300 Dynamo TRT 的每百万 Token 成本（CPMT）约为 2.35 美元，而启用 MTP 后该成本降至约 0.11 美元。仅仅应用一项推理优化技术，就能在该交互性下实现约 21 倍的成本下降。

https://substackcdn.com/image/fetch/$s_!8RyG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff88b30b6-aa73-4ad2-a008-b2e8f940cfd0_1958x1104.png

来源：SemiAnalysis InferenceX

https://substackcdn.com/image/fetch/$s_!YpDx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff6dfa226-93d7-4596-9dc5-feebd5ef1dce_1966x1098.png

来源：SemiAnalysis InferenceX

https://substackcdn.com/image/fetch/$s_!rSgJ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8742f134-05d4-4a07-9257-8c93b4730cd7_2704x1790.png

来源：SemiAnalysis InferenceX

将交互性固定在 50 tok/sec/user，我们可以进一步观察 MTP 能在多大程度上有效降低各类芯片的 CPMT。

https://substackcdn.com/image/fetch/$s_!BIXI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbc992849-b42d-4899-81a3-77105c86886b_1950x1250.png

来源：SemiAnalysis InferenceX
