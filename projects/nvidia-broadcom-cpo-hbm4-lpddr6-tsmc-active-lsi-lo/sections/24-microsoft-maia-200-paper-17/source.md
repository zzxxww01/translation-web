Microsoft detailed their Maia 200 AI accelerator. The paper was less of a research paper and more of a white paper, with only a single image, a spec sheet comparing it to the Maia 100. Makes sense given a lot of Maia 200 claims are dubious such as the flops/mm^2 and flops/w.

While the Maia 100 was designed in a pre-GPT era, Maia 200 was designed for the current age of models and specifically inference. Earlier this year, Maia 200 nodes were made generally available on Azure.

![](https://substackcdn.com/image/fetch/$s_!3VIK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0c381cad-9332-483a-9fd7-8de08cd7d90a_2880x1620.jpeg)

*Microsoft Maia 200 Specifications Summary. Source: Microsoft, ISSCC 2026*

Maia 200 is the last holdout of reticle-scale monolithic designs. Every major HBM-equipped training and inference accelerator has moved on to multi-chip designs with 2, 4, or even 8 compute dies per package. Every single mm² of the die has been hyper-optimized for one purpose. Unlike with an Nvidia or AMD GPU, there is no legacy hardware for media or vector operations. Microsoft has pushed the reticle-scale monolithic approach to its limit on TSMC’s N3P process, packing in over 10 PFLOPs of FP4 compute, 6 HBM3E stacks, and 28× 400 Gb/s full-duplex D2D links.

![](https://substackcdn.com/image/fetch/$s_!oV7g!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F98820b64-6a10-4132-b24a-a2122f7417ad_2880x1620.jpeg)

*Microsoft Maia 200 Package Cross-Section. Source: Microsoft, ISSCC 2026*

On the package-level, Maia 200 is very standard, mimicking the H100. A CoWoS-S interposer, with 1 main die, and 6 HBM3E stacks.

![](https://substackcdn.com/image/fetch/$s_!1q24!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4949a336-f267-4f4c-b813-1f6af0d7f629_506x541.jpeg)

*Microsoft Maia 200 Die Floorplan. Source: Microsoft, ISSCC 2026*

The long sides of the chip are covered in 3 HBM3E PHYs each, while the short sides each have 14 of the 28 lanes of 400 Gb/s D2D links. In the center, there is 272 MB of SRAM, with 80 MB of TSRAM (L1) and 192 MB of CSRAM (L2).

![](https://substackcdn.com/image/fetch/$s_!Wj4l!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F62240549-cf4a-4472-8294-7b7b2bca21fa_2880x1620.jpeg)

*Microsoft Maia 200 Scale-Up Network and IO. Source: Microsoft, ISSCC 2026*

The Maia 200 has two different kinds of links, fixed links between other chips in the same node, and switched links between a chip and a switch. 21 links are configured as fixed links, 7 to each other chip, while the remaining 7 links are configured as switched links to one of four in-rack switches.

We will be publishing a deep dive into the Maia 200, its microarchitecture and network topology, for institutional subscribers.
