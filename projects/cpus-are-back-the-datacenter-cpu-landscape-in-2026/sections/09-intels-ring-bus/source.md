![](https://substackcdn.com/image/fetch/$s_!u8AU!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe4c3bb6f-9b4b-47c6-9b22-a50aecc28ea0_2424x1789.png)

*Intel Nehalem-EX Ring Interconnect. Source: Intel, Hot Chips 2009*

To scale past this limit, Intel implemented a ring bus architecture with their Nehalem-EX (Beckton) Xeons in 2010, bringing 8 cores with integrated memory controllers and inter-socket QPI links into a single die. Implemented in earlier years within ATi Radeon GPUs and the IBM Cell processor, the ring bus arranges all nodes into a loop, with ring stops integrated into the L3 cache slices and wiring in the metal layers above the cache. Caching and Home agents deal with memory snooping between cores and coherence with the memory controller.

Data from each ring stop’s core and L3 cache slice is queued and injected into the ring, with data advancing one stop per clock to its target destination. This means core to core access latency is no longer uniform, with cores on opposite sides of the ring having to wait additional cycles compared to directly adjacent cores. To help with latency and congestion, two counter rotating rings are implemented, with the optimal direction of travel chosen based on address and ring loading. With wiring complexity now moderated, Intel could scale core counts to 8 on Nehalem-EX and 10 for Westmere-EX. However, scaling beyond that with a single ring would lead to problems with coherence and latency as the ring gets too long.

### Ivy Bridge-EX Virtual Rings

![](https://substackcdn.com/image/fetch/$s_!4FIz!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0830e24f-4740-4e69-8707-090b48c6ec4c_2332x1803.png)

*Intel Ivytown Virtual Rings. Source: Intel, Hot Chips 2014*

To scale core count to 15 for the Ivy Bridge generation, Intel had to get clever with the routing topology. The cores are arranged in three columns of five, with three ‘virtual rings’ looping around the columns. Switches in the ring stops controlled the direction of travel along the half rings, creating a “virtual” triple ring configuration.

### Haswell and Broadwell Dual Rings

![](https://substackcdn.com/image/fetch/$s_!gHb0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5b1e5413-09bc-46c0-9cd2-64e233a613ab_2987x1679.png)

*Haswell HCC Dual Ring Bus. Source: Intel*

In 2014, Intel changed topologies yet again with the 18-core Haswell HCC die featuring dual independent counter rotating ring buses connected with a pair of bi-directional buffered switches. Memory controllers were split amongst the two rings, with the 8-core ring also housing the IO ring stops. The MCC die variant wrapped a single half-ring back on itself. Broadwell HCC, released in 2015, brought core counts up to 24 with dual 12-core ring buses.

The downside to stitching multiple rings together is the increased variability in core to core and memory access latency, especially so when cores on one ring are accessing the memory of the other ring. This Non Uniform Memory Access (NUMA) was detrimental to system performance for programs that are latency sensitive with high core to core interactivity.

To help with this, Intel offered a “Cluster on Die” configuration option in the BIOS that treated the two rings as independent processors. The operating system would show the CPU being split into two NUMA nodes, each with direct access to half the local memory and L3 cache. [Testing in CoD mode](https://old.chipsandcheese.com/2023/11/07/core-to-core-latency-data-on-large-systems/) showed that latency within each ring stayed under 50ns while access to the other ring took over 100ns, illustrating the latency penalty of going through the buffered switches.

While these methods helped Intel increase core counts to 24, it was not an elegant nor scalable solution. Adding a third ring and two more sets of buffered switches would be too complicated and impractical, creating many NUMA clusters. A new interconnect architecture was required for more cores.
