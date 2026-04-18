We have extensively covered challenges in continuing to scale DRAM.

* [The Memory Wall: Past, Present, and Future of DRAM](https://newsletter.semianalysis.com/p/the-memory-wall) - Dylan Patel, Jeff Koch, and 3 others · September 3, 2024

At [VLSI 2025, SK Hynix detailed their own 4F² Peri-Under-Cell (PUC) DRAM](https://newsletter.semianalysis.com/i/174558662/dram-4f2-and-3d). At ISSCC, Samsung disclosed their own implementation of a 4F² Cell-on-Peripheral (COP) DRAM. PUC and COP are the same architecture with different names.

![](https://substackcdn.com/image/fetch/$s_!R4vq!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1d73da51-6e13-4c3f-a013-11188a56fcaf_2880x1620.jpeg)

*4F² VCT DRAM Cell Architecture. Source: Samsung, ISSCC 2026*

The architecture for 4F² cells is the same as SK Hynix’s, with vertical channel transistors (VCT), and capacitors above the drain.

![](https://substackcdn.com/image/fetch/$s_!4BMO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb889dd90-99fa-42d6-acc7-c8198d858390_2880x1620.jpeg)

*Cell-on-Peripheral (COP) DRAM Stack Architecture. Source: Samsung, ISSCC 2026*

The vertical architecture presented by Samsung is essentially the same as that used by SK Hynix, with a cell wafer hybrid bonded on top of a peripheral wafer. With this architecture, it is possible to use a DRAM node for the cell wafer while using a more advanced logic node for the periphery.

![](https://substackcdn.com/image/fetch/$s_!cEvZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff2c22653-7ddd-4eb8-87da-131a04a44314_2880x1620.jpeg)

*COP Architecture Comparison for DRAM vs. NAND. Source: Samsung, ISSCC 2026*

Samsung notes that hybrid bonding for COP has already been used for NAND. This is true for other NAND manufacturers, but Samsung has not brought hybrid bonding for NAND into high volume production and is still years away from doing so.

Moreover, the number of inter-wafer connections for DRAM is an order of magnitude higher than for NAND and requires much tighter pitches. To reduce the number of inter-wafer interconnections, Samsung has employed two novel approaches.

![](https://substackcdn.com/image/fetch/$s_!vZzA!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F058cc85d-e7c7-4d2c-bafe-43cdc55f9607_2880x1620.jpeg)

*COP NOR-Type Sub-Wordline Driver Optimization. Source: Samsung, ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!Q4d0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F148125f3-7781-496c-9df5-f4ef6dd56b70_2880x1620.jpeg)

*COP Even/Odd Column Select MUX Optimization. Source: Samsung, ISSCC 2026*

First, they have reorganized the sub-wordline drivers (SWD) from 128 per cell block to 16 groups of 8. This reduces the number of signals required for the SWD by 75%.

Next, they split the column select into an even and an odd path. This requires twice the multiplexers (MUX) but halves the column select line (CSL) count to 32 per data pin.

![](https://substackcdn.com/image/fetch/$s_!-Vrx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F76c17f7b-d3ae-4595-bee1-b49403715d62_2880x1620.jpeg)

*COP Core Circuitry Layout Under Cell Array. Source: Samsung, ISSCC 2026*

With hybrid bonding, the core circuitry, that is, bitline sense amplifiers (BLSA) and SWD can be placed under the cell array. The goal is for the core circuits to occupy the same area as the cell array to increase overall density.

![](https://substackcdn.com/image/fetch/$s_!2ZFO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe3f4b60f-a3f5-4985-a5f6-d3a804ae9a69_2880x1620.jpeg)

*COP Core Circuitry Layout Options. Source: Samsung, ISSCC 2026*

Samsung adopted the “sandwich” structure, which allows them to maximize the area efficiency of the core circuitry, and reduce the edge region area, which is not under any cells.

![](https://substackcdn.com/image/fetch/$s_!NQFx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb1824aa4-f1c3-4174-94c7-320067ca2401_2880x1620.jpeg)

*COP Sandwich Structure Area Efficiency. Source: Samsung, ISSCC 2026*

The area used by the core circuitry was reduced from 17.0% down to only 2.7%, a significant improvement, directly translating to overall die size reductions.

In traditional DRAM, increasing the number of cells per bitline would result in a significant increase in chip area, while for VCT DRAM, the increase is almost negligible as the core circuitry is all below the cells.

![](https://substackcdn.com/image/fetch/$s_!cPId!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3bfef447-2020-4611-af35-496a0f7926c9_2880x1620.jpeg)

*Samsung 4F² COP DRAM Summary and Die Shot. Source: Samsung, ISSCC 2026*

Samsung did not provide any density figures for this chip, only stating that it was a 16 Gb chip on a 10nm DRAM process.

Samsung noted that the VCT DRAM suffers from the floating-body effect, increasing leakage and reducing retention time. Mitigating this effect remains a key challenge for 4F² adoption.

Despite these challenges, we still expect 4F² hybrid bonded DRAM to arrive in the latter part of the decade as early as the generation after 1d. Our [memory model tracks the timing and ramp of each node in detail](https://semianalysis.com/memory-model/). The current memory pricing landscape largely incentivizes the ramp and introduction of new nodes with higher bit densities to improve bit output per fab. On the otherhand, performance/$ of memory is highly sought after more than capacity for many use cases.
