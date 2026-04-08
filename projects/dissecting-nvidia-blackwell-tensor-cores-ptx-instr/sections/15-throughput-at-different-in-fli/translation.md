在我们的吞吐量基准测试中，我们设置了大量的飞行中指令，数量在 256 到 1024 之间，以此来摊销指令发射与提交等待的开销。然而，实际内核通常仅使用 1 到 4 条飞行中 MMA 指令。因此，我们对 1 到 10 条飞行中指令的吞吐量进行了基准测试，并在此探讨其吞吐量的变化规律。

在所有配置下，我们发现相同的 N 维度与飞行中 MMA 指令数能够达到相似的理论极限性能 (Speed of Light, SoL) 百分比。值得注意的是，只有在 N 取最大值时才能达到 90% 的 SoL，而在 N 取最小值时仅能达到约 70%。对比 1SM 与 2SM MMA，我们发现 1SM 的 SoL 吞吐量比 2SM 高出约 5%。对于相同的数据格式和协作线程阵列 (CTA) 组 MMA，较大 N 维度的吞吐量始终高于较小的 N 维度。最后，我们观察到 4 条飞行中 MMA 指令的吞吐量 SoL 百分比最高仅能达到 78% 至 80%。

https://substackcdn.com/image/fetch/$s_!zi4B!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa662dd8a-5747-43e1-8fc4-8e0a73599bcf_1600x635.png

https://substackcdn.com/image/fetch/$s_!bQr2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1c7ae14b-4955-43db-a8b2-5673ff661d72_1600x635.png

https://substackcdn.com/image/fetch/$s_!hvag!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb1f518e0-ccbe-48de-ace9-1dd5264df6d5_1600x635.png

下文我们将讨论基于内核编写库 CUTLASS 的实际用例。此外，我们还将探讨吞吐量、多播 (multi-cast) 以及物理布局 (floorplans)。
