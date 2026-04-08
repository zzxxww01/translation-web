We benchmarked single MMA instruction latency, and we plot the comparison below. Across all configurations, we see latency linearly increases from N=64 to 128, and the spike at N=256 is likely due to the jump from 128 to 256. For individual CTA group MMAs, 1SM MMA M=64 and M=128 have similar latencies across N sizes, whereas in 2SM MMA, M=256 latency grows slightly faster than M=128, which matches our theoretical estimations. Comparing data types, we see little difference for 1SM but clear separation for 2SM MMAs.

![](https://substackcdn.com/image/fetch/$s_!21tK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6a0575f8-c15a-4688-943c-2331a0a753ce_1600x695.png)

We notice a small but consistent pattern of the order of latency:

> S8 < BF16 = E4M3 = F4 < MXF8 = MXF4

We believe integer operations being more power efficient leads to S8 being the fastest, and scale factor computation introduces a minor overhead for MXF8 and MXF4.

![](https://substackcdn.com/image/fetch/$s_!8pOu!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4812fa68-0ae7-40d9-920c-2eb1f55b2d51_1600x1020.png)
