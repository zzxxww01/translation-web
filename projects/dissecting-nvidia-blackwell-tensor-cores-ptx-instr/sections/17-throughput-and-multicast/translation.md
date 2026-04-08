前文我们探讨了单条指令的可达吞吐量；我们发现某些指令可能天生受限于共享内存 (SMEM) 带宽，但在测量每种指令形状的峰值性能时，我们并未将内存系统纳入考量。在本节中，我们采用相同的单协作线程阵列 (CTA) CUTLASS 基准测试，并将其扩展为使用尺寸大于 1x1 的集群 (cluster)。此外，对于任何 M 维度为偶数的集群形状，我们均使用 2SM MMA 原子指令 (atoms)。

图表中展示了部分测试结果。在每张图表中，我们保持每个协作线程阵列 (CTA) 的分块 (tile) 大小不变，并分别针对 1SM 和 2SM 改变集群大小。需要注意的是，对于 128x128 的单协作线程阵列 (CTA) 分块形状，当将集群的 N 维度从 1 扩展到 2 (2SM) 或从 2 扩展到 4 (1SM) 时，集群引入的多播 (multicast) 机制带来了显著的性能收益。因此我们可以得出结论：小于该尺寸的分块形状受限于内存子系统/L2 带宽。

https://substackcdn.com/image/fetch/$s_!PF7p!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F219aa10e-cce7-4fd5-896f-ab39146dd54a_1600x1143.png
