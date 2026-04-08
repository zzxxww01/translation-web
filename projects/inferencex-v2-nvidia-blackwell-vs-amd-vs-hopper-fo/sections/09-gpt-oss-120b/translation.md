针对 MI300X 和 MI325X，我们观察到整体性能实现了全面小幅提升。部分 AITER 优化改善了 MI300X 在所有交互性下的性能，而切换到上游 vLLM ROCm 镜像也带来了进一步提升。

SemiAnalysis InferenceX 是一款由读者支持的免费开源软件。想要接收最新文章并支持我们的工作，欢迎成为免费或付费订阅者。

https://substackcdn.com/image/fetch/$s_!jygf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F10e95c72-6372-415e-8e51-d8021815182c_2142x1784.png

来源：SemiAnalysis InferenceX

至于 MI325X，似乎并非所有存在于下游 ROCm fork 镜像（在 2025 年 10 月 5 日测试中使用）中的性能增强，都已合入官方 vLLM ROCm 镜像。更离谱的是，MI355X 居然还在用 vLLM 0.10.1 版本的 fork rocm/7.0:rocm7.0_ubuntu_22.04_vllm_0.10.1_instinct_20250927_rc1)。我们本期望现在能看到它更新，但遗憾的是，当前的官方镜像（撰写本文时的 0.15.1 版本）尚未针对 MI355X 进行优化，并且会遇到严重错误。之前我们在 vLLM 0.14 版本的 MI355X 测试中也曾遭遇严重错误导致的崩溃。坊间传闻，vLLM 0.16.0 终于将实装所有必要改动，以提升 MI355X 的性能表现。

https://substackcdn.com/image/fetch/$s_!Xx8c!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1755b498-ab4d-4c02-b6fd-152ee538a34d_2126x1788.png

来源：SemiAnalysis InferenceX

将目光转回英伟达的系统，Hopper 和 Blackwell 在 vLLM 0.11.2 到 0.13.0 版本之间均实现了稳步的性能提升。我们很快将更新英伟达 GPU 的配置方案，以适配最新版本的 vLLM，并预计在切换后将获得更显著的性能飞跃。我们同样观察到，最新 1.2.0 版本的 TRT-LLM 也带来了性能提升。

https://substackcdn.com/image/fetch/$s_!WD4A!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F53a95093-3d25-4d01-9d64-64ea9e113749_2376x1760.png

来源：SemiAnalysis InferenceX

https://substackcdn.com/image/fetch/$s_!ZeZf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F77c591fb-74ef-46ce-bba2-9f82a52f5f6f_2362x1752.png

来源：SemiAnalysis InferenceX
