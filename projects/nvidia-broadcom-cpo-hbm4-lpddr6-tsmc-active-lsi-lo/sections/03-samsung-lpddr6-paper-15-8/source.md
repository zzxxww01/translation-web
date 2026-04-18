Both Samsung and SK Hynix showed off their LPDDR6 chips. We will discuss Samsung’s chips first and turn to SK Hynix’s later.

![](https://substackcdn.com/image/fetch/$s_!Odn_!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb15266c9-bc1e-4365-9316-28d2a6e36fac_2880x1620.jpeg)

*LPDDR5X vs. LPDDR6 Comparison. Source: Samsung, ISSCC 2026*

Samsung presented their LPDDR6 architecture and detailed the power-saving techniques used.

![](https://substackcdn.com/image/fetch/$s_!Ysn8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0098a613-71de-4d6c-b446-2a203e66fef7_2880x1620.jpeg)

*LPDDR6 Sub-Channel and Bank Structure. Source: Samsung, ISSCC 2026*

LPDDR6 adopts a 2 sub-channel per die architecture, with 16 banks in each sub-channel. It also features two modes: a normal mode and an efficiency mode. In the efficiency mode, the secondary sub-channel is powered down, and the primary sub-channel controls all 32 banks. However, there is a latency penalty for accessing data in the secondary sub-channel.

The dual sub-channel architecture also means that there is twice the amount of peripheral circuitry, such as command decoders, serialization and control. From the die shots provided by both Samsung and SK Hynix, the penalty is about 5% of the total die area, leading to a reduction in total bits per wafer.

![](https://substackcdn.com/image/fetch/$s_!79tH!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F68f2f392-7912-4f69-9c53-ef6c4f6942b6_2880x1620.jpeg)

*LPDDR6 Signaling Options. Source: Samsung, ISSCC 2026*

Unlike GDDR7, which uses PAM3 signaling, LPDDR6 will continue to use NRZ. However, it does not use standard NRZ as the eye would not have sufficient margin. It uses wide NRZ with 12 data (DQ) pins per sub-channel and a burst length of 24 per operation.

![](https://substackcdn.com/image/fetch/$s_!GQm1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1737c518-8a4f-4042-a536-513a9f769cb8_2880x1620.jpeg)

*LPDDR6 Metadata and DBI Bit Allocation per Burst. Source: Samsung, ISSCC 2026*

For those of you doing the math, 12×24 is 288, not a power of two. The remaining 32 bits are split into 2 use cases, 16 for metadata like ECC, and 16 for Data Bus Inversion (DBI).

DBI is a power-saving and signal integrity mechanism. Before a burst is sent out, the controller checks if more than half the bits would switch state compared to the previous burst. If so, the controller inverts all the bits and sets a DBI flag, so that the receiver knows to invert them to get the actual data. This limits the maximum number of simultaneous switching outputs to half the bus width, reducing power consumption and supply noise.

To calculate the effective bandwidth, you must account for these metadata and DBI bits like so: Bandwidth = Data Rate × Width (24 b) × Data (32 b) / Packet (36 b). For 12.8 Gb/s, you get 34.1 GB/s, and for 14.4 Gb/s, you get 38.4 GB/s.

![](https://substackcdn.com/image/fetch/$s_!bjV0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F986010c2-7d39-4d5f-b195-76d6c653c5ea_2880x1620.jpeg)

*Samsung LPDDR6 High-Frequency Power Domain Optimization. Source: Samsung, ISSCC 2026*

LPDDR6 has two constant power domains, VDD2C at 0.875V and VDD2D at 1.0V. By carefully choosing which peripheral logic is using which power domain, read power has been reduced by 27% and write power reduced by 22%.

![](https://substackcdn.com/image/fetch/$s_!QJ_x!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8741b331-6528-4e4f-a064-722f271f43a0_2880x1620.jpeg)

*Samsung LPDDR6 I/O Power Switching at Low Data Rates. Source: Samsung, ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!iMMC!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F06109578-4db8-490e-b963-1968a2ebacb0_2880x1620.jpeg)

*Samsung LPDDR6 Additional Low-Power DQ/CA Paths. Source: Samsung, ISSCC 2026*

LPDDR is primarily used at low data rates of 3.2 Gb/s and below when idling. Samsung focused heavily on saving power at these lower data rates through careful use of the voltage domains, reducing both standby and read/write power consumption.

![](https://substackcdn.com/image/fetch/$s_!Tycr!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F931c917e-8cf5-4e59-9b07-45faa91aeee0_2880x1620.jpeg)

*LPDDR6 RDL Timing and Layout Benefits. Source: Samsung, ISSCC 2026*

By using a redistribution layer (RDL), Samsung can locate related circuits closer together physically. This shortens critical delay paths and reduces their sensitivity to voltage and temperature variation. At the high frequencies of LPDDR6, tighter timing and reduced variation are essential.

![](https://substackcdn.com/image/fetch/$s_!UXaU!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F295c4906-10e2-4877-909b-d7c76e61a6f4_2880x1620.jpeg)

*Samsung LPDDR6 Specifications and Die Shot. Source: Samsung, ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!003E!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6c037b47-34b6-41db-b615-2e62e41bba05_2880x1620.jpeg)

*Samsung LPDDR6 Shmoo Plot. Source: Samsung, ISSCC 2026*

Samsung’s LPDDR6 can reach a data rate of 12.8 Gb/s at 0.97V, and up to 14.4 Gb/s at 1.025V. Each 16 Gb die is 44.5 mm², with a density of 0.360 Gb/mm² on an unknown 10nm-class process. This is considerably lower than the density of LPDDR5X on 1b at 0.447 Gb/mm² and only slightly higher than the density of LPDDR5X on 1a at 0.341 Gb/mm². While the area penalty from the dual sub-channel architecture does partially contribute, there seem to be other problems with the LPDDR6 as well. The memory density described leads us to believe that this prototype LPDDR6 chip was manufactured on their 1b process.
