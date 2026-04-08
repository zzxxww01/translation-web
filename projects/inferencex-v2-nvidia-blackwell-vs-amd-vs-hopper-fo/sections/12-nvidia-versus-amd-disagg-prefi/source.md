With today’s release of InferenceXv2, for the first time the ML community is able to see a full Pareto frontier for open-source MI355X distributed inference. We show Pareto curves for the B200 and MI355X with and without enabling MTP.

For FP8 disagg prefill, MI355X (MoRI SGLang) is quite competitive with B200 (Dynamo SGLang). Wide EP is not used for either of these configs as all prefill/decode instances run using EP8 at the most. At both ends of the throughput versus interactivity Pareto frontier, MI355X falls behind the B200 slightly. However, MI355X disagg has a slight advantage for certain levels of interactivity in the middle of the curve. Both the B200 and the MI355X benefit from employing MTP, and we observe the same relative performance improvement for both chips when using MTP.

![](https://substackcdn.com/image/fetch/$s_!_OWw!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F99728443-e697-49cc-8416-7a380c60ad12_2147x1249.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

However, if we were to only measure output (decode) token throughput, we see that output token throughput is much higher for the B200 than for the MI355X at lower interactivity levels. Note that when looking at output token only throughput for disaggregated inference configurations, we normalize throughout by the number of decode GPUs, not total GPUs. It is possible that different numbers of GPUs are used for output when running inference jobs on the B200 and MI355X, but the bottom line is that whatever configuration decode is run on, B200 gets the decode job done faster.

SemiAnalysis is free open source software and reader-supported. To receive new posts and support our work, consider becoming a free or paid subscriber.

![](https://substackcdn.com/image/fetch/$s_!RrVb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff67a92c3-b159-4b2a-bf87-ecbb7002b23c_2118x1306.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Despite the MI355X being competitive in FP8 disagg, its FP4 performance suffers from composability issues. AMD single node FP4 performance is decent, but when we compare AMD FP4 disagg prefill to Nvidia, performance is subpar and the MI355X gets absolutely mogged by Nvidia’s B200. In a 1k1k scenario, the MI355X (MoRI SGLang) with MTP barely manages to beat the B200 (Dynamo SGLang) without MTP.

![](https://substackcdn.com/image/fetch/$s_!pdWn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa5b9e7bc-c484-4400-9ffe-96ed4bbfb70f_2138x1236.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Once we bring Dynamo TRT-LLM into the equation, the B200’s performance is boosted even more to the point that the MI355X even with MTP can’t match the B200’s performance with Dynamo TRT-LLM and MTP. The MI355X can only match the B200 (without MTP) in performance by using MTP, and only for a range of interactivities from ~60 tok/s/user through ~120 tok/s/user.

![](https://substackcdn.com/image/fetch/$s_!BIqJ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0be8b8f5-b627-4dc9-938b-4a407ef19c34_2103x1233.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

When comparing Dynamo TRTLLM B200 disagg prefill to SGLang MoRI MI355 disagg prefill, AMD gets framemogged due to the more mature implementation of disagg prefill on TRTLLM.

![](https://substackcdn.com/image/fetch/$s_!V0OR!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F89827e17-6cfd-42f1-b250-d7f07cbe6a09_2120x1242.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!qzCm!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc53a37b8-dd9f-4142-b114-60e6e2c7f3e7_3446x1946.png)

Source: Dwarkesh Podcast and SemiAnalysis

The diagram below shows us the various parallelism configurations that form up the MI355X (MoRI SGLang) Pareto frontier. Note that currently, wide EP is not employed for any points (i.e., configurations with EP 16, 32, etc.).

![](https://substackcdn.com/image/fetch/$s_!IcWw!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe1b62a52-bd6a-4cd1-82e7-65b6903d82ac_2996x1774.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)
