Since Hopper, Nvidia datacenter GPUs have supported an optional feature which is known by several names, such as “thread block clusters”, “CTA clusters”, and “cooperative grid arrays” (CGAs), all of which refer to the same feature. A cluster is a logical grouping of CTAs, the shape and size of which can be statically or dynamically specified per-kernel. Clusters are visible to the programming model in some useful ways, one of which allows for multicast loads to multiple CTAs in the same cluster; we discuss this later in the context of TMA multicast.

Importantly, CTAs in a cluster are guaranteed to be co-scheduled on the same GPC. This has an important consequence in the 1-CTA-per-SM “persistent CTA”-style Blackwell kernel: if the cluster size does not evenly divide the number of SMs in a GPC, some of the SMs will be left idle. This behavior can be confusing for kernel authors who, unaware of the sparsely-documented GPC, naively launch a number of persistent CTAs equal to the number of SMs with clusters enabled, resulting in serialized execution for some CTAs.

The number of yielded SMs per GPCs is not fixed, not the same between GPCs on the same chip, and may not even be symmetrical between dies in the same package. Manufacturing of semiconductors results in defects and those defects can land all over the chip. As such Nvidia has to engineer their chips in a way such that they can still have those yielded units still exposed to software in a relatively uniform way.

We prompted Claude to write a utility to reverse-engineer the mapping of SMs to GPCs by launching clusters of various sizes and using PTX `%%smid` to record which SMs appear in the same GPC. The result is a list of logical groupings of TPCs into GPCs. The list is longer than the 8 GPCs present in Hopper/Blackwell because there are some TPCs which seem to occupy their own logical GPC, and are never co-scheduled with any other TPCs.

![](https://substackcdn.com/image/fetch/$s_!VqPc!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4647ae85-dc9e-4c79-a203-47909a997e1b_1184x268.png)

As of SM100, NVIDIA has provided a solution to this quantization issue so that kernels can get the benefit of larger clusters while still making use of all the available SMs. Kernels can be launched with two cluster sizes: a preferred cluster size and a fallback cluster size. In general, to use the whole GPU, the fallback cluster should be size 2 or size 1.

References:

* [Cluster API](https://docs.nvidia.com/cuda/cuda-programming-guide/03-advanced/advanced-host-programming.html#launching-with-clusters-using-cudalaunchkernelex)

* [Cooperative groups API](https://docs.nvidia.com/cuda/cuda-programming-guide/04-special-topics/cooperative-groups.html)

* `CU_LAUNCH_ATTRIBUTE_PREFERRED_CLUSTER_DIMENSION`

* [CUTLASS Example 73](https://github.com/NVIDIA/cutlass/blob/main/examples/73_blackwell_gemm_preferred_cluster/blackwell_gemm_preferred_cluster.cu)
