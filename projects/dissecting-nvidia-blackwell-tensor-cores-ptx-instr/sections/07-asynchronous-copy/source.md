Async copy (PTX: `cp.async` , SASS: `LDGSTS`) was introduced in the Ampere generation, and the instruction moves data from global memory to shared memory asynchronously. Async copy is non-blocking, allowing memory loads to overlap with computation. It also writes directly to shared memory without going through registers, reducing register pressure.

Referencing FlashInfer Multi-head attention (MHA) kernels, we benchmark async copy with the following configuration:

* CTAs per SM: 1, 2, 3, 4

* Number of Stages: 1, 2, 4

* Threads per CTA: 64, 128, 256

* Load Size: 4B, 8B, 16B

We plot throughput versus bytes-in-flight per SM, the total number of bytes concurrent memory loading instructions are loading.

Although different load sizes converge to similar throughput at the same bytes-in-flight, we prefer 16-byte loads. 16-byte loads achieve slightly higher throughput at similar bytes-in-flight while using less execution resources. For example, at 32 KiB in flight, 8B load uses 4 stages, while 16B load uses 2 stages. This saves the memory space for 2 memory barrier objects and reduces instruction issue pressure.

![](https://substackcdn.com/image/fetch/$s_!wD4E!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F763336d2-7438-44f3-879b-f3116360c0ac_1600x1033.png)

Overall, we see memory throughput with `LDGSTS` saturating at around 6.6 TB/s at 32 KiB in flight.

We also benchmark config space multi-latent attention (MLA) kernels use:

* 1 CTA per SM

* 16B loads

* Threads per CTA: 64, 128, 256

* Number of Stages: 4, 8, 12, 16

Our experiments show that increasing the number of stages achieves higher throughput at higher bytes-in-flight, and that increasing threads per CTA strictly improves performance across all configurations. Interestingly, MLA uses 2 warps and 12 stages, landing at about 2.2 TB/s . We believe this is due to softmax warps needing the most registers, and increasing warp count reduces register allocation per thread.

![](https://substackcdn.com/image/fetch/$s_!Lvbe!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F337b9825-d13a-44ed-85f5-df0aec71ba9b_1600x684.png)

We benchmarked the latency of the same set of configurations. We see that `LDGSTS` has a baseline latency of ~600 nanoseconds and nearly doubles after 8 KiB in flight. This is because we need to use a large number of threads for `LDGSTS` to achieve high bytes in flight, leading to a high number of warps stalled due to MIO (memory input output) throttle.

![](https://substackcdn.com/image/fetch/$s_!pE_H!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9381e20a-0318-4284-af11-d1cf13a4c450_1600x977.png)

![](https://substackcdn.com/image/fetch/$s_!tjkZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7888d3c1-270d-4d5e-a940-301c70813f89_1544x206.png)
