For MI300X and MI325X, we have seen marginal improvements across the board. Some AITER optimizations helped MI300X performance across all interactivities, and switching to the upstream vLLM ROCm image led to improvements.

SemiAnalysis InferenceX is free open source software and reader-supported. To receive new posts and support our work, consider becoming a free or paid subscriber.

![](https://substackcdn.com/image/fetch/$s_!jygf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F10e95c72-6372-415e-8e51-d8021815182c_2142x1784.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

In the case of the MI325X, it appears that not all performance enhancements that were present in the downstream ROCm fork image (used during the October 5th, 2025 run) have made it into the official vLLM ROCm image. Unfortunately, the MI355X literally still uses a fork of the vLLM 0.10.1 build `rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250927_rc1`). We would love to have seen it updated it by now, but unfortunately the current official image (0.15.1, at the time this article was written) is not yet optimized for the MI355X and runs into hard errors. We had also run into hard errors crashes on Mi355 for vLLM 0.14. Word on the street is that vLLM 0.16.0 will finally deliver all the changes needed for better MI355X performance.

![](https://substackcdn.com/image/fetch/$s_!Xx8c!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1755b498-ab4d-4c02-b6fd-152ee538a34d_2126x1788.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/#inference)

Turning back to Nvidia’s systems, both Hopper and Blackwell saw a steady performance increase between vLLM 0.11.2 and 0.13.0. Soon, we will update recipes for Nvidia GPUs to use the latest vLLM version and we expect even greater performance gains after making the switch. We also observed a performance bump in the latest 1.2.0 version of TRT-LLM.

![](https://substackcdn.com/image/fetch/$s_!WD4A!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F53a95093-3d25-4d01-9d64-64ea9e113749_2376x1760.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/#inference)

![](https://substackcdn.com/image/fetch/$s_!ZeZf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F77c591fb-74ef-46ce-bba2-9f82a52f5f6f_2362x1752.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/#inference)
