![](https://substackcdn.com/image/fetch/$s_!sC88!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7520d55a-ba5b-466e-9799-72fe683a1923_2860x1588.png)

*AMD EPYC CPU Generations. Source: AMD*

![](https://substackcdn.com/image/fetch/$s_!Z99I!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc704a28b-2774-4428-9745-2cfdcf1f1573_2775x1508.png)

*Intel Criticizing AMD’s Naples. Source: Intel*

AMD’s return to the datacenter CPU market with their EPYC Naples 7001 series in 2017 caused quite a stir, with Intel mocking the design as “Four glued-together desktop die” with inconsistent performance. In reality, the small design team at AMD had to be resourceful, and could only afford to tape out a single die that had to be used for both desktop PCs, server and even embedded with integrated 10Gbit Ethernet on the same die.

![](https://substackcdn.com/image/fetch/$s_!NxBd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff6de7f59-7300-4154-aba5-836eae048878_3025x1693.png)

*AMD Zeppelin SoC Architecture. Source: AMD, ISSCC 2018*

Naples implemented a 4-die MCM with each “Zeppelin” die containing 8 cores, allowing AMD to exceed Intel’s 28 cores with 32. Each die holds 2 Core Complexes (CCX), with 4 cores and 8MB of L3 connected with a crossbar. An on-die Scalable Data Fabric enables inter-CCX communication. Infinity Fabric on Package (IFOP) links connected each die to the other 3 in the package, while Infinity Fabric Inter Socket (IFIS) links enabled dual-socket designs. Infinity Fabric enabled coherent memory sharing between dies, and was derived from their old HyperTransport technology.

This architecture meant that there was no unified L3 cache and core-to-core latencies varied greatly, with multiple hops required to go from a core in a CCX on one die to a core in another die. A typical dual socket server ended having four NUMA domains. Intra-CCX, Inter-CCX, Die-to-die MCM, Inter-Socket. Performance reflected this, as highly parallelizable tasks with minimal core to core and memory access such as rendering performed well, while memory and latency sensitive tasks that relied more on inter-core communication did poorly. As most software was also not NUMA aware, this gave Intel’s criticism a point for “inconsistent performance”.

### EPYC Rome’s Centralized IO

![](https://substackcdn.com/image/fetch/$s_!qr8U!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F89034fe0-5221-40fe-9936-7e7e779456d6_2830x1602.png)

*Rome and Milan SoC Architecture. Source: AMD*

The 2019 Rome generation saw a complete rethink of the die layout, taking advantage of heterogeneous disaggregation to create a 64-core part that far outstripped Intel who were still stuck at 28. Eight 8-core Core Compute Dies (CCD) surrounded a central I/O die containing the memory and PCIe interfaces, with the CCDs moving to the latest TSMC N7 process while the I/O die stayed on GlobalFoundries’ 12nm. The CCDs still consisted of two 4-core CCXs, but now have no direct communication with each other. Instead, all inter-CCX traffic is routed through the I/O die, where signals travel across the substrate over Global Memory Interconnect (GMI) links. This meant that Rome functionally appeared as sixteen 4-core NUMA nodes with only 2 NUMA domains.

VMs spun up on Rome had to be kept to 4 cores to avoid performance loss from cross-die communications, much like the prior Naples. This was addressed with the Milan generation in 2021 that increased CCX size to 8 cores by moving to a ring bus architecture, while reusing the same I/O die as Rome.

![](https://substackcdn.com/image/fetch/$s_!yJpR!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F053b0db0-b10d-46be-ab7c-6826eeb1b607_2777x1154.png)

*AMD Turin-Dense. Source: AMD*

Despite initial plans to adopt advanced packaging, AMD stuck to this familiar design for the next 2 generations as well, with 2022 Genoa moving to 12 CCDs and 2024 Turin with up to 16 CCDs on the 128-core EPYC 9755, all surrounding a central I/O die with upgraded DDR5 and PCIe5 interfaces.

The key benefit of this chiplet design is the scalability of core counts with just a single silicon tapeout. AMD only needs to design a single CCD to offer the full gamut of core counts across the SKU stack by including different numbers of CCDs. The small die area of each CCD also helps with yields and achieving earlier time to market when moving to a new process node. This contrasts with a mesh design that uses large reticle sized dies and requires multiple tapeouts for each core count offering with smaller meshes. Different CCD designs can also be swapped in while sharing the same IO die and socket platform, with AMD creating additional variants using the compact Zen 4c cores in Bergamo and Zen 5c cores for the 192-core Turin variant. We wrote about this new core variant for efficient cloud computing here. Disaggregation also allows smaller versions to be made with EPYC 8004 Siena processors using just 4 Zen 4c CCDs on a 6-channel memory platform.

* [Zen 4c: AMD’s Response to Hyperscale ARM & Intel Atom](https://newsletter.semianalysis.com/p/zen-4c-amds-response-to-hyperscale) - Dylan Patel and Gerald Wong · June 5, 2023
