![](https://substackcdn.com/image/fetch/$s_!vm-p!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa49ab8ae-a31f-4ca0-b522-8bfa4c30a0fc_2671x1489.png)

*AMD Rackscale AI Infrastructure Roadmap. Source: AMD*

AMD’s next generation MI500 AI racks are set to launch in 2027 with a new EPYC Verano CPU, just 1 year after Venice. To our knowledge, the Zen 7 CPU core architecture will not be ready for Verano, as the cores team works on a roughly two-year cadence. We believe Verano will therefore be a variant of Venice, still using Zen 6 cores, and likely with the same 256-core count. The difference with Verano should be a new I/O die on 3nm with PCIe Gen7 support and 200G Ethernet SerDes for a much faster Infinity Fabric connection to the MI500 GPUs. This would support UALoE

A true next generation Zen 7 EPYC, codenamed Florence, should debut in 2028 on TSMC’s A16 process with backside power. Alternatively, if AMD could do without backside power, they could wait for TSMC’s A14 process to be ready for 2029 products. We estimate core count to increase to around 320 or so.

![](https://substackcdn.com/image/fetch/$s_!otrQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe4a3cd7a-72fe-4414-bcf7-9a1ac1d827f2_3111x1740.png)

*AMD Zen CPU Core Roadmap. Source: AMD*

On the core microarchitecture, AMD CTO Mark Papermaster confirmed that Zen7 introduces a new dedicated Matrix Multiplication engine for local AI computation that is known as ACE in the x86 Advisory Group. This is much like the AMX engines Intel added with Sapphire Rapids in 2023. Zen7 also adopts AVX10, the evolution of AVX512 with more features and instruction flexibility with smaller bit widths. A new interrupt model in FRED (Flexible Return and Event Delivery) and ChkTag memory tagging also debut on Zen7. All these features will have debuted earlier on Intel Diamond Rapids. Additionally, Diamond Rapids also support Advanced Performance Extensions (APX), an instruction set extension that adds access to more registers and improves general purpose performance. This does not seem to be present on Zen7.
