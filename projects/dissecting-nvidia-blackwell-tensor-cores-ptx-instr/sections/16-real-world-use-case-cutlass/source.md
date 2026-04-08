Here we look at a real world use case: the tiled GEMM inner-loop pattern of continuously loading tiles along the inner dimension K to compute a single tile of an output matrix.

First we use Nvidia’s CUTLASS Library to instantiate a kernel with a single persistent CTA which computes a single output tile. We vary the number of load stages in the DMA->Math pipeline, making use of more and more SMEM as we increase the number of stages and at the same time achieving better latency hiding. The K dimension is set to be very large so that we measure the achieved math throughput in the steady state mode of the software pipeline as a percentage of the hardware speed-of-light math throughput.

For a chosen tile size, more and more SMEM can be used to increase the stage count and hide more latency. For a given pipeline depth N, if one stage is actively performing MMA, up to N-1 stages’ A and B buffers can be in-flight. Another way to look at it is that the latency for a given load stage can still be fully hidden up to (N-1)\*M where M is the time for a single stage to perform MMA, so the latency hiding ability strictly increases for a fixed tile size with increasing stage count.

However, if the GEMM Epilogue consumes SMEM, there is less available for the main loop and so the stage count used must be lower. Here, we use an epilogue that consumes no SMEM, and therefore the lines end along the X-axis when the total SMEM consumed by stage buffers reaches the max SMEM capacity per-SM.

![](https://substackcdn.com/image/fetch/$s_!ZJVd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4595a83a-3bc4-4208-86b1-c09748633651_1600x700.png)

So SMEM usage and therefore stage count is [computed](https://github.com/NVIDIA/cutlass/blob/main/include/cutlass/gemm/collective/builders/sm100_umma_builder.inl#L84) based on:

* Operand SMEM tiles (A and B)

* Barrier storage

* Epilogue SMEM usage
