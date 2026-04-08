![](https://substackcdn.com/image/fetch/$s_!2wN-!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fae88cb59-dfc9-4ef0-82db-daeb13090a11_2774x1467.png)

*AmpereOne 2024 Roadmap. Source: Ampere Computing*

![](https://substackcdn.com/image/fetch/$s_!tg4g!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9bd4b346-265c-417c-8de2-3bb02f84db2d_2618x1683.png)

*Ampere Altra Max (Left) and Altra (Right). Source: Ampere Computing*

![](https://substackcdn.com/image/fetch/$s_!67XG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F14200e92-bb26-47b1-89d4-c52dc20cccd8_1500x1852.png)

*Delidded AmpereOne CPU. Source: Brendan Crain, Wikimedia*

![](https://substackcdn.com/image/fetch/$s_!DWkM!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9c471082-f099-457c-bc01-5aa2deb081cb_2923x1573.png)

*AmpereOne Mesh Architecture. Source: Ampere Computing, Hot Chips 2024*

Ampere Computing was the original champion for merchant ARM silicon, competing directly with AMD and Intel as a 3rd silicon provider for OEM server builds. With a strong partnership with Oracle, Ampere delivered their 80-core Altra and 128-core Altra Max line of CPUs with great fanfare, promising to disrupt the x86 CPU duopoly with cost effective ARM CPUs. Ampere Altra employed the Neoverse N1 core with their own mesh interconnect with cores grouped into 4-core clusters. Accompanying the cores are 8-channels of DDR4 and 128 PCIe4 lanes on a single TSMC 7nm die.

The next generation AmpereOne CPUs brought core counts up to 192, thanks to a move to a 5nm process and a novel chiplet design that disaggregates the IO into separate DDR5 and PCIe dies in an MCM configuration that does not require use of an interposer. Ampere also moved to a custom ARM core, designed for core density rather than outright performance, paired with an oversized 2MB L2 cache to minimize performance penalties from noisy neighbors where other VMs running on adjacent cores hog traffic on the shared mesh interconnect. A similar 4-core cluster is implemented on a 9x8 mesh network. In total, integer performance was doubled over Altra Max.

The chiplet design allows the same compute die to be reused in other variants, with the 12-channel AmpereOne-M adding 2 more memory controller dies. The future AmpereOne-MX reuses the same I/O chiplets but swaps in a 3nm compute die with 256 cores. Their 2024 roadmap also detailed a future AmpereOne Aurora chip with 512 cores and AI Training and Inference capabilities.

However, this roadmap is no longer valid once Ampere Computing was acquired by SoftBank in 2025 for $6.5 Billion. While true that Masayoshi Son wanted Ampere’s CPU design talent to shore up their CPU designs for the Stargate venture, the acquisition was also spurred by Oracle wanting to divest itself from a poorly performing business. Ampere’s CPUs never ramped into significantly high enough volumes due to timing and execution issues.

The Altra generation was their first major market entry, but arrived too early for mass adoption as most software was not ARM-native at the time. Unlike hyperscalers who could quickly adapt their internal workloads for their own ARM silicon, the general purpose and enterprise CPU markets are much slower to move. Following that, the AmpereOne generation faced many delays, with Oracle Cloud A2 and CPU availability arriving in the second half of 2024. By then, the hyperscaler ARM CPU projects are in full swing, and AMD could match Ampere’s 192 cores but with 3-4 times higher per core performance. Despite Oracle promoting Ampere instances with halved per-core licensing costs, the CPUs were not popular enough, and the order book dried up. Oracle never used up their full pre-payment for Ampere CPUs, with their Ampere CPU purchases dwindling from $48M in fiscal 2023 to $3M in 2024 and $3.7M in 2025.

Ampere is now working on AI chips as well as CPUs under the Softbank umbrella.
