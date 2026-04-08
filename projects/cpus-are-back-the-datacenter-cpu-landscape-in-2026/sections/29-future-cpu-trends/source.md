The humble CPU will continue to evolve throughout the next decade as computing needs change over time. The current RL training and Agentic tool use era is accelerating CPU demand like never before, with CPU designs beginning to diverge to fit three use cases.

* High core density efficient CPUs with high throughput for cloud and general purpose compute such as Graviton5

* High performance per core CPUs with high memory bandwidth and tight integration with AI accelerators for coherent memory expansion such as Vera

* Data processing and networking capable CPUs and DPUs to deal with the massive data requirements of AI clusters and model context offloads such as Bluefield-4

Going forward, we are likely to see even more specialization. In all cases, CPU sockets and core counts are getting larger with higher memory and I/O speeds and widths, placing greater pressure on CPU interconnects and data fabrics. NoC designers will be relied on even more to create designs with very high bisection bandwidths across thousands of square millimetres of silicon and multiple chiplet crossings while maintaining full coherency with external devices and requiring much lower latencies than GPU fabrics.

The adoption of LPDDR in the datacenter will continue, with PCB layer count and complexity already pushed to the limit for the large 16-channel memory designs. LPDDR6 SOCAMM modules enable far higher bandwidth density while maintaining higher capacities than on-package memory.

The winning design will come from the one that has the best data fabric. Some designs will employ Gigabytes of cache to hide latencies and improve memory-bound performance, while others will go to town with CXL memory expanders. We may yet see the return of HBM on CPUs, last seen in Sapphire Rapids Xeon Max and AMD’s MI300C.

Looking even further out, will the datacenter CPU as we know it today still exist? The next era of compute demand may see the move to APU designs pioneered with AMD’s MI300A with integrated CPU cores, removing the need for CPU head nodes. APUs may also be an option for RL Training specific accelerators that can run the RL Environment locally with unified memory, shortening the round trip time of going to general purpose CPU clusters for RL. Co-Packaged Optics with memory disaggregation and pooling in JBOM “Just a Bunch of HBM” concepts and Credo’s Omniconnect memory gearboxes may reduce the need for memory expander CPUs and lower CPU attach ratios (such as 1 CPU per rack of accelerators). We also see a future where the CPU ends up integrated as the core of a massive >400T switch. In any case, the CPU will continue to live on as the fundamental core of the computer.

Contact us at sales@semianalysis.com for the following data.

* Bill of Materials (BOM) Costing

+ Provide a table that breaks down the cost of production of 2026 x86 Datacenter CPUs. For each processor family, costing of different product tiers in the SKU stack will be provided.

- Variants include AMD Venice SP7 and SP8 in both Classic and Dense CCD configurations, Intel Diamond Rapids-AP UCC 16-channel and Diamond Rapids-SP HCC and LCC 8-channel.

- Include BOM costing of NVIDIA Grace and Vera ARM CPUs as well as other discussed ARM CPUs as a means of comparison to the x86 CPUs listed above.

+ Cost breakdown into active silicon (including CPU, SoC, and I/O), advanced packaging (2.5D and hybrid bonding), traditional packaging cost including yield impact and product testing costs.

+ Active Silicon factors in all die sizes, process technology and metal layers, yielded dies per wafer, wafer cost, and number of dies per package. For example, active silicon cost of the top-end 256-core AMD Venice SP7 will be computed from TSMC N2 wafer cost with 8 compute dies and TSMC N6 wafer cost with 2 IO dies.

+ Advanced packaging cost factors in type (e.g., CoWoS-L for AMD Venice, EMIB and Foveros Direct 3D for Intel Diamond Rapids), area of interposer and Hybrid bond size, number of die to-die links and Known Good Die testing. Yield loss from the advanced packaging process will be accrued as additional active silicon cost due to wasting good dies on faulty assemblies.

+ Traditional packaging cost includes substrate cost that factors in material, layer count, and area, as well as integrated passive devices, TIM and lid costs

+ Testing costs include ATE/SLT and Burn-in cost on the package level. Losses from device binning will increase the average per package BOM cost.

* Architectural Design and Performance Analysis

+ List the full specifications of AMD Venice and Intel Diamond Rapids, including but not limited to: core counts, TDP, cache sizes, memory bandwidth, PCIe and CXL IO lane counts, multi socket interconnect specifications (AMD XGMI and Intel UPI).

+ Provide diagrams of CPU floorplan layout and topology, including core and Last Level Cache placement, mesh interconnect sizes, die-to-die PHYs and IO PHYs.

+ Analysis of floorplan layout and topology and the changes across CPU generations, with commentary on the difficulty of scaling a mesh architecture to large sizes.

+ Comparison of layout between AMD, Intel, ARM and its impact on NUMA domains and core clustering with multiple Last Level Cache domains

+ Provide integration schematics of advanced packaging, including layout of chiplets, interposer sizes, and pitches.

+ Discussion of advanced packaging technology selection(CoWoS-L (AMD Venice), CoWoS-R (NVIDIA Vera), and EMIB/Foveros Direct 3D (Intel Clearwater Forest)) and its impact on cost, power, and performance

+ Detail scalability challenges on high core count CPU designs and the impact to inter-core latency, memory access uniformity and latency

+ Provide internal performance estimates (e.g. SPECint2017) for AMD Venice and Intel Diamond Rapids with analysis on performance scalability with respect to core count and chip cost
