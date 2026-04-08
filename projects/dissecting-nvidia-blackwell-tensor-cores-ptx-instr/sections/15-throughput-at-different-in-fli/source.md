In our throughput benchmark, we set high numbers of in-flight instructions to amortize instruction issuing and commit wait overheads, ranging from 256 to 1024. However, kernels typically use 1 to 4 in-flight MMA instructions. We benchmarked the throughput at 1 to 10 in-flight instructions, and we discuss the changes in throughput here.

Across all configurations, we see the same N and in-flight MMAs achieve similar percentages of Speed-of-Light (SoL). Notably, only the largest N reaches 90% SoL, while the smallest N achieves only about 70%. Comparing 1SM and 2SM MMA, we see 1SM achieves around 5% higher SoL throughput than its 2SM counterpart. For the same data format and CTA group MMA, the throughput for larger N is always higher than smaller N sizes. Finally, we observe that the throughput SoL percentages for 4 in-flight MMAs caps out at 78% - 80%.

![](https://substackcdn.com/image/fetch/$s_!zi4B!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa662dd8a-5747-43e1-8fc4-8e0a73599bcf_1600x635.png)

![](https://substackcdn.com/image/fetch/$s_!bQr2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1c7ae14b-4955-43db-a8b2-5673ff661d72_1600x635.png)

![](https://substackcdn.com/image/fetch/$s_!hvag!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb1f518e0-ccbe-48de-ace9-1dd5264df6d5_1600x635.png)

Below we discuss real-world use cases with kernel writing library CUTLASS. We also discuss throughput, multi-cast, and floorplans.
