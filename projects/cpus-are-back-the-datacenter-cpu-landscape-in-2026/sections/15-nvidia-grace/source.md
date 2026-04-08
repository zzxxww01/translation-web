![](https://substackcdn.com/image/fetch/$s_!Fg1r!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F56be8f6f-b46d-4a8c-b042-449a59a8fe0c_1999x1018.png)

*Nvidia’s Grace CPU connections. Source: NVIDIA*

![](https://substackcdn.com/image/fetch/$s_!oe6W!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5e6f2555-0038-48f1-945e-f48bdc05c2f7_1846x1046.png)

*Nvidia Grace Scalable Coherency Fabric. Source: NVIDIA*

Unlike most of the general purpose CPUs covered in this article, Nvidia’s CPUs are designed with head nodes and Extended GPU Memory in mind, with NVLink-C2C as its party trick. This 900GB/s (bi-directional) high speed link allows the connected Hopper or Blackwell GPU to access the CPU’s memory at full bandwidth, alleviating the low memory capacity limits of HBM with up to 480GB memory per Grace CPU. Grace also adopts mobile-class LPDDR5X memory to keep non-GPU power down while maintaining high bandwidths of 500GB/s on a 512-bit wide memory bus. The initial Grace Hopper superchips attached 1 Grace for each GPU, while the later Grace Blackwell generations shared the CPU across 2 GPUs. NVIDIA also offered a dual-Grace superchip CPU for HPC customers that require high memory bandwidth.

Regarding the CPU cores, NVIDIA uses the high performance ARM Neoverse V2 design with 1MB of private L2 cache on a 6x7 mesh network housing 76 cores and 117MB of L3 cache, with up to 72 cores enabled for yield. Each Cache Switch Node (CSN) on the mesh stop connects up to 2 cores and L3 slices. NVIDIA emphasizes the high 3.2TB/s bisection bandwidth of the mesh network, showing Grace’s specialized focus on data flow rather than raw CPU performance.

On the performance side, Grace has a quirky microarchitectural bottleneck from the Neoverse V2 cores that makes it slow for unoptimized HPC code. From Nvidia’s [Grace Performance Tuning Guide](https://docs.nvidia.com/dccpu/grace-perf-tuning-guide/compilers.html), optimizing large applications for better code locality can result in 50% speedups. This is due to limitations in the core branch prediction engine in storing and fetching instructions ahead of use. On Grace, instructions are organized into 32 2MB virtual address spaces.

Performance starts to drop off massively when this Branch Target Buffer fills beyond 24 regions as hot code hogs the buffer and increases instruction churn, causing more branch prediction mispredicts. If the program exceeds 32 regions, the entire 64MB buffer gets flushed, with the branch predictor forgetting all previous branch instructions to accommodate new incoming ones. Without a functioning branch predictor, the CPU core’s front end bottlenecks the whole operating as ALUs sit idle awaiting instructions to execute.

This is why AI workloads are currently being slowed by the Grace CPUs in GB200 and GB300.

### Nvidia Vera

Vera takes things further in 2026 for the Rubin platform, doubling C2C bandwidth to 1.8TB/s and doubling the memory width with eight 128bit wide SOCAMM 192GB modules for 1.5TB of memory at 1.2TB/s of bandwidth. The mesh design remains, with a 7x13 grid that houses 91 cores, with up to 88 active. L3 cache increases to 162MB. NVIDIA now disaggregates the perimeter memory and I/O regions into separate chiplets, totaling 6 dies packaged with CoWoS-R (1 reticle-sized compute die on 3nm with NVLink-C2C, 4 LPDDR5 memory dies and 1 PCIe6/CXL3 IO die).

![](https://substackcdn.com/image/fetch/$s_!C8_g!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F36a84fe6-b848-4374-9c7f-245cc317e0a3_1989x1851.png)

*Vera Rubin NVLink C2C Diagram. Source: NVIDIA*

![](https://substackcdn.com/image/fetch/$s_!YHta!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Febce2cd3-75fb-44fe-aa0b-35a191131a98_3119x1925.png)

*Vera CPU Specifications. Source: NVIDIA*

![](https://substackcdn.com/image/fetch/$s_!CdZY!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F24ed62c6-9b02-438e-8acb-1868bfd4ee81_3000x3040.jpeg)

*Vera Floorplan Annotated. Source: NVIDIA, SemiAnalysis Estimates*

Perhaps burned by the performance bottlenecks of ARM’s Neoverse cores, NVIDIA has brought back their custom ARM core design team with a new Olympus core that supports SMT, enabling 88 cores with 176 threads. The last NVIDIA custom core was 8 years ago in the Tegra Xavier SoC with 10-wide Carmel cores. The ARMv9.2 Olympus core increases the width of the floating point unit to 6x 128b-wide ports vs 4 on Neoverse V2, now supporting ARM’s SVE2 FP8 operations. 2MB of private L2 cache supports each core, doubled from Grace. In total, Nvidia claims a 2x performance improvement going to Vera.
