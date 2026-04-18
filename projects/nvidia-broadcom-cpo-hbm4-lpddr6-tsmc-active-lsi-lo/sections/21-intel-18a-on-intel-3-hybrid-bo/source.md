![](https://substackcdn.com/image/fetch/$s_!L-SD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffc1e02d7-2ca4-4129-9200-e99084fa4cfc_1792x1265.jpeg)

*Intel M3DProc 18A and Intel 3 Die Floorplan. Source: Intel, ISSCC 2026*

Intel disclosed their first hybrid bonded chip, the M3DProc. It consists of an Intel 3 bottom die, and an 18A top die. Each die contains 56 mesh tiles, cores and DNN accelerator tiles, respectively. The two dies are bonded together with Foveros Direct, hybrid bonding at a 9μm pitch.

![](https://substackcdn.com/image/fetch/$s_!Ysv3!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F636479de-4917-48f9-b513-7c57fe81968e_2494x1403.jpeg)

*Intel M3DProc 3D Mesh Architecture. Source: Intel, ISSCC 2026*

The mesh tiles are arranged in a 14×4×2 3D mesh, with SRAM being shared across both dies.

![](https://substackcdn.com/image/fetch/$s_!6vZe!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc2a08665-501d-4c3b-a54a-0bfae0dc5258_2412x910.jpeg)

*Intel M3DProc 2D vs. 3D Throughput and Energy Efficiency. Source: Intel, ISSCC 2026*

Intel found that the 3D mesh reduces latency and increases throughput by almost 40%. They also tested the energy efficiency of transferring data, with 2D being within the 56 mesh tiles of the bottom die, and 3D being 28 adjacent mesh tiles across both dies. The results show that the Hybrid Bonding Interconnect (HBI) had a negligible impact on efficiency.

![](https://substackcdn.com/image/fetch/$s_!aWNv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4877bf3c-30c1-4278-b85e-65ddbc343f1b_1362x1400.jpeg)

*Intel M3DProc Tile Bonding Floorplan. Source: Intel, ISSCC 2026*

Each tile has 552 pads, with just under half used for data, and just under a quarter used for power.

In terms of packaging, M3DProc is similar to Clearwater Forest (CWF). CWF has Intel 3 base dies, connected to 18A compute dies via 9μm Foveros Direct.

The M3DProc achieves 875 GB/s 3D bandwidth, while each CWF compute die only achieves 210 GB/s. This chip’s 3D NoC has a significantly higher bandwidth density. CWF uses Foveros Direct to disaggregate the CPU core cluster’s L2 cache from the base L3 with 6 clusters per top die at 35GB/s each for 210GB/s per top die. M3DProc’s 875GB/s 3D bandwidth is aggregated over 56 vertical tile connections, or 15.6GB/s each over a far smaller area.
