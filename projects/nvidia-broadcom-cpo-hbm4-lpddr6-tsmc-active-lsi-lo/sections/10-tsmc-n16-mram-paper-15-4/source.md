TSMC presented an updated STT-MRAM on their N16 node, building on their previous work from ISSCC 2023. TSMC is positioning the MRAM as an embedded non-volatile memory (eNVM), for use in automotive, industrial, and edge applications, which do not need the most advanced technology but instead reliability.

![](https://substackcdn.com/image/fetch/$s_!AEKe!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb74d1b16-3ff4-4bca-8df1-6e8909f865d1_2880x1620.png)

*TSMC N16 MRAM Design Features and Die Floorplan. Source: TSMC, ISSCC 2026*

The MRAM features dual-port access so reads and writes can occur simultaneously — critical for over-the-air (OTA) updates in automotive, where the system cannot halt reads while firmware is being written.

![](https://substackcdn.com/image/fetch/$s_!mICA!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2bb08e47-26dd-4357-b813-60ec053c33d4_2880x1620.png)

*TSMC N16 MRAM Shmoo Plot at -40 °C and 150 °C. Source: TSMC, ISSCC 2026*

It features interleaved reads across modules with independent clocks, raising throughput to 51.2 Gb/s at 200 MHz. On silicon, the 84 Mb macro achieves 7.5ns read access time at 0.8V across -40 °C to 150 °C.

![](https://substackcdn.com/image/fetch/$s_!qUbb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9ac17a55-6e1f-415f-bebb-b5dd0c966ea9_2880x1620.png)

*TSMC N16 MRAM Modular Macro Architecture. Source: TSMC, ISSCC 2026*

The architecture is modular — configurable in 16 Mb, 8 Mb and 2 Mb modules that compose into macros from 8 Mb to 128 Mb. By combining large 16 Mb modules with a few smaller 2 Mb and 8 Mb modules, the capacity can be fine tuned to the needs of any design. For example, 5× 16 Mb modules and 2× 2 Mb modules form an 84 Mb macro.

![](https://substackcdn.com/image/fetch/$s_!yxjs!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbe9063a9-d2b4-4d04-9dfd-ebf11aac4259_2880x1620.png)

*TSMC N16 MRAM Endurance and Reliability. Source: TSMC, ISSCC 2026*

As stated earlier, reliability is where embedded MRAM lives or dies. After 1 million endurance cycles at -40 °C, the hard error rate stays well below 0.01 ppm — well within ECC correction range. Read disturb at 150 °C is below 10⁻²² ppm at typical read voltages, effectively negligible. The 168 Mb test chip passes reflow and supports 20-year retention at 150 °C, meeting stringent automotive requirements.

![](https://substackcdn.com/image/fetch/$s_!hLrV!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0ef20058-3a8c-4df0-85e1-5912e2da26ff_2880x1620.png)

*TSMC N16 MRAM Specification vs Prior Work. Source: TSMC, ISSCC 2026*

Compared to the old MRAM on the same N16 node, the bitcell has shrunk 25% from 0.033 µm² to 0.0249 µm², and macro density increases to 16.0 Mb/mm² iso-capacity. The read speed drops from 6 ns to 5.5 ns iso-capacity, and the dual-port access and interleaved reads are entirely new.

While Samsung Foundry also published work on 8LPP eMRAM this year, TSMC’s is far more promising. It targets the needed features, has great performance, and is on a cheaper N16 node.

![](https://substackcdn.com/image/fetch/$s_!09sO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F87ac2737-caab-46a2-8b88-417507719b1a_2880x1620.png)

*TSMC N16 MRAM Flash-Plus Roadmap. Source: TSMC, ISSCC 2026*

TSMC is already planning the next-generation “Flash-Plus” variant with a 25% smaller bitcell and 100× higher endurance.
