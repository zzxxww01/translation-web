Rebellions is a South Korean startup working on AI accelerators. At ISSCC, they published the first architectural breakdown of their new accelerator, the Rebel100. Unlike other accelerators, which are generally manufactured at TSMC, Rebellions chose Samsung Foundry’s SF4X node. With Nvidia, AMD, Broadcom and others hogging most of TSMC’s capacity, this allows them more flexibility.

![](https://substackcdn.com/image/fetch/$s_!HCo6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff2ea04c2-71cf-4065-98b1-606182921d24_1068x801.jpeg)

*Rebellions Rebel-Quad (now Rebel100) Summary from Hot Chips 2025. Source: Rebellions via [ServeTheHome](https://www.servethehome.com/rebellions-rebel-quad-ucie-and-144gb-hbm3e-accelerator-at-hot-chips-2025/)*

At Hot Chips 2025, Rebellions demonstrated the chip running Llama 3.3 70B. The specs have remained the same between Hot Chips and ISSCC. One key point to note is the use of Samsung’s I-CubeS interposer technology. While the Hot Chips slide mentions the usage of TSMC’s CoWoS-S, we have clarified that this was a mistake on the slide, and that it has always been I-CubeS.

We have recently mentioned that [CoWoS-S capacity constraints have been easing](https://newsletter.semianalysis.com/i/190110359/cowos-tight-but-easing). That said, Samsung may have offered steep discounts to bundle I-CubeS advanced packaging with their front-end process — sparing the startup from having to find and validate a separate advanced packaging supplier. Samsung may have also conditioned the availability of their HBM on using I-CubeS.

I-CubeS has not seen adoption among any of the leading AI accelerators, and this could be Samsung’s attempt to break into the market. There are only 5 confirmed users of I-CubeS: eSilicon, Baidu, Nvidia, Rebellions and Preferred Networks.

The first is a networking ASIC by eSilicon on Samsung’s 14LPP with HBM2. Baidu’s Kunlun1 accelerator is similar, using Samsung’s 14LPP process and 2 HBM2 stacks. When the CoWoS-S capacity was very tight back in 2023, Nvidia outsourced a small amount of H200 production to I-CubeS. Then, there is the Rebel100 and lastly, a planned accelerator from Preferred Networks on the SF2 process.

![](https://substackcdn.com/image/fetch/$s_!Wj1c!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F91f29194-e088-40ef-b134-ac45449d21ae_2880x1620.jpeg)

*Rebellions Rebel100 Multi-Die Architecture. Source: Rebellions, ISSCC 2026*

The Rebel100 uses 4 compute dies and 4 HBM3E stacks. Each die has 3 UCIe-A interfaces. However, only two are used on each die, clocked at 16 Gb/s.

![](https://substackcdn.com/image/fetch/$s_!Rt0c!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff9b5a17f-feb0-4c70-b528-cae2a38c11f3_2880x1620.jpeg)

*Rebellions Rebel100 Package-Level Modularity. Source: Rebellions, ISSCC 2026*

Rebellions claims that the design is reconfigurable at the package level, where additional IO or memory chiplets can be added to integrate with Ethernet for scale-up. This is where the remaining UCIe-A interface would be used.

Rebellions stated that the IO chiplets would be taped out by 1Q2026. There was no provided timeline for the memory chiplets.

![](https://substackcdn.com/image/fetch/$s_!kIab!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcbab43a4-26b7-4011-bfeb-ea01c4902a56_2880x1620.png)

*Rebellions Rebel100 Summary and Roadmap. Source: Rebellions, ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!NxmQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F759c00f2-e242-404b-a841-5e4458a75e4c_2880x1620.png)

*Rebellions Rebel100 Integrated Silicon Capacitors for HBM3E Power Quality. Source: Rebellions, ISSCC 2026*

They have also integrated silicon capacitors beside each HBM3E stack to improve power quality for HBM3E and critical control blocks.
