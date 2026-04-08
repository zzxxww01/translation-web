China’s home grown CPU efforts are continuing apace, with both Loongson and Alibaba’s Yitian line offering locally designed options. However, the biggest player in the market is Huawei, who have refocused their datacenter CPU roadmap with their Kunpeng processor series. Huawei has some of the most capable design engineers from their HiSilicon team, with custom TaiShan CPU cores and data fabrics that are worth keeping an eye on.

Huawei’s first few generations of datacenter CPUs used the standard mobile ARM Cortex cores. The 2015 Hi1610 featured 16 A57 cores. 2016’s Hi1612 doubled core counts to 32, while the Kunpeng 916 in 2017 updated the core architecture to Cortex-A72. All three generations were fabbed on TSMC 16nm.

![](https://substackcdn.com/image/fetch/$s_!nuLP!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9050cd76-7b26-4fa8-b999-8b5a81a3a501_1306x2336.png)

*Kunpeng 920 Die Shots. Source: 万扯淡*

The Kunpeng 920 arrived in 2019 with an ambitious multi-chiplet design and 64 custom cores. Two compute dies on TSMC 7nm each contained 8 clusters of 4 TaiShan V110 cores running on the ARM v8.2 ISA. The clusters are connected with a ring bus to four channels of DDR4 on the same die totaling 8-channels across the two compute dies. Kunpeng 920 was the first CPU to adopt TSMC’s CoWoS-S advanced packaging, with a large silicon interposer connecting 2 compute dies to an I/O die with 40 PCIe Gen 4 lanes and dual integrated 100 Gigabit Ethernet controllers using a custom die to die interface. While Kunpeng 920 integrated many novel technologies, the US sanction on Huawei which curtailed their supply of TSMC had disrupted their CPU roadmap, as the next Kunpeng 930 generation failed to release in 2021.

![](https://substackcdn.com/image/fetch/$s_!J5oo!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc84b6c66-8fe3-4f33-812d-aa3ddfd7c144_1300x1833.png)

*Kunpeng 920B Die Shots. Source: Kurnal*

Instead, an updated Kunpeng 920B was quietly released in 2024 with several upgrades. The TaiShan V120 cores now support SMT, with 10 clusters of 4 on each of the two compute dies for 80 cores and 160 threads. Core interconnect and layout remained similar to the Kunpeng 920 with 8 channels of DDR5 on the compute dies. The I/O die is now split into halves with the compute dies in the middle. We believe the 5 year gap between CPU generations were the result of US sanctions and having to redesign the chip for the SMIC N+2 process.

![](https://substackcdn.com/image/fetch/$s_!ZzDl!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffa36c618-5da3-4cc3-9235-a3b4f5322892_3035x1034.png)

*Huawei Kunpeng CPU Roadmap. Source: Huawei*

![](https://substackcdn.com/image/fetch/$s_!r1Rj!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F651c2acf-e470-4797-b124-9cdd060ca65d_3065x778.png)

*Huawei TaiShan 950 SuperPoD. Source: Huawei*

For 2026, Huawei is updating its CPU line again with the Kunpeng 950 and configuring them in TaiShan 950 SuperPoD racks for general purpose compute. Kunpeng 950 promises a 2.9x speedup on OLTP database performance over the Kunpeng 920B using their proprietary GaussDB Multi-Write distributed database architecture. To achieve this, core counts more than doubled to 192 using a new LinxiCore that retains SMT support. A smaller 96 core version will also be produced. 16 dual-socket servers go into each TaiShan 950 SuperPoD rack with up to 48TB of DDR5 memory, indicating a 12-channel memory design. These racks also integrate storage and networking, and will be adopted by Oracle’s Exadata database servers and used by China’s finance sector. The design will likely be produced on SMIC’s N+3 process that recently debuted in the Kirin 9030 smartphone chip.

Huawei’s roadmap continues into 2028 with the Kunpeng 960 series. This generation follows the trend of splitting the design into two variants. A 96 core, 192 thread high performance version will be made for AI head nodes and databases that promises a 50%+ improvement in per core performance, while a high-density model for virtualization and cloud compute will increase core counts to 256 and possibly beyond. By then, we expect Huawei to take significant share in Chinese hyperscaler CPU deployments.

Below we present our CPU roadmap to 2028, and detail the key features and architectural changes of the datacenter CPUs beyond 2026, including AMD’s Verano and Florence, Intel’s Coral Rapids and cancelled CPU lines, ARM’s Venom specifications, Qualcomm’s return to the datacenter CPU market with SD2, and include NVIDIA’s Bluefield-4 as a sign of how CPU deployments are evolving going forward. We then discuss the impacts of the DRAM shortage on each datacenter CPU segment and look at future CPU trends, highlighting crucial design aspects that will shape CPUs in the next decade.
