![](https://substackcdn.com/image/fetch/$s_!cMe7!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3676208d-dd25-42ba-8f03-cc1359a1076c_2029x1057.png)

*Bluefield-4 NVIDIA Context Memory Storage Platform. Source: NVIDIA CES 2026*

![](https://substackcdn.com/image/fetch/$s_!dd72!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd1e305db-6eb6-4ac4-af46-c11eb9b67b29_2506x1673.jpeg)

*Bluefield-4 Package Rendering. Source: NVIDIA, SemiAnalysis Estimates*

CPUs are now featuring more in the networking stack. While previous SmartNICs and Data Processing Units (DPUs) added some ARM cores to the Ethernet controllers to perform in-network offloads and accelerations, NVIDIA takes this to the next level with their latest DPU. They are now co-packaging an entire Grace CPU alongside a ConnectX-9 chip for the Bluefield-4 DPU, used in each Rubin compute tray for the frontend NIC as well as putting four BF4s in their Context Memory Storage Platform for KV-Cache offload to high-speed NAND.

The huge computational power of the 64 enabled Grace cores backed up by 128GB of LPDDR5 memory shows the CPU’s increasing involvement in data management for AI. Model KV-Cache offload and storage represents a third network being added to the current AI network topology of East-West (Scale-out GPU cluster scaling) and North-South (connection to storage, external resources and the Internet). With Bluefield-4, the line between a NIC with CPU compute and a CPU with networking acceleration (such as Xeon 6 SoC Granite Rapids-D) blurs even more.
