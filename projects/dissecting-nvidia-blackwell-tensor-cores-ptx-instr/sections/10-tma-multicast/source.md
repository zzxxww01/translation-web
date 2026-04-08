TMA supports a multicast mode, where a single load copies data to the shared memory of multiple SMs, specified by a CTA mask. Multicast is commonly used in GEMM-like patterns, where input tiles are shared between SMs working on different output tiles. For example, multicast is useful for the activation function SwiGLU, which uses a dual-GEMM pattern of two GEMM operations sharing one input matrix. The major benefit is reducing HBM loads, which lowers effective bandwidth usage. It also significantly reduces L2 traffic, because requests for shared data for multiple CTAs are coalesced into one request.

According to NCU, the unit responsible for serving TMA multicast requests is called the L2 Request Coalescer (LRC):

The L2 Request Coalescer (LRC) processes incoming requests for L2 and tries to coalesce read requests before forwarding them to the L2 cache. It also serves programmatic multicast requests from the SM and supports compression for writes.

It sounds like the hardware might provide some multicast behavior, even if it isn’t explicitly requested, like a miss status holding register. We test this by running the same TMA multicast benchmark, except instead of one CTA issuing a multicast load, all CTAs issue independent TMA loads to the same data.

Here, we compare three cases:

1. Every SM loads different data (baseline) 2. TMA multicast (explicit) - one CTA in each cluster issues multicast loads to all CTAs in its cluster 3. TMA multicast (implicit) - all CTAs in each cluster issue plain TMA loads to the same data

TMA multicast allows for much higher load bandwidth to fill SMEM buffers, even if data is not already in L2. For known traffic patterns, explicit TMA multicast instructions perfectly eliminate L2 traffic, resulting in the ideal “1 / cluster\_size” L2 bytes per SMEM byte. We also observe that for this simple benchmark, we achieve nearly the same SMEM fill throughput in both the explicit and the implicit case. However, we can see the LRC is not perfect; the L2 receives a bit more traffic in the implicit case, especially as the total volume increases.

![](https://substackcdn.com/image/fetch/$s_!Kl4E!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3b833880-e9f9-4018-b7cf-d8f8cc9f95c7_1600x1309.png)

*Implicit multicast performs on par with explicit in terms of effective memory throughput. However, for L2 cache traffic reduction, implicit multicast loses effectiveness after more than 64 bytes in-flight.*
