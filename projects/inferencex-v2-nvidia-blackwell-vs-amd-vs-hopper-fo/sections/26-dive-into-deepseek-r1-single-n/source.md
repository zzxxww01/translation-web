On DeepSeek R1 FP8 1k1k, we see that MI355X is competitive with its counterpart B200 on single node scenarios, despite getting mogged on FP4 multi node scenarios. MI355X (SGLang) even beats B200 (SGLang) in throughput performance at lower interactivity levels. Moreover, MI355X (SGLang) beats B200 (TRT and SGLang) in most cases from a perf/TCO perspective.

Unfortunately, the year is 2026, and most frontier labs and inference providers are not running FP8 nor single node inference.

This result goes to show that AMDs chips are great and can be extremely competitive with Nvidia if only they could move faster on the software front. Speed is the moat.

![](https://substackcdn.com/image/fetch/$s_!F-j0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa4e8da6f-c4ee-4d39-96ae-9143459d3ea9_2102x1236.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

![](https://substackcdn.com/image/fetch/$s_!w0x6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7ce2b96f-840d-411b-9c6c-2f821219fba5_2130x1444.png)

Source: [SemiAnalysis InferenceMAX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

To that end, we see MI355X fall well behind B200 in performance on FP4:

![](https://substackcdn.com/image/fetch/$s_!O75w!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdbc1dd2c-e15c-45b7-acf7-508d38ad1913_2406x1430.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

In comparing DeepSeek R1 FP8 perf between H200 (SGLang) and MI325X (SGLang), not much has changed since our initial release of InferenceXv1 last October. The MI325X data was captured on Feb 12th, 2026 with SGLang 0.5.8 whereas the B200 data was captured Jan 23, 2026 with SGLang 0.5.7.

One thing we note is the considerably smaller interactivity range for MI325X than H200, with H200 ranging from 30-90 tok/sec/user whereas MI325X ranges from only 13-35 tok/sec/user. This is problematic for providers who would like to serve users at a broader range of interactivity.

![](https://substackcdn.com/image/fetch/$s_!SI_q!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff3ba43db-8f65-4b28-a4a2-66282670449f_2117x1236.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21957492333&i_seq=8k%2F1k&i_prec=fp8#inference)
