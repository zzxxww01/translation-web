SanDisk and Kioxia demonstrated their BiCS10 NAND, with 332 layers and 3 decks. This is the highest reported NAND bit density, at 37.6 Gb/mm², dethroning the previous champion, [SK Hynix’s 321L V9](https://newsletter.semianalysis.com/i/184077729/3d-nand-hynix-321-layer).

![](https://substackcdn.com/image/fetch/$s_!xViG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9f240c14-4a4f-4fab-bc19-194185a47c6b_2880x1620.jpeg)

*BiCS10 Die Shot and Density Comparison vs. SK Hynix and Samsung V9. Source: SanDisk/Kioxia, ISSCC 2026*

Despite using a similar architecture with 6 planes, 3 decks, and a similar number of layers, SK Hynix falls behind, with 30% lower bit density. In a QLC configuration, BiCS10 has a bit density of 37.6 Gb/mm², while SK Hynix’s V9 has a bit density of only 28.8 Gb/mm². While in a TLC configuration, the densities are 29 and 21 Gb/mm² respectively, another example of SK Hynix’s trailing position.

![](https://substackcdn.com/image/fetch/$s_!mqol!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6701cf01-e5c3-4aeb-87e6-ab7e99222f7d_2880x1620.jpeg)

*NAND 1×6 vs. 2×3 Plane Configuration Comparison. Source: SanDisk/Kioxia, ISSCC 2026*

Moreover, BiCS10 features a 6-plane configuration, increasing IO bandwidth by 50%. There are two ways to implement a 6-plane configuration, 1×6 and 2×3. SK Hynix chose to use a 2×3 configuration, while SanDisk and Kioxia have decided to use a 1×6 configuration.

A 1x6 configuration has fewer ground pads and reduces area by 2.1%. However, the lower number of ground pads and vertical power tracks constrains power distribution.

![](https://substackcdn.com/image/fetch/$s_!qU7L!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe1c58eb6-654f-4ec5-9d5b-14d27c7f3679_2880x1620.jpeg)

*BiCS10 CBA Additional Top-Metal Layer for Power Distribution. Source: SanDisk/Kioxia, ISSCC 2026*

By using the CBA (Cell Bonded Array) architecture, SanDisk and Kioxia are able to customize the CMOS wafer process. By adding another top-metal layer in parallel to the existing one, they created a stronger power grid and overcame their power distribution constraints.

![](https://substackcdn.com/image/fetch/$s_!6HeL!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3c965c54-2786-4298-bdfc-f916f5133490_2880x1620.jpeg)

*Multi-Die NAND Idle Power Penalty and Die-Gating Solution. Source: SanDisk/Kioxia, ISSCC 2026*

Stacking more dies is essential to increasing storage density. However, in multi-die architectures, the idle current from unselected dies is approaching the active current of the selected die. SanDisk implemented a gating system to fully shut down the data path of the unselected dies, reducing the idle current by two orders of magnitude.
