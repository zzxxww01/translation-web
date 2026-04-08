![](https://substackcdn.com/image/fetch/$s_!pozD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F216a402f-a60c-42f3-b7e4-00546356b555_3010x1685.png)

*Intel Knights Landing Mesh Interconnect. Source: Intel, Hot Chips 2016*

To solve the scalability problem, Intel adopted the mesh interconnect architecture used in their 2016 Xeon Phi “Knights Landing” processor for their mainline Skylake-X Xeon Scalable CPUs in 2017, bringing 28 cores in the XCC die. While core counts did not increase much over Broadwell, the design would form the base that would scale core counts over the next decade.

In a mesh architecture, cores are arranged in a grid, with each column and row connected with half rings, forming a 2D mesh array. Each mesh stop can house cores and L3 cache slices, PCIe IO, the IMC, and accelerators. Routing between cores is done in a circular manner, with data travelling in the vertical direction before moving horizontally across. The caching and home agents are now distributed across all the ring stops along with their snoop filters for memory coherence across the network.

With a mesh network and multiple memory controllers on opposite sides of the die, memory access and core to core latency would vary significantly with large meshes. As with the earlier Cluster on Die approach, several clustering modes were offered that split the mesh into quadrants for Sub-NUMA Clustering (SNC), reducing average latencies at the expense of treating each processor as multiple sockets with smaller L3 and memory access pools for each NUMA node.

In Knights Landing, each mesh stop housed two cores with a shared L2 cache. The mesh grid is 6 columns by 9 rows in size, with top and bottom rows more IO and MCDRAM. The mesh network runs on it’s own clock, and can dynamically adjust mesh clocks to save power. On Knights Landing, the mesh ran at 1.6GHz.

![](https://substackcdn.com/image/fetch/$s_!b8mI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffb55424a-5436-4909-83f4-57f750341ca1_1951x1654.png)

*Skylake-SP Mesh Diagram. Source: Intel*

With Skylake-X, the 28 cores are arranged in a 6x6 mesh with a north IO cap and 2 spots for the IMC on the sides. The mesh array is smaller due to the size of the cores, which added more L2 cache and an AVX-512 extension to the core for increased floating point performance. The die size would exceed the 26 x 33 mm reticle limit if another row or column were to be added. With a smaller mesh and higher CPU frequencies of up to 4.5GHz, the mesh clock was increased to 2.4GHz, allowing similar average latencies to Broadwell’s dual rings.

The subsequent Cascade Lake and Cooper Lake processors brought minor changes with the same 28-core layout. As a side node, Intel made a 56-core dual die MCM in Cascade Lake-AP and cancelled a similar version for Cooper Lake CPX-4 in response to AMD’s datacenter return with EPYC.

![](https://substackcdn.com/image/fetch/$s_!8h83!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3aeb2086-3dc2-4707-b47a-1b04ce197224_2176x1604.png)

*Ice Lake XCC 40-core Mesh Diagram. Source: Intel*

The next Ice Lake generation benefited from a node shrink from 14nm to 10nm, allowing core counts to increase to 40 cores in a 8x7 mesh, the maximum within the reticle limit. However, the next generation Sapphire Rapids was still going to be on the same node and with more features. That placed Intel in a pickle with how to increase core counts again.

### Disaggregated Mesh Across EMIB

![](https://substackcdn.com/image/fetch/$s_!84cW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F224c3b3b-2f89-4983-baa8-ba2dfbf79771_2979x1661.png)

*Intel Xeon’s Disaggregation Journey to Chiplets. Source: Intel*

![](https://substackcdn.com/image/fetch/$s_!Jaqc!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcd750739-7f96-4cdb-b968-d5fccfcd99c2_2197x1895.png)

*Sapphire Rapids XCC Topology. Source: Intel*

Sapphire Rapids added Advanced Matrix Extension (AMX) engines for matrix multiplication and AI, further increasing core area. That meant a single monolithic die would only fit 34 cores, a regression from Ice Lake. To increase core counts to 60, Intel had no choice but to split the cores across multiple dies again. However, they wanted to keep the silicon “logically monolithic”, such that the processor would appear and perform identically to a single die.

Thus, Sapphire Rapids debuted Intel’s EMIB advanced packaging technology to carry the mesh architecture across dies. Two pairs of mirrored 15-core dies were stitched together with a Modular Die Fabric, creating a much larger 8x12 mesh across four quadrants and nearly 1600 mm2 of silicon. A double row of mesh stops were required for the IO to facilitate the increased data traffic between the doubled throughput of PCIe 5.0 and the new data accelerator blocks.

With a much larger mesh spanning multiple dies, average core to core latencies deteriorated to 59ns from Skylake’s 47ns. To avoid using the mesh network as much as possible, Intel increased the private L2 cache for each core to 2MB, resulting in more L2 cache on die than L3 cache (120MB vs 112.5MB). Sub-NUMA Clustering (SNC) was also recommended more with each die treated as its own quadrant.

While a first for Intel in going to chiplets, Sapphire Rapids was infamous for its multi-year delay and numerous revisions. Perhaps due to performance problems getting the mesh to function across EMIB or from other execution issues, the final version made it all the way to stepping E5 before release in early 2023. Original roadmaps slated it for 2021.

The subsequent Emerald Rapids update in late 2023 kept the same core architecture and node, but reduced the die count to 2. With less silicon area spent on the EMIB die to die links, Intel were able to increase core counts from 60 to 66 (up to 64 enabled for yield) while also nearly tripling L3 cache to 320MB. We wrote more about the design decisions here.

* [Intel Emerald Rapids Backtracks on Chiplets – Design, Performance & Cost](https://newsletter.semianalysis.com/p/intel-emerald-rapids-backtracks-on) - Dylan Patel, Gerald Wong, and 3 others · May 3, 2023

### Heterogeneous Disaggregation on Xeon 6

![](https://substackcdn.com/image/fetch/$s_!uuve!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb7e1a665-9bf8-4dd2-873a-4de31bd70c7e_2802x1562.png)

*Xeon 6 Platform Features. Source: Intel*

![](https://substackcdn.com/image/fetch/$s_!5cM1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb4873f4f-99fa-4a9f-9389-b3c1a35f46c6_2510x1047.png)

*Xeon 6 Compute and I/O Die Diagrams. Source: Intel*

Another benefit going to a multi-die chiplet design beyond going past the reticle limit is being able to mix and match dies and share designs across different variants and configurations. For the next Xeon 6 platform in 2024, Intel went for heterogeneous disaggregation by partitioning the I/O away from the core and memory. Doing this allows the I/O dies to stay on the older Intel 7 node while the compute dies moved to Intel 3. Intel could thus reuse the I/O IP developed from Sapphire Rapids while saving cost as I/O does not benefit as much from moving to more advanced nodes. At the same time, the compute dies can be mixed and matched with both P-core Granite Rapids and E-core Sierra Forest configurations with up to 3 compute dies on the top Granite Rapids-AP Xeon 6900P series, creating a large 10x19 mesh over 5 dies, connecting 132 cores with up to 128 enabled for yield.

![](https://substackcdn.com/image/fetch/$s_!Omye!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff31bc7da-3964-4e1a-a65c-22d17a7473d4_3102x2196.png)

*Xeon 6 Compute Die Mosaic. Clockwise from Top Left: UCC 44c, HCC 50c, HDCC 152c, LCC 20c. Source: Intel, SemiAnalysis Estimates*

On the 144-core Sierra Forest, the E-cores are grouped into 4-core clusters that share a common mesh stop, arranged in an 8x6 mesh with 152 cores printed and up to 144 cores active. Although Sierra Forest was made on a request from hyperscalers for a “cloud-native” CPU with lower TCO per core, Intel has admitted that adoption has been limited, with hyperscalers already adopting AMD and designing their own ARM-based CPUs, while Intel’s traditional enterprise customers were not interested in it. As a result, the dual-die 288-core Sierra Forest-AP (Xeon 6900E) SKUs did not make it to general availability, surviving as low volume off-roadmap parts to serve the few hyperscale customers that ordered it.

### Clearwater Forest Failure

![](https://substackcdn.com/image/fetch/$s_!-Mf7!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9e7b64d4-593a-4b8e-a26c-3ddba7850e97_2543x2621.png)

*Twelve 24-core Clearwater Forest Compute Dies on 18A. Source: Intel, SemiAnalysis*

The I/O dies are also being reused in the upcoming Xeon 6+ Clearwater Forest-AP E-core processors. The compute dies debut Intel’s Foveros Direct hybrid bonding technology, stacking 18A core dies atop base dies containing the mesh, L3 cache and memory interface, bringing core counts up to 288. Vertical disaggregation allows the compute cores to move to the latest 18A logic process while keeping the mesh, cache and I/O that does not scale as well on the older Intel 3 node.

![](https://substackcdn.com/image/fetch/$s_!qVHN!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff9fc472b-1964-4d8a-9743-0610dd8a10ba_2966x1415.png)

*Clearwater Forest Performance Projections. Source: Intel*

However, Intel’s execution issues surface again with Clearwater Forest, delaying availability from H2 ’25 to H1 ’26. Intel blamed the delay on their Foveros Direct integration challenges, which is not surprising with such a complex server chip being the lead vehicle as Intel tries to figure out hybrid bonding. Perhaps as a result of this, the vertically disaggregated interconnect has a relatively low bandwidth at only 35GB/s per 4-core cluster in accessing the base die’s L3 and mesh network.

Despite a two-year gap with new core micro-architecture, new node, new advanced packaging and higher cost, Intel showed Clearwater Forest as being only 17% faster than Sierra Forest at the same core counts. With such limited performance gains despite much higher costs from low hybrid bonding yields, it is no wonder that Intel barely mentioned Clearwater Forest in their latest Q4 ’25 earnings. Our take is that Intel does not want to produce these chips in high volumes which hurt margins and would rather keep this as a yield learning vehicle for Foveros Direct.
