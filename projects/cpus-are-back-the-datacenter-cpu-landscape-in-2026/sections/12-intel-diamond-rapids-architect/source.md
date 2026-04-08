![](https://substackcdn.com/image/fetch/$s_!ZcsD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F73fc256f-03cf-47b4-9ac5-a6240b0c9de0_2786x1606.png)

*Diamond Rapids Overview. Source: HEPiX via @InstLatX64*

At first glance, Diamond Rapids almost looks like a copy of AMD’s designs, with compute dies surrounding a central I/O die. It seems that it was too difficult to grow a single mesh network beyond the 10x19 on Granite Rapids to further increase core count, meaning Intel finally succumbs to having multiple NUMA nodes and L3 domains. Four Core Building Block (CBB) dies flank two I/O and Memory Hub (IMH) dies in the middle.

Within each CBB, 32 Dual Core Modules (DCM) on Intel 18A-P are hybrid bonded onto a base Intel 3-PT die containing the L3 cache and local mesh interconnect. To reduce the number of mesh stops and reduce network traffic, two cores now share a common L2 cache in each DCM, a design reminiscent of the Dunnington generation from 2008. While this means Diamond Rapids has 256 cores in total, it seems only up to 192 cores will be enabled for the mainline SKUs, with higher core counts presumably reserved for off-roadmap orders due to lower yields.

The IMH dies contain the 16-channel DDR5 memory interfaces, PCIe6 with CXL3 support, and Intel datapath Accelerators (QAT, DLB, IAA, DSA).

Interestingly, it seems that the die to die interconnect no longer requires EMIB advanced packaging, with long traces across the package substrate connecting each CBB die to both IMH dies, allowing each CBB direct access to the entire memory and IO interface without needing a second extra hop to the other IMH. This also ensures that only 2 cross-die hops are needed for any inter-CBB communication. As a result of moving away from advanced packaging and splitting the cores across 4 dies, we expect cross-CBB latencies to be appreciably worse off, with a large difference in latency compared to staying within the same die.

![](https://substackcdn.com/image/fetch/$s_!v88S!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe49ef13f-5a91-465a-af7e-3caabc9c651a_2942x1627.png)

*Intel removes SMT on their P-cores. Source: Intel*

Though worse latencies are problematic, the worst issue with Diamond Rapids is the lack of SMT. Spooked by the Spectre and Meltdown vulnerabilities that fundamentally affected Intel more than AMD, their core design team began designing P-cores without it, starting with Lion Cove in the 2024 client PC. Intel rationalized it at the time by claiming the area saved by removing SMT functionality would give better efficiency at the expense of raw throughput. This was fine for PC designs as they had integrated E-cores alongside that would help bolster multi-threaded performance.

However, maximum throughput matters for datacenter CPUs, severely handicapping Diamond Rapids. Compared to the current 128 core, 256 thread Granite Rapids, we expect the main 192 core, 192 thread Diamond Rapids to be only around 40% faster, exposing Intel for another generation with lower performance than AMD.

In a late move, Intel has cancelled the mainstream 8-channel Diamond Rapids-SP platform entirely, leaving their highest volume core market without a new generation into at least 2028. While this helps streamline Intel’s bloated SKU stack, we feel this is the wrong move as general purpose compute for AI tool use and context storage uses more mainstream CPUs with good connectivity as opposed to massive performance per socket options.
