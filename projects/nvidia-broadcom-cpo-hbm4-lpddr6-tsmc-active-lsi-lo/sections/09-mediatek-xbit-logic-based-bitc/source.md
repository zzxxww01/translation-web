![](https://substackcdn.com/image/fetch/$s_!m8pd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa42110ab-a204-4a5f-8977-830bd38e06ea_1283x461.jpeg)

*SRAM HC Bitcell Density vs. Logic-Based MBFF Across Nodes. Source: MediaTek, ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!NbiN!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fda693b39-6780-47ce-ac48-bf8a5b5a489f_2880x1620.jpeg)

*SRAM Bitcell Scaling Limitations: Area and Voltage Constraints. Source: MediaTek, ISSCC 2026*

[SRAM scaling is dead.](https://newsletter.semianalysis.com/i/174558465/sram-scaling-beating-a-dead-horse) Despite logic area decreasing by 40% from N5 to N2, 8-transistor high-current SRAM bitcells have only decreased in area by 18%. 6-transistor high-current (6T-HC) bitcells are even worse, only decreasing by 2%. Assist circuitry has scaled more, but it's not free lunch.

It is well known that [N3E’s high-density bitcell is a regression from N3B’s, falling back to N5’s density](https://newsletter.semianalysis.com/i/175660907/n3-technology-nodes). In this paper, MediaTek shed some light on the high-current bitcell. N3E’s high-current bitcell increased in area by 1-2% over N5. The density decreased from ~39.0 Mib/mm² to ~38.5 Mib/mm². Do note these figures do not account for assist circuitry overhead.

![](https://substackcdn.com/image/fetch/$s_!_Cbb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe8879827-c259-4dfd-a9ae-79a59dbfc37d_2880x1620.jpeg)

*8T Bitcell NMOS/PMOS Layout Challenges with Logic Rules. Source: MediaTek, ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!oxdV!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd4abf3fe-77e4-4333-a1c8-da1eeedb5789_2520x1408.jpeg)

*MediaTek 10T xBIT Balanced Bitcell Circuit Design. Source: MediaTek, ISSCC 2026*

In modern logic nodes, 6T bitcells have 4 NMOS and 2 PMOS transistors, while 8T bitcells have 6 and 2 respectively. The unequal number of NMOS and PMOS transistors requires specialized rules and makes layout more inefficient. MediaTek’s novel bitcell is a 10-transistor cell, named the xBIT, with 4 NMOS and 6 PMOS transistors or vice versa. The two variants of the bitcell can be arranged together into a rectangular block, with 20 transistors, storing 2 bits.

![](https://substackcdn.com/image/fetch/$s_!n1LG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa550e975-e262-4350-8c6f-380c90b3ae01_2520x1408.jpeg)

*xBIT vs. Foundry 8T Density and Power Comparison. Source: MediaTek, ISSCC 2026*

When compared to the PDK’s standard 8T bitcells, the xBIT achieved 22% to 63% higher density, with the largest gains at lower wordline widths. Power has also improved greatly, with the average read/write power reduced by over 30%, and leakage reduced by 29% at 0.5V. At 0.9V, performance was similar to an 8T bitcell and at 0.5V, although it was 16% slower than the 8T bitcell, it was fast enough not to be the bottleneck in a processor, and the voltage range was large enough for voltage-frequency scaling.

![](https://substackcdn.com/image/fetch/$s_!xu_9!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6f2a3a1a-a796-4979-8477-fab6bf41c58d_1699x1094.jpeg)

*xBIT Shmoo Plot. Source: MediaTek, ISSCC 2026*

MediaTek also showed a shmoo plot of the xBIT cell, going from 100 MHz at 0.35V, up to 4GHz at 0.95V.

We will be doing a deep dive into SRAM and its scaling factors in an upcoming newsletter article.
