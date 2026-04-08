![](https://substackcdn.com/image/fetch/$s_!wrPN!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faf081f84-4b44-4861-83b9-7467a1b74f89_2964x1485.png)

*Graviton CPU History. Source: AWS*

Amazon Web Services (AWS) was the first hyperscaler to successfully develop and deploy their own CPUs for the cloud. Thanks to the acquisition of the Annapurna Labs chip design team and ARM’s Neoverse Compute Subsystem (CSS) reference designs, AWS could now offer their EC2 cloud instances at lower prices thanks to a better margin profile by going directly to TSMC and OSAT partners for chip production as opposed to buying Intel Xeons.

The Graviton push started in earnest during the COVID boom with the Graviton2 generation, when AWS offered heavy discounting to entice cloud customers to port their programs over to the ARM ecosystem from x86. While not as performant on a per core basis compared to Intel’s Cascade Lake generation, Graviton2 brought 64 Neoverse N1 cores at a fraction of the price with significantly higher performance per dollar.

Graviton3’s preview in late 2021 brought several changes that focused on elevating per core performance to competitive levels. AWS moved to ARM’s Neoverse V1, a much larger CPU core with twice the floating point performance as N1, while keeping core counts at 64. A 10x7 Core Mesh Network (CMN) was employed with 65 cores printed on die, leaving room for 1 core to be disabled for binning. AWS also disaggregated the design into chiplets, with four DDR5 memory and two PCIe5 I/O chiplets surrounding the central compute die on TSMC N5, all connected with Intel’s EMIB advanced packaging. With the delays to Intel’s Sapphire Rapids, Graviton3 became one of the first datacenter CPUs to deploy DDR5 and PCIe5, a full year ahead of AMD and Intel, which we wrote about here.

* [Amazon Graviton 3 Uses Chiplets & Advanced Packaging To Commoditize High Performance CPUs | The First PCIe 5.0 And DDR5 Server CPU](https://newsletter.semianalysis.com/p/amazon-graviton-3-uses-chiplets-and) - Dylan Patel · December 2, 2021

Graviton4 continued scaling, adopting the updated Neoverse V2 core and increasing core counts and memory channels by 50% to 96 and 12-channels respectively, bringing 30-45% speedups over the previous generation. PCIe5 lane counts tripled from 32 to 96 lanes for much greater connectivity to networking and storage. Graviton4 also brought support for dual-socket configurations for even higher instance core counts.

![](https://substackcdn.com/image/fetch/$s_!P_3k!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcaa991f9-af71-4c1d-b519-c7aa45b5bfac_2732x1472.png)

*Graviton5 core diagram. Source: AWS*

In preview since December 2025, Graviton5 features another huge jump in performance with 192 Neoverse V3 cores, double that of the previous generation, with 172 Billion transistors on TSMC’s 3nm process. While L2 cache per core remains at 2MB, the shared L3 cache increases from a paltry 36MB on Graviton4 to a more respectable 192MB on Graviton5, with the extra cache acting as a buffer as memory bandwidth only went up by 57% (12-channel DDR5-8800) despite doubling core counts.

The packaging of Graviton 5 is very unique as we discussed on [Core Research](https://semianalysis.com/core-research/) and has large implications of a few vendors in the supply chain.

Interestingly, while the PCIe lanes were upgraded to Gen6, lane counts regressed from 96 lanes on Graviton4 to 64 on Graviton5, as apparently AWS was generally not deploying configurations using all PCIe lanes. This cost optimization saves Amazon alot on TCO while not impacting performance.

Graviton5 employs an evolved chiplet architecture and interconnect, with 2 cores now sharing the same mesh stop, arranged in an 8x12 mesh. While AWS did not show the packaging and die configurations this time, they ensured that Graviton5 does employ a novel packaging strategy, and that the CPU core mesh is split over multiple compute dies.

![](https://substackcdn.com/image/fetch/$s_!0qb4!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9280a965-5af9-4c30-8ae0-b107f9248e48_2697x1149.png)

*Graviton Pre-Silicon Design. Source: AWS*

In terms of CPU usage, AWS was proud to mention that they have been using thousands of Graviton CPUs internally in their CI/CD design integration flows and to run EDA tools to design and verify future Graviton, Trainium and Nitro silicon, creating an internal dogfooding cycle where Gravitons design Gravitons. AWS also announced that their Trainium3 accelerators will now use Graviton CPUs as head nodes, with 1 CPU to 4 XPUs. While the initial versions run with Graviton4, future Trainium3 clusters will be powered by Graviton5.
