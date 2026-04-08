The AMD team has significantly improved performance for all configurations of SGLang DeepSeek R1 FP4. For the same interactivity, AMD has almost doubled the amount of throughput in the span of less than 2 months. Moreover, we have pushed AMD to upstream performance enhancing changes from their forked SGLang images into the official SGLang image. From December 2025 to January 2026, AMD’s software was improved up to 2x in performance.

![](https://substackcdn.com/image/fetch/$s_!Jjej!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd0bd5df8-c675-4dce-a853-dfa6f4d381af_1498x1102.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?g_model=DeepSeek-R1-0528&g_rundate=2026-02-02&g_runid=21577661184&i_seq=8k%2F1k&i_prec=fp4%2Cfp8&i_gpus=mi355x_sglang&i_dstart=2025-12-14&i_dend=2026-01-29&i_hc=1#inference)

In order to continue becoming closer to an first class experience, AMD needs increase their support of vLLM & SGLang maintainers through compute contributions and code contributions & having more reviewers that work for AMD to speed up the review process of AMD PRs into the upstream.

![](https://substackcdn.com/image/fetch/$s_!lFtH!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff7fc9e49-b04b-41b0-b0ec-df0d912c0a3c_800x434.jpeg)

Source: SemiAnalysis

On the other hand, Nvidia’s results were more consistent, with minor improvements for B200 SGLang over a similar time period.

![](https://substackcdn.com/image/fetch/$s_!nuP1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F19e48a4c-0c1b-4681-b180-03ef0c8c2ce3_2346x1340.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Many of the mature SKUs had minimal improvements. For example, H200 TRT single node has not changed in performance in the span of 4 months since October, but this is because Hopper support has been excellent since day 1, and performance has close to peak theoretical for this workload all along, making it hard to deliver incremental performance gains.

![](https://substackcdn.com/image/fetch/$s_!_wVx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fca0fbb96-36c4-4040-a022-49f2185b661a_2074x1224.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

MI300X and MI325X have seen some improvements, mainly from the most recent SGLang release. Note that for much of the history of InferenceX, AMD was using “private” ROCm images that were not upstreamed, so runs prior to ~Jan 2026 cannot be compared directly to those that are more recent.

![](https://substackcdn.com/image/fetch/$s_!-eGZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4b8c3b9b-7536-4cba-8b85-854d25169864_1922x1726.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?g_model=DeepSeek-R1-0528&g_rundate=2026-02-13&g_runid=21976393587&i_seq=8k%2F1k&i_prec=fp8&i_gpus=mi325x_sglang%2Cmi300x_sglang&i_dstart=2026-01-23&i_dend=2026-02-13&i_hc=1#inference)

GB200 Dynamo TRT-LLM disagg has seen some significant improvements as well, with a 20% increase in max throughput in the span of a little over 1 month. We also see improvements in the middle interactivities, where wide EP is deployed. This is likely due to maturing wide EP kernels on GB200.

![](https://substackcdn.com/image/fetch/$s_!7v-Z!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdb4fa8dc-176c-4224-9ab5-6ebfe8f6af9c_1493x1280.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-01-31&g_runid=21538687343&i_gpus=gb200_dynamo-trt&i_dstart=2025-12-19&i_dend=2026-01-31#inference)

B200 SGLang has seen steady and continuous improvement for both FP4 and FP8 scenarios since our initial launch, with throughput per GPU doubling at some interactivity levels since last October.

![](https://substackcdn.com/image/fetch/$s_!a06J!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1d5636b8-69d8-4676-9c3c-823da8d03514_2638x1840.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-01-13&g_runid=20972034325&i_gpus=b200_sglang&i_dstart=2025-10-05&i_dend=2026-01-13&i_prec=fp4%2Cfp8&i_dates=2025-10-30%2C2025-12-14#inference)

For MI355X Disaggregated inference serving, AMD recommends using SGLang with MoRI. [MoRI is AMD’s MoE dispatch/combine collective and KV Cache transfer library](https://github.com/ROCm/mori/tree/main) built from first principles by AMD’s cracked 10x China-based engineering team. Although MoRI needs much more open CI and testing, we are strong supporters of the direction that MoRI is taking. This is because instead of taking AMD’s historical approach, which was to fork NVIDIA’s NCCL into RCCL, MoRI is built from scratch by taking the lessons from RCCL/NCCL and building an entirely new package from first principles. The use of MoRI has also delivered good speedups in the span of more than a month, with throughput per GPU increasing by more than 20% in the 20-45 tok/s/user interactivity range.

![](https://substackcdn.com/image/fetch/$s_!J5Il!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6b0d71aa-e6aa-425f-bbcc-25e2c1de2f4d_1900x1744.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-01-13&g_runid=20972034325&i_gpus=b200_sglang&i_dstart=2025-10-05&i_dend=2026-01-13&i_prec=fp4%2Cfp8&i_dates=2025-10-30%2C2025-12-14#inference)
