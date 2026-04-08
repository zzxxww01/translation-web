### RL and Agent Usage, Context Memory Storage, DRAM Pricing Impacts, CPU Interconnect Evolution, AMD Venice, Verano, Florence, Intel Diamond Rapids, Coral Rapids, Arm Phoenix + Venom, Graviton 5, Axion

By [Gerald Wong](https://substack.com/@geraldwong116502) and [Dylan Patel](https://substack.com/@semianalysis)

Feb 09, 2026 · Paid

![](https://substackcdn.com/image/fetch/$s_!Qsru!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3f9507d8-140b-4db8-9fd6-2ac28050a1ea_2016x1344.png)

Since 2023, the datacenter story has been simple. GPUs and networking are king. The arrival and subsequent explosion of AI Training and Inference have shifted compute demands away from the CPU. This meant that Intel, the primary supplier of server CPUs, failed to ride the wave of datacenter buildout and spending. Server CPU revenue remained relatively stagnant as hyperscalers and neoclouds focused on GPUs and datacenter infrastructure.

At the same time, the same hyperscalers have been rolling their own ARM-based datacenter CPUs for their cloud computing services, closing off a significant addressable market for Intel. And within their own x86 turf, Intel’s lackluster execution and uncompetitive performance to rival AMD has further eroded market share. Without a competent AI accelerator offering, Intel was left to tread water while the rest of the industry feasted.

Over the last 6 months this has changed massively. We have posted multiple reports to [Core Research](https://semianalysis.com/core-research/) and the [Tokenomics Model](https://semianalysis.com/tokenomics-model/) about soaring CPU demand. The primary drivers we have shown and modeled are reinforcement learning and vibe coding’s incredible demand on CPUs. We have also covered major CPU cloud deals by multiple vendors with AI labs. We also have modeling of how many CPUs of what types are being deployed.

![](https://substackcdn.com/image/fetch/$s_!5yS5!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9c9e56be-fcab-4b4a-9a66-0ead1858e8d9_1648x1629.png)

*Intel Q4’25 DCAI Revenue. Source: Intel*

However, Intel’s recent rallies and changing demand signals in the latter part of 2025 have shown that CPUs are now relevant again. In their latest Q4 earnings, Intel saw an unexpected uptick in datacenter CPU demand in late 2025 and are increasing 2026 capex guidance on foundry tools and prioritizing wafers to server from PC to alleviate supply constraints in serving this new demand. This marks an inflection point in the role of CPUs in the datacenter, with AI model training and inference using CPUs more intensively.

![](https://substackcdn.com/image/fetch/$s_!AFjW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F066448fc-f72e-4159-aa67-e0192e2ff2ea_3023x1461.png)

*Datacenter CPU Core Count Trend. Source: SemiAnalysis Estimates*

2026 is an exciting year for the datacenter CPU, with many new generations launching this year from all vendors amid the boom in demand. As such, this piece serves to paint the CPU landscape in 2026. We lay the groundwork, covering the history of the datacenter CPU and the evolving demand drivers, with deep dives on datacenter CPU architecture changes from Intel and AMD over the years.

We then focus on the 2026 CPUs, with comprehensive breakdowns on Intel’s Clearwater Forest, Diamond Rapids and AMD’s Venice and their interesting convergence (and divergence) in design, discussing the performance differences and previewing our CPU costing analysis.

Next, we detail the ARM competition, including NVIDIA’s Grace and Vera, Amazon’s Graviton line, Microsoft’s Cobalt, Google’s Axion CPU lines, Ampere Computing’s merchant ARM silicon bid and their acquisition by Softbank, ARM’s own Phoenix CPU design and look at Huawei’s home grown Kunpeng CPU efforts.

For our subscribers, we provide our datacenter CPU roadmap to 2028 and detail the datacenter CPUs beyond 2026 from AMD, Intel, ARM and Qualcomm. We then look ahead to what the future looks like for datacenter CPUs, discuss the effects of the DRAM shortage, what NVIDIA’s Bluefield-4 Context Memory Storage platform means for the future of general purpose CPUs, and the key trends to look out for in the CPU market and CPU designs going forward.
