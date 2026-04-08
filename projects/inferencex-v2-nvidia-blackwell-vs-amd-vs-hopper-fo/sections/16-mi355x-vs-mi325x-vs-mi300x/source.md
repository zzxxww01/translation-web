On AMD SKUs, we see up to 10x better performance on the MI355X vs the MI300X. AMD has only gotten DeepSeek SGLang Disaggregated Inferencing to work on the MI355X so far AMD has not submitted MI300X or MI325X disaggregated inferencing results, potentially due to software issues on older SKUs that are still being solved.

![](https://substackcdn.com/image/fetch/$s_!vT9R!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd6dd3138-e228-4121-a061-4aa92c84d6a4_2334x1390.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_seq=8k%2F1k&i_metric=y_outputTputPerGpu&i_prec=fp8%2Cfp4&i_legend=0#inference)

![](https://substackcdn.com/image/fetch/$s_!rvyB!,w_720,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F101c2a16-c861-40f5-8079-3f2e38038980_2491x1123.png)

Source: SemiAnalysis InferenceX

Turning to cost, for DeepSeekR1 on FP8, at an interactivity of 24 tok/s/user, the MI355X delivers inferences a cost that is slightly less than 3x cheaper than for the MI325X. The throughput of each GPU is slightly less than 4 times that of MI325X.

![](https://substackcdn.com/image/fetch/$s_!SaQ4!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fab1ad749-fe92-4209-9347-4456d22b0cfd_2088x1432.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)
