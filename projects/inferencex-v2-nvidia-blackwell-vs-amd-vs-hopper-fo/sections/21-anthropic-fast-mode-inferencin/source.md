Anthropic recently released “[fast mode](https://code.claude.com/docs/en/fast-mode)” alongside Opus 4.6. The value proposition: the same model quality at roughly 2.5× the speed, for around 6–12× the price. Both figures might seem surprising, and some users have speculated that [this must require new hardware](https://x.com/Yuchenj_UW/status/2020214926133063705). It doesn’t. In fact, this is just the fundamental tradeoff at play. Any model can be served at a wide range of interactivity levels (tokens/sec per user), and the cost per million tokens (CPMT) shifts accordingly. Mercedes makes metro busses as well as race cars, to follow long with our analogy.

Bean counters may think that fast mode is more expensive, but when looking at it through a total cost of ownership lens, fast mode is actually way cheaper for some situations. For example, a GB200 NVL72 rack can cost 3.3 million dollars, and as such, if claude code agentic loops (which runs on Trainium in production) that tool use call NVL72 racks, and these racks run inference 2.5x slower, you would need 2.5x more racks to deliver inference, meaning that not enabling fast mode would cost close to 5 million dollars in extra spend.

![](https://substackcdn.com/image/fetch/$s_!sIVI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcad37655-7b9a-4c86-81a8-3314ad0526fe_1694x348.png)

Source: [Anthropic](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!7boM!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4bb71482-fe77-4e33-b5cb-b7db512b61c1_1700x439.png)

Source: [Anthropic](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Consider a DeepSeek R1 0528 FP4 coding workflow served on B200s with TRT-LLM. At an interactivity of 50 tok/sec/user, inference cost is approximately $0.56/M output tokens. At an interactivity of 125 tok/sec/user, this rises to around $4/M output tokens, a 2.5× speed increase for a ~7× price increase, closely mirroring what we see with Anthropic’s fast mode. Note that this assumes DeepSeek R1 is similar to Opus 4.6, which isn’t the case. Still, the general principle holds true.

![](https://substackcdn.com/image/fetch/$s_!7SFd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F66509f21-d3e5-435f-9163-50d9be56c789_1930x1162.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!CjTZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6621150f-7da2-44ae-9695-493374487825_1972x1122.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

This follows directly from the fundamental latency-throughput tradeoff in LLM inference. At high batch sizes, GPUs achieve better utilization and greater total token throughput, meaning more users served concurrently and lower cost per token. At low batch sizes with greater parallelism per request, each user gets faster responses, but total token throughput drops. Since the [hourly cost of the accelerators](https://semianalysis.com/ai-cloud-tco-model/) is fixed regardless of how they’re used, lower throughput means fewer tokens over which to amortize that cost, and thus a higher price per token.

In short, fast mode isn’t necessarily a hardware story, but merely the natural consequence of trading throughput for latency on the same GPUs.

![](https://substackcdn.com/image/fetch/$s_!pPy0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F132f55e4-43c7-4df3-bb4e-1408d85c2782_2718x1796.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Furthermore, we observe that inference optimization techniques such as speculative decoding, as explained earlier, can directly lead to cheaper inference; no new chips are required.

Take the following example, DeepSeek R1 FP4 on an 8k/1k workload. At an interactivity level of 150 tok/sec/user, the baseline GB300 Dynamo TRT cost per million tokens is approximately $2.35, whereas enabling MTP decreases the price to approximately $0.11. This is a ~21x price decrease at this interactivity level simply by employing an inference optimization technique.

![](https://substackcdn.com/image/fetch/$s_!8RyG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff88b30b6-aa73-4ad2-a008-b2e8f940cfd0_1958x1104.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!YpDx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff6dfa226-93d7-4596-9dc5-feebd5ef1dce_1966x1098.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!rSgJ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8742f134-05d4-4a07-9257-8c93b4730cd7_2704x1790.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Fixing an interactivity level of 50 tok/sec/user, we further see how much MTP can effectively decrease CPMT across a variety of chips.

![](https://substackcdn.com/image/fetch/$s_!BIXI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbc992849-b42d-4899-81a3-77105c86886b_1950x1250.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)
