One of, if not the, biggest constraints is TSMC’s N3 logic wafer capacity. TSMC’s N3 family started shipping for revenue in 2023, with demand initially driven primarily by smartphones and PCs. [N3 got off to a shaky start, with the first variant “N3B” having yield issues and being too expensive relative to the density improvement.](https://newsletter.semianalysis.com/i/175660907/tsmc-3nm-fab-costs) Greater adoption came with the refined N3E process, a relaxed variant with far fewer EUV layers and therefore lower cost. Key smartphone and PC customers include Apple, which uses N3 variants for its M3 to M5 Mac chips and A17 to A19 iPhone processors, Qualcomm for its Snapdragon 8 Elite series, MediaTek for its Dimensity smartphone SoCs as well as select automotive and PC chips, and Intel for its Lunar Lake and Arrow Lake client processors.

![](https://substackcdn.com/image/fetch/$s_!lpP7!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbe6a510f-f4ee-4ee8-9267-22ccd427f99c_1860x1038.png)

Source: [SemiAnalysis Foundry Model](https://semianalysis.com/foundry-industry-model/)

Up until today, N3 demand has been driven primarily by consumer electronics. In 2026, all the main AI accelerator families are transitioning to N3, and AI will account for the majority of N3 demand before transitioning to N2 and beyond.

We can see in the table below the industry-wide convergence toward TSMC’s N3 family as the leading process node for AI accelerators heading into 2026. NVIDIA transitions from 4NP with Blackwell to 3NP with Rubin. AMD, typically the earlier adopter of new nodes, has already adopted N3 for MI350X and will stay on N3 for the AID and MID tiles for MI400 (XCD is N2). Google’s TPU roadmap shifts fully to N3E starting with TPU v7, with TPU seeing a huge upsize in program volumes this year. AWS also transitions to N3P with Trainium3. Meta’s MTIA follows a similar path, though it will be at much lower volumes.

![](https://substackcdn.com/image/fetch/$s_!F7JO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0129d5ef-d8c3-46a8-a8f5-e69d5e4a84b5_1896x1180.png)

Source: [SemiAnalysis Accelerator Model](https://semianalysis.com/accelerator-hbm-model/)

This shift is not limited to XPU silicon. The Vera CPU used in VR racks uses N3P for all its silicon. There is also networking silicon in the form of the NVLink 6 switch, as well as scale out switches like Tomahawk 6 and Spectrum 6. With Rubin offering 1.6T of scale out network per GPU, Rubin kicks off the adoption of 3nm 200G optical DSPs.

This sudden convergence of N3 adoption coupled with the continued growth of AI compute demand has resulted in a huge demand shock for N3 wafer capacity. TSMC has been caught flat-footed, with wafer capacity expansion failing to keep pace with surging AI demand. How did this happen? Although the greatest compute buildout in history began in late 2022, TSMC’s capex only exceeded its previous peak in 2025. This year, TSMC is going to smash through last year’s record Capex, because they have realized how far customer demand is exceeding their capacity.

![](https://substackcdn.com/image/fetch/$s_!siy0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6fd015f7-6e9e-4a42-b5c9-2c359d65dd59_1424x742.png)

Source: Company Filings

While TSMC maintains a clear technology lead over its only competitors, Intel and Samsung, that advantage matters less if customers cannot secure sufficient wafer supply to support their businesses. Capacity constraints may therefore push customers to explore greater foundry diversification. Intel, for example, has the administration’s backing and any outsourcing towards Intel Foundry will earn brownie points from the US government. Meanwhile, momentum is beginning to build at Samsung Foundry as well, with some recent design wins. First off, Samsung has secured some Tesla chip programs, such as AI5 and AI6, although they are dual-tracked with TSMC. [Samsung Foundry has also entered Nvidia’s Datacenter supply chain](https://semianalysis.com/institutional/samsung-foundry-finds-its-way-into-nvidias-ai-supply-chain/), a development we discussed in our Foundry Model.
