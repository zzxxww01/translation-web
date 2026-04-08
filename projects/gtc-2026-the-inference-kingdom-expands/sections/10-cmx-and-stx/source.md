We have written extensively on Nvidia’s CMX, or ICMS platform in our last Rubin piece and Memory Model. Nvidia introduced the STX reference storage rack architecture.

#### CMX

**CMX** is NVIDIA’s context memory storage platform. CMX addresses a growing bottleneck in modern inference infrastructure: the rapid expansion of **KV Cache** required to support long-context and agentic workloads.

KV cache grows linearly with input sequence length and number of users and is the primary tradeoff when it comes to prefill performance (time to first token). At scale, on-device HBM does not have enough capacity. Host DRAM extends beyond HBM capacity with an additional tier of cache, but also hits limits on total amount per node, memory bandwidth, and network bandwidth. Enter NVMe storage for additional KVcache offload.

NVIDIA introduced a “new” intermediate storage “tier G3.5” within the inference memory hierarchy at CES in January. Tier G3.5 NVMe sits in between tier G3 DRAM and tier G4 shared storage (also NVMe, or SATA/SAS SSD, or HDD). Previously referred to as **ICMS (Inference Context Memory Storage)** and now branded as the **CMX platform**, this is just another re-brand of storage servers attached to compute servers via Bluefield NICs. The only difference from NVMe architectures is the swap from Connect-X NICs to Bluefield NICs.

![](https://substackcdn.com/image/fetch/$s_!wa5A!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb3a0a186-dbca-4e82-b477-f41c8148e2f3_1336x1258.jpeg)

Source: Original NVIDIA ICMS blog in January, 2026 – updated and re-released on March 16, 2026 [https://developer.nvidia.com/blog/introducing-nvidia-bluefield-4-powered-inference-context-memory-storage-platform-for-the-next-frontier-of-ai/](https://developer.nvidia.com/blog/introducing-nvidia-bluefield-4-powered-inference-context-memory-storage-platform-for-the-next-frontier-of-ai/)

#### STX

To expand the scope of CMX, NVIDIA also launched STX. STX is a reference rack architecture using Nvidia’s BF-4 based storage solution to complement VR compute racks. The reference architecture effectively specifies exactly how many drives, Vera CPUs, BF-4 DPUs, CX-9 NICs, and Spectrum-X switches are needed for a given cluster.

![](https://substackcdn.com/image/fetch/$s_!p_Sv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fddb9b036-0027-4510-975b-9c707ca486c4_3000x4000.jpeg)

*BF-4 in STX. Source: Nvidia, SemiAnalysis*

Unlike the BF-4 in the VR NVL72, which consists of a Grace CPU and a single CX-9 NIC, the BF-4 in the STX reference design includes one Vera CPU, two CX-9 NICs, and two SOCAMM modules. Each STX box contains two BF-4 units, totaling two Vera CPUs, four CX-9 NICs, and four SOCAMM modules. For the whole STX rack, it has a total of 16 boxes, implying 32 Vera CPUs, 64 CX-9 NICs, and 64 SOCAMMs.

![](https://substackcdn.com/image/fetch/$s_!N7af!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F31ef2de0-8f01-45f0-bea0-0fca1c8744ee_878x1030.png)

*STX Rack (left). Source: Nvidia, SemiAnalysis*

The STX announcement included a typical Nvidia show of strength where they named all major storage vendors as supporting STX, including AIC, Cloudian, DDN, Dell Technologies, Everpure, Hitachi Vantara, HPE, IBM, MinIO, NetApp, Nutanix, Supermicro, Quanta Cloud Technology (QCT), VAST Data and WEKA.

Put together, BlueField-4, CMX, and STX represent NVIDIA’s broader effort to standardize how clusters are designed at the storage layer. NVIDIA has captured the compute and network layer, and is actively moving into the storage, software, and infrastructure operations layers over time.

Now behind the paywall, we will share some more details on how all of this impacts the supply chain. Including beneficiaries of the LPX system, and the updated Kyber racks. We will also reveal a rack concept that Nvidia has yet to announce.
