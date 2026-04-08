From Hopper to Blackwell, NVIDIA made several incremental improvements to the architecture and changes to the PTX abstractions for MMA-related instructions. We cover most of these in our article [NVIDIA Tensor Core Evolution](https://newsletter.semianalysis.com/i/174558646/blackwell). The major notable changes are:

* The introduction of tensor memory (TMEM) to hold MMA accumulators. Threads no longer implicitly own the results of MMA operations and instead, TMEM is explicitly managed at the MMA scope from software

* `tcgen05` operations are now issued by a single thread on behalf of the entire CTA, rather than at warp or warpgroup scope as in previous generations. You can see this reflected in the CuTe MMA atoms which now use `ThrID = Layout`<_1>`` [in Blackwell](https://github.com/NVIDIA/cutlass/blob/main/include/cute/atom/mma_traits_sm100.hpp#L1045) instead of `ThrID = Layout`<_128>`` as in the [warpgroup-scoped MMAs of Hopper](https://github.com/NVIDIA/cutlass/blob/main/include/cute/atom/mma_traits_sm90_gmma.hpp#L491)

* Support for TPC-scoped TMA and MMA across pairs of coordinating CTAs, exposed as `cta_group::2` in PTX and `2CTA` in SASS, where two SMs making up a TPC can execute `tcgen05.mma` on shared operands, providing access to higher operational intensity MMA instructions by reducing per-CTA SMEM bandwidth requirements. Later we show that this operand sharing is necessary to make use of the available MMA throughput

* Native support for sub-byte datatypes with micro-scaling

* [Cluster Launch Control (CLC)](https://docs.nvidia.com/cutlass/latest/media/docs/cpp/blackwell_cluster_launch_control.html) as hardware support for dynamic work scheduling in persistent-CTA kernels (Covering in future articles)

* [Programmatic dependent launch (PDL)](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/programmatic-dependent-launch.html) was introduced in Hopper to hide launch and setup latency in back-to-back kernels (Covering in future articles)
