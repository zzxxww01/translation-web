At almost all interactivity levels, disagg outperform aggregated inference (grey lines) in terms of total token throughput per GPU. Multi-node disaggregrated prefill framemogs single node aggregrated serving.

![](https://substackcdn.com/image/fetch/$s_!aeCq!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7ace6118-029a-44df-b0ef-2e7595e6f388_2032x1339.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?g_model=DeepSeek-R1-0528&g_rundate=2026-02-14&i_seq=8k%2F1k&g_runid=22013103756#inference)

Nvidia continues to push new updates for B200/GB200 FP8. The latest data on DeepSeek FP8 B200 TRT single node (both MTP enabled/disabled) vs GB200 Dynamo+TRT disagg (both MTP enabled/disabled). This indicates consistent engineering effort to improve rack-scale inference software and wideEP kernels.

![](https://substackcdn.com/image/fetch/$s_!s0zP!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F29485790-238d-4e1d-aa48-0559c79c9855_2132x1247.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

When comparing MI355X disaggregated inference vs aggregated inference, we noticed a similar pattern. Disaggregated inference only overtakes aggregated inference at low interactivity, high batch sizes. This is true across FP4, and it is likely due to poorly optimized kernels.

![](https://substackcdn.com/image/fetch/$s_!wwi4!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F25a7c41e-fa99-4117-8e49-ac121a22bf0f_2092x1241.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

When composing disagg prefill+wideEP with FP4 on the MI355X, we observe suffers subpar performance.

Although theoretical modeling shows that disagg inference on MI355Xs should perform way better than single node, disagg actually performs worse for higher interactivity levels due to a lack of kernel and collective optimization in the ROCm software stack when composing multiple SOTA inference optimizations together.

![](https://substackcdn.com/image/fetch/$s_!PqhO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2d82d32f-089b-405d-b4ef-94b4956676ed_2078x1233.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

### Nvidia TensorRT LLM and NVL72

TensorRT LLM already serves billions of tokens per hour globally across providers like TogetherAI and other advanced providers, and it has really allowed the GB200 NVL72 and GB300 NVL72 to shine, delivering more than double the performance at high throughput. MTP boosts these results even further, making use of the chips’ full potential.

![](https://substackcdn.com/image/fetch/$s_!NgC9!,w_720,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd4628887-37be-4563-ad68-091282e20ddf_2350x1486.png)

Source: SemiAnalysis InferenceX

The benefits delivered from the larger world size of the NVL72 family is also evident if we look at cost graphs. At a fixed interactivity level of 60 tok/s/user, each GB200 NVL GPU produces slightly less than triple the number of tokens/s than each B200 does.

SemiAnalysis InferenceX is free open source software and reader-supported. To receive new posts and support our work, consider becoming a free or paid subscriber.

![](https://substackcdn.com/image/fetch/$s_!_KKs!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F36087d46-94e1-4629-90cb-4b0dfad1a8c1_1856x827.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

This gap shrinks as interactivity increases. At 130 tok/s/user, the GB200 NVL72 has nearly no advantage and is even more expensive on a $/Million tokens basis. At low batch sizes, the inference workload shrinks enough to fit within a single HGX node’s NVLink domain (i.e. 8 GPUs), and the GB200 NVL72’s larger scale-out advantage starts to disappear.

![](https://substackcdn.com/image/fetch/$s_!RyLb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3e287d0e-947f-4fd7-9dc8-d697fad9ac7d_1781x822.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)
