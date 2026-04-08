The [VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/) provides a detailed analysis on the BoM and the Power Budget of the rack system.

![](https://substackcdn.com/image/fetch/$s_!79G7!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7a435ee7-a40f-4df2-a84a-9d37041115d5_3379x755.png)

Source: [VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

The VR NVL72 is more expensive on a per-GPU capital cost basis, ~45% higher vs GB300s and ~14-15% higher vs the MI4XX given a higher server cost on a per GPU basis. This results in a higher Capital Cost of Ownership (TCO). For example VR NVL 72 Hyperscaler Arista has a capital cost of $3.28 to MI4XX Hyperscaler of $2.86 per hour per GPU over a 4 year useful life. Our TCO Model runs on a 4y useful life for the purpose of calculating capital cost per hour to reflect a conservative business case, but most Neoclouds and Hyperscalers will use a 5-6y depreciation period and we think it is best to look at EBIT margins using this depreciation period. Our preferred yardstick is Project IRR, which is agnostic to the chosen depreciation period.

However, one advantage for Nvidia’s VR SOCAMM option is that NVIDIA directly procures memory, allowing them to negotiate long-term agreements, volume-preferential terms with memory suppliers and most importantly, VVIP pricing. We think this will shield end customers from spikes in memory costs as we outline in our [AI server apocalypse note](https://semianalysis.com/institutional/the-ai-server-pricing-apocalypse/?access_token=eyJhbGciOiJFUzI1NiIsImtpZCI6InNlbWlhbmFseXNpcy5wYXNzcG9ydC5vbmxpbmUiLCJ0eXAiOiJKV1QifQ.eyJhdWQiOiJzZW1pYW5hbHlzaXMucGFzc3BvcnQub25saW5lIiwiYXpwIjoiS1NncVhBaGFmZmtwVjQzbmt0UU1INSIsImVudCI6eyJ1cmkiOlsiaHR0cHM6Ly9zZW1pYW5hbHlzaXMuY29tL2luc3RpdHV0aW9uYWwvdGhlLWFpLXNlcnZlci1wcmljaW5nLWFwb2NhbHlwc2UvIl19LCJleHAiOjE3NzIyMjcwMTcsImlhdCI6MTc2OTYzNTAxNywiaXNzIjoiaHR0cHM6Ly9zZW1pYW5hbHlzaXMucGFzc3BvcnQub25saW5lL29hdXRoIiwic2NvcGUiOiJmZWVkOnJlYWQgYXJ0aWNsZTpyZWFkIGFzc2V0OnJlYWQgY2F0ZWdvcnk6cmVhZCBlbnRpdGxlbWVudHMiLCJzdWIiOiIwMTk4OTQ2ZC0xNWUwLTc4MGItYWE2My1iNTc2YmQ3YWY2OTIiLCJ1c2UiOiJhY2Nlc3MifQ.2-BzgpJsNkRro7XCzTy3QDFtE-QyqEQxE7kykja0HIN5XHg3O1bvBzRuBc5x1Pz_HfCVhuRT3fA8f1s7GI_CvA), and is another example of how, [as the Central Bank of AI](https://semianalysis.com/institutional/nvidia-as-the-central-bank-of-ai/), Nvidia is effectively hedging DRAM prices for all of its customers.

By contrast, AMD is much more exposed to DRAM price increases as it has about double the amount of DRAM, with about 55 TB per rack of LPDDR5 and 55 TB per rack of DDR5. For the AMD’s Helios rack scale system, AMD sells the GPU/board and does procure the LPDDR5 memory, but it does not procure DDR5 DRAM for rack compute trays; rack assemblers/ODMs source and integrate DDR5 memory. This leaves buyers of AMD’s racks more exposed because AMD is only able to potentially “hedge” the LPDDR5 portion via long-term contracts leaving the DDR5 portion completely exposed. Having double the DRAM content also nearly doubles the overall exposure.

Helios memory costs are more likely to be passed through or re-priced by assemblers and therefore exhibit greater hikes in a memory upcycle. Therefore, we model lower memory price hikes for VR and GB compared to MI4XX below. Our MI400 rack assumptions reflect $8.70/GB LPDDR pricing for AMD versus $6.77/GB for Nvidia, embedding volume discount structures vs the market contract price of $10.63/GB but reflecting the slack of volume economics vs NVIDIA.

Our [AI Memory Model](https://semianalysis.com/memory-model/) expects significant increases in LPDDR5 and DDR5 contract prices into 2Q26 and beyond and we expect to make further revisions higher in total server capex.

NVIDIA’s 2300W configuration represents the Max-P configuration, while the efficiency optimized Max-Q configuration runs at 1800W. Regardless of which configuration Nvidia claims both can hit the same peak clocks and therefore achieve marketed 50 PFLOPS FP4 performance. While the underlying hardware is the same, the TCO implications are due to operating costs from different levels of power consumption.

Below we share detailed numbers on cost of servers, storage, networking, etc as well as what Nvidia plans to do with Groq.

![](https://substackcdn.com/image/fetch/$s_!WlUw!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9cef854e-8f7c-4f45-bd8a-a17c095ea191_3034x1194.png)

Source: [SemiAnalysis AI TCO Model](https://semianalysis.com/ai-cloud-tco-model/)

![](https://substackcdn.com/image/fetch/$s_!TZYu!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F67acd953-f548-45ed-94cd-93728716d2dd_3212x1126.png)

Source: [SemiAnalysis AI TCO Model](https://semianalysis.com/ai-cloud-tco-model/)

Operating costs are similar for VR Max-P vs MI4XX given their comparable chip TDPs and given that most operating costs scale with respect to IT power requirements.

VR Max-Q on the other hand, exhibits lower Operating costs relative to MI4XX given the lower chip TDP. For example a VR NVL 72 cluster deployed at a Hyperscaler with Arista networking would have a operating cost of $0.75 per gpu per hour, representing ~20% lower costs vs MI4XX deployed with a Hyperscaler with the same Arista networking. This highlights the advantages of the Max-Q configuration, particularly from an operating cost perspective, as the lower power TDP reduces rack-level power density for a meaningful cost savings over time.

![](https://substackcdn.com/image/fetch/$s_!8ntQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa1735f7d-dafc-4ef1-87bb-b079122d1880_3048x1164.png)

Source: [SemiAnalysis AI TCO Model](https://semianalysis.com/ai-cloud-tco-model/)

![](https://substackcdn.com/image/fetch/$s_!NWHY!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9763a7ed-6c8f-49a1-af11-8d34b6244424_3214x1080.png)

Source: [SemiAnalysis AI TCO Model](https://semianalysis.com/ai-cloud-tco-model/)

The MI4XX currently has a performance per TCO advantage based on marketed dense FLOPS over VR. VR has a higher TCO per GPU compared to MI4XX, yet VR marketed PFLOPs are lower vs MI4XX resulting in a TCO per PFLOP disadvantage for the VR vs MI4XX.

NVIDIA is offering sparsity for FP4, marketing 50 PFLOPS of FP4, while AMD has opsted to remove sparsity support since CDNA4 for inference dtypes. Harnessing the 50 PFLOPS sparse vs 35 PFLOPS dense drops the cost per perf in units of $/hr per Marketed PFLOP by 35% – a valid comparison if AI Labs can indeed successfully harness Sparse FP4 on the VR NVL72.

As always, one caveat is that this comparison is done based on a marketed dense PFLOP basis. Effective dense PFLOP (i.e. the real world chip throughput) can differ based on Model Flops Utilization % (MFU), and in general we have seen NVIDIA chip operate at a higher MFU % vs AMD chips, suggesting that performance per TCO based on effective dense PFLOPs could be better for NVIDIA systems vs AMD – however, MFU is dependent on actual workloads with no one-size-fits-all MFU % that is consistently applicable to either systems.

Indeed, real world use of FP4 Sparsity will probably not reach 50 PFLOPS but it will probably deliver better effective FLOPs than FP4 Dense, but we have yet to evaluate what that real-world performance could be. Running VR NVL72 on 1800W would probably mean lower FP4 Sparse FLOPs than on 2300W.

![](https://substackcdn.com/image/fetch/$s_!js3P!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff3423fa8-92cd-4d15-8e8e-a205bff85e4d_1123x513.png)

Source: [SemiAnalysis AI TCO Model](https://semianalysis.com/ai-cloud-tco-model/)

![](https://substackcdn.com/image/fetch/$s_!39Xv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc85a7bc2-9a3c-4b70-b9e5-6e3ef0424ee0_1374x572.png)

Source: [SemiAnalysis AI TCO Model](https://semianalysis.com/ai-cloud-tco-model/)

Inference throughput too can diverge materially from marketed peak FLOPS, meaning spec-sheet compute does not directly translate into real-world token generation performance. While the B300 is rated at 4,500 Dense FP8 TFLOPs versus 5,000 Dense FP8 TFLOPs for MI355, implying a 10% theoretical compute disadvantage and with same marketed memory bandwidth of 8TB/s measured inference token throughput from our [InferenceX](https://inferencex.semianalysis.com/) benchmarks shows B300 delivering roughly 6.3x the performance at 100 interactivity for Deepseek R1, using 8k input tokens and 1k output tokens.

Given that total cost of ownership is only 1.75x higher, this results in a superior performance-per-TCO profile for B300 despite the more modest marketed figures. Such a wildly different result despite very similar specs underscores that real world performance is not dictated by peak FLOPS or memory bandwidth alone. Software and network capabilities are also major factors that contribute to training and token throughput in real workloads.

Rubin and MI4XX will ship with new microarchitectures, real world performance is especially difficult to predict without and benchmarking like we do with InferenceX.

Notably, both operating modes share identical memory bandwidth specifications at 8TB/s. Yet, despite the parity in memory bandwidth inference performance still diverges materially.

![](https://substackcdn.com/image/fetch/$s_!0kLF!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F61dc18ea-4e59-48f6-bf35-b938b7d0671d_2484x1424.png)

Source: [SemiAnalysis InferenceX](https://inferencex.semianalysis.com/)
