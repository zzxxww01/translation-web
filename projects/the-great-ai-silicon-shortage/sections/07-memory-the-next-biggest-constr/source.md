The [global memory shortage](https://newsletter.semianalysis.com/p/memory-mania-how-a-once-in-four-decades) is unlikely to ease in the near term. Memory has emerged as the next major battleground, as chip vendors and hyperscalers race to secure DRAM supply for accelerator production. While total DRAM wafer capacity continues to grow, most incremental capacity is being absorbed by HBM, effectively crowding out commodity DRAM.

On a wafer-per-bit basis, HBM consumes roughly three times more wafer capacity than commodity DRAM, a gap that could widen to nearly four times as the industry transitions to HBM4 this year and even larger in HBM4E next year. As a result, incremental HBM growth diverts a disproportionate share of DRAM wafer capacity away from commodity DRAM, reinforcing structurally tight memory conditions.

![](https://substackcdn.com/image/fetch/$s_!3wRG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe3edd595-4b9d-4d67-8da2-ee97a6f6e053_2136x1126.png)

Source: [SemiAnalysis Memory Model](https://semianalysis.com/memory-model/)

![](https://substackcdn.com/image/fetch/$s_!3eWl!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faab0bd24-a53a-4e2a-a0ea-7daa0057e0f8_2004x1094.png)

Source: [SemiAnalysis Memory Model](https://semianalysis.com/memory-model/)

This pressure is being amplified by rapid increases in HBM content per accelerator. HBM bit shipments are inflecting sharply, driven primarily by rising memory capacity per device rather than unit growth alone. For NVIDIA, the move from Blackwell to Blackwell Ultra and Rubin increases HBM capacity by 50%, with Rubin Ultra driving a further ~4×increase. Similar step-ups are occurring across hyperscaler ASICs, with TPU v8AX and Trainium3 also migrating to 12-Hi stacks from 8-Hi in their previous generation, while AMD’s memory capacity increases by 50% from MI350 to MI400.

![](https://substackcdn.com/image/fetch/$s_!vlh2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F17bae206-924e-4e87-a7f1-c91a3f257c9e_2098x1130.png)

Source: [SemiAnalysis Accelerator Model](https://semianalysis.com/accelerator-hbm-model/)

Another tightening dynamic is the push toward higher HBM pin speeds. Customers such as NVIDIA are targeting approximately 11 Gb/s pin speeds for HBM4, a requirement that remains difficult for memory vendors to achieve at acceptable yields. While SK Hynix and Samsung are making better progress toward meeting these specifications, Micron is lagging behind in HBM4, a dynamic we discussed in our [Rubin article](https://newsletter.semianalysis.com/p/vera-rubin-extreme-co-design-an-evolution) and within the [Accelerator & HBM Model](https://semianalysis.com/accelerator-hbm-model/) as early as January. This escalation in performance requirements, as customers demand higher pin speeds and vendors struggle to deliver at scale, further constrains effective HBM supply.

![](https://substackcdn.com/image/fetch/$s_!nRle!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5c55d753-0c40-4c17-83f1-e3d2063f7cfc_2134x1226.png)

Source: [SemiAnalysis Memory Model](https://semianalysis.com/memory-model/)

Beyond HBM, server DRAM demand is also strengthening. AI server system memory will increase materially in NVIDIA’s next-generation platforms, with VR NVL72 racks carrying 3× higher DDR content, at 1,536 GB per Vera CPU versus 512 GB per Grace. We also expect general DRAM bit demand to inflect higher in 2026, as an aging cloud and enterprise server installed base enters a multi-year replacement cycle. At the same time, AI workloads, particularly data staging, orchestration, and reinforcement learning, are [driving CPU demand](https://newsletter.semianalysis.com/p/cpus-are-back-the-datacenter-cpu), gradually increasing CPU-to-GPU ratios over time.

Across the DRAM market, accelerating deployment of AI and general-purpose servers and rising DRAM content per system is expected to drive server DRAM demand higher over time. This demand should more than offset softness in smartphones, PCs, and consumer electronics over the next two years as memory prices rise.

![](https://substackcdn.com/image/fetch/$s_!2Opv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4f090096-02d5-4aaf-b7b2-d0233652675f_2002x1180.png)

Source: [SemiAnalysis Memory Model](https://semianalysis.com/memory-model/)

If logic capacity is freed up for accelerators, customers will quickly need to turn their attention to securing more HBM from memory suppliers. With conventional DDR DRAM prices skyrocketing, DDR margins have surged close to or even surpassing levels at which HBM supply has been contracted. In the past, the superior margin profile offered by HBM gave memory suppliers a clear reason to expand HBM wafer capacity. However, this is no longer the case as margin dynamics have reversed, at least for 2026.

To incentivize more HBM wafer starts vs commodity wafers, customers would likely need to pay higher prices than current contracted levels to secure incremental HBM supply. This dynamic is likely to become more visible in 2027, when the next round of HBM pricing negotiations is settled. If the memory suppliers relent and shift capacity towards HBM, the available bit supply for conventional DDR DRAM would tighten even further.

Another key implication is the reallocation of bits from consumer applications to server and HBM, a dynamic we have been highlighting since 2H25. In our latest analysis in Memory Model, we highlight the impact of consumer shock on potential bit reallocation. In an extreme scenario where there is a 50% cut in consumer unit shipments, approximately 55,390 million Gb would be released, equivalent to roughly 14% of total DRAM demand in 2026. Under a 25% cut scenario, around 27,690 million Gb would be freed up, representing about 7% of total DRAM demand and nearly 80% of this year’s HBM demand.

![](https://substackcdn.com/image/fetch/$s_!qN_X!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffd82a56a-592f-48d7-8269-232c73920309_2379x504.png)

Source: [SemiAnalysis Memory Model](https://semianalysis.com/memory-model/)

Our base case remains a more moderate 10-15% decline in consumer shipments. Under a 10% shipment cut, approximately 11,076 million Gb would be released, representing only ~3% of total DRAM demand. In our view, this level of incremental supply is not sufficient to materially alter the overall supply-demand dynamics we expect to see this year.

The key question is how prepared memory suppliers are for consumer weakness, and to what extent they have already adjusted. We believe memory makers have a solid understanding of softness across consumer end markets. Samsung management, for example, has highlighted consumer weakness on multiple occasions, and we believe capacity allocation plans already incorporate a 10-15% downside shipment scenario. We expect other major memory suppliers to be similarly positioned.
