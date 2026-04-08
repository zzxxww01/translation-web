MI300X, MI325X, H200, and H100 group in the lower-left of the throughput vs interactivity plot, indicating broadly similar tradeoffs, with Nvidia generally holding a modest lead. The next step up is MI355X, which delivers roughly more than 2x higher token throughput per GPU at a given interactivity level, relative to that first group. Within MI355X, ATOM shifts the curve toward higher throughput at low interactivity, suggesting it prioritizes peak throughput over per-user responsiveness.

Above that tier sits NVIDIA’s B200 and GB200, which outperform MI355X across the frontier. While B200 and GB200 share the same Blackwell compute die, GB200 achieves a higher throughput–interactivity curve because the platform and serving stack reduce non-compute bottlenecks at scale (interconnect/topology, CPU-GPU coupling, and runtime scheduling), translating into effective scale-out and less overhead per token.

![](https://substackcdn.com/image/fetch/$s_!euhc!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F478b3a9a-c57d-4766-bde1-c3ee1fef550a_2068x1178.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

If we add cost into the equation, MI355x becomes more competitive: beating B200 at high throughputs. However, GB200 still takes the cake for being the cheapest choice.

![](https://substackcdn.com/image/fetch/$s_!wliK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F028672d5-2c24-4dbd-974d-9f50d163df27_1796x1182.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Turning again to the comparison between B200 and GB200 NVL72, it is obvious the impact NVL72 has. We discussed the impact of the GB200 NVL72’s larger 72 GPU scale-up world size vs the B200’s 8 GPU scale-up world size earlier in this article. The output token throughput per GPU more than doubles in the ~100 tok/s/user interactivity range, showing the impact of the NVL72’s larger scale up domain.

![](https://substackcdn.com/image/fetch/$s_!J3Ls!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0186cfbc-1b42-46ae-ae1a-0d7791afcb20_2081x1306.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)
