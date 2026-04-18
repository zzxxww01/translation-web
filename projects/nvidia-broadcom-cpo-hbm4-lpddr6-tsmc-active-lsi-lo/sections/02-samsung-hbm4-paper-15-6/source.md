Samsung was the only one among the top three memory vendors to present a technical paper on HBM4. Before ISSCC, we noted in our [Accelerator & HBM model](https://semianalysis.com/institutional/hbm4-samsung-incremental-progress-micron-execution-risk-rising-hbm3e-pricing-revised-up/) that Samsung had made great improvements in their HBM4 generation over their HBM3E. The data presented at ISSCC confirmed our analysis, with Samsung posting best-in-class performance - we have also detailed this development months ago, in a [model update note](https://semianalysis.com/institutional/samsung-hbm4-performance-leadership-sk-hynix-hbm4-issues/).

The technical details presented at ISSCC, combined with industry chatter we have gathered, clearly demonstrate that Samsung’s HBM4 is competitive with its peers. Notably, it can meet the pin speed required for Rubin while staying below 1V. While Samsung still lags SK Hynix in terms of reliability and stability, the company has made meaningful progress in closing the gap on the technology front and could challenge SK Hynix’s dominance in HBM. Their 1c-based HBM4 paired with an SF4 logic base die appears to deliver stronger performance in pin speed.

![](https://substackcdn.com/image/fetch/$s_!8SFa!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F515a99f4-5397-4b1a-9f95-d9a3dff37521_2880x1620.jpeg)

*Samsung HBM3E vs. HBM4 Specifications. Source: Samsung, ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!t-2P!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F773189fd-1dd5-434a-aa0c-694db785b9c9_2880x1620.jpeg)

*Samsung HBM4 Die Shots and Cross-Section. Source: Samsung, ISSCC 2026*

Samsung demonstrated a 36 GB, 12-high HBM4 stack featuring 2048 IO pins and 3.3 TB/s of bandwidth, built using 6th-generation 10nm-class (1c) DRAM core dies paired with an SF4 logic base die.

The most obvious architectural change from HBM3E to HBM4 is the process technology split between the core DRAM dies and the base die. HBM4 uses the DRAM process node only for the core die while the base die is manufactured with an advanced logic node unlike previous generations of HBM that used the same process for both.

The key architectural challenge arises as AI workloads demand higher bandwidth and faster data rates from HBM. By moving the base die to the SF4 logic process, Samsung enables higher operating speeds and lower power consumption. The operating voltage (VDDQ) fell 32%, from 1.1V in HBM3E to 0.75V in HBM4. A logic-based base die provides higher transistor density, smaller device dimensions, and better area efficiency due to smaller transistors and larger metal-layer stack availability as compared to a base die fabricated on a DRAM process. This helps Samsung’s HBM4 achieve — and significantly surpass — JEDEC’s HBM4 standard that we explain more at the end of this section.

![](https://substackcdn.com/image/fetch/$s_!SBki!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff3e96393-ade6-49e3-82fa-8127beff5ad4_2880x1620.jpeg)

*Samsung HBM4 Adaptive Body-Bias Control and Process Variation. Source: Samsung, ISSCC 2026*

Combined with adaptive body-bias (ABB) control, which mitigates process variation across stacked core dies, the doubled TSV counts further improve timing margin. Together, Samsung’s paper claimed that the ABB and the 4× higher TSV count allow their HBM4 to achieve operating speeds up to 13 Gb/s per pin.

The improvement brought by the SF4 base die and 1c DRAM core dies comes with a trade-off. Samsung’s choice of **SF4 for the logic base die comes at a higher cost** comparedwith competing approaches even though Samsung Foundry can offer discounts for their internal base die usage. SK Hynix is adopting **TSMC’s N12 logic process** for their HBM4 base die, while Micron relies on their **internal CMOS base-die technology,** both of which are lower-cost options than the near leading-edge SF4 node, even considering vertical integration cost advantages.

The 1c front-end manufacturing process has proved challenging for Samsung throughout 2025, especially given that the company skipped the 1b node and moved directly from 1a-based HBM3E to the 1c generation. Front-end yields for the 1c node were only around 50% last year, although they have been gradually improving over time. The lower yield poses a risk for their HBM4 margins.

Historically, Samsung’s HBM has earned lower margins than those of their top competitor, SK Hynix, a dynamic that we model across all vendors comprehensively in our [Memory Model](https://semianalysis.com/memory-model/). We have detailed wafer volumes, yields, density, COGS, and more for each vendors HBM, DDR, and LPDDR across various nodes.

Samsung’s strategy appears to be an aggressive adoption of a more advanced node for the base die to achieve superior performance and outpace their competitors, particularly as HBM requirements from leading customers such as NVIDIA continue to become more demanding.

Another key issue in HBM to address is tCCDR, the minimum interval required between consecutive READ commands issued across different stack IDs (SID). For AI workloads that rely heavily on parallel memory access across many channels, tCCDR directly impacts achievable memory throughput.

In a stacked DRAM architecture, multiple core dies are vertically integrated on top of a base die. This naturally introduces small delay differences across the stack, driven by factors such as process variation between the core dies and the base die, TSV propagation differences, and local channel variation.

The increased stack heights and channel counts, from 16 to 32, compound this challenge. As the channel counts and stack heights increase, the variation between the dies accumulates, causing larger timing mismatches across channels and dies that impact the achievable tCCDR and overall HBM performance.

![](https://substackcdn.com/image/fetch/$s_!YCM6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe56f1735-adbc-4038-8473-b27f5ae002fb_1611x1352.jpeg)

**Samsung HBM4 Per-Channel TSV RDQS Auto-Calibration Scheme. Source: Samsung, ISSCC 2026**

To address this issue, Samsung introduces a “per-channel TSV RDQS timing auto-calibration scheme.” After power-up, the system measures delay variation across channels using a replica RDQS path that mirrors the timing behavior of the real signal path. A time-to-digital converter (TDC) quantizes the timing differences, which are then compensated for using delay compensation circuits (DCDL) for each channel.

This calibration accounts for both global delay variation between stacked core dies and local per-channel variation, aligning timing across the stack. By compensating for these mismatches, Samsung significantly improves the effective timing margin and increases the maximum achievable data rate while maintaining the required tCCDR constraints. This scheme alone increased data rates from 7.8 Gb/s to 9.4 Gb/s.

Some of our readers who are well versed in memory technology may be asking: How is there enough die area to accommodate the significant increase in TSV counts? This is where the 1c node becomes important. Compared with the previous 1a node, 1c further shrinks the DRAM cell area, freeing up die space that can be used to integrate the larger number of TSVs required for HBM4.

![](https://substackcdn.com/image/fetch/$s_!FNwT!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F35b20c2b-2f00-4d4c-b05a-578d695a51c1_2880x1620.jpeg)

*Samsung HBM4 PMBIST Test Pattern Operation. Source: Samsung, ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!06LM!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fec777954-f7fa-44fb-a8b3-f295d57f3e59_2880x1620.jpeg)

*Samsung HBM4 PMBIST vs. HBM3E MBIST Comparison. Source: Samsung, ISSCC 2026*

Another key innovation enabled by the logic base die is Samsung’s Programmable Memory Built-In Self-Test (PMBIST) architecture. PMBIST allows the base die to generate fully programmable memory test patterns while supporting the complete JEDEC row and column command set, meaning the test engine can issue the same commands that a real system would generate and can do so at any clock edge and at full interface speed. In practical terms, this allows engineers to replicate complex real-world memory access patterns and stress the HBM interface under realistic operating conditions, which is difficult with traditional fixed-pattern test engines.

This approach represents a notable departure from HBM3E. As discussed earlier, the HBM3E base die is fabricated using a DRAM process, which imposed strict power and area constraints on the MBIST (Memory Built-In Self-Test) engine and limited testing to a small set of predefined patterns given the natural power and area disadvantage of DRAM against logic. By moving the base die to Samsung Foundry’s SF4 logic process, Samsung enables a fully programmable testing framework capable of running complex test algorithms and flexible access sequences.

This enables much more robust debugging and better yield learning for HBM. Engineers can create targeted stress patterns to validate critical timing parameters such as tCCDR and tCCDS, identify corner-case failures earlier in manufacturing, and accelerate characterization during chip-on-wafer (CoW) and system-in-package (SiP) testing. Put simply, PMBIST improves test coverage, debug efficiency, and ultimately production yield as HBM stacks grow more complex and operate at higher speeds.

![](https://substackcdn.com/image/fetch/$s_!E1zF!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8a03c69a-dc9b-4dfb-a6d2-ad4315760852_2880x1620.jpeg)

*Samsung HBM4 Shmoo Plot. Source: Samsung, ISSCC 2026*

Samsung also demonstrated strong pin speed results — their HBM4 is able to hit 11 Gb/s at sub-1V core voltage (VDDC), and up to 13 Gb/s at higher voltages. We have yet to see Samsung’s peers demonstrate comparable performance albeit they do have better reliability and stability.

Samsung’s implementation significantly exceeds the baseline specification of the official JEDEC HBM4 standard (JESD270-4), which specifies a maximum data rate of 6.4 Gb/s per pin and about 2 TB/s of bandwidth. Samsung demonstrates more than 2× the JEDEC-standard pin speed, reaching 13 Gb/s per pin and delivering 3.3 TB/s of bandwidth. Even at VDDC/VDDQ of 1.05V and 0.75V, the device can sustain a data rate of 11.8 Gb/s.
