### The Relentless March of the A-Series and M-Series

The result of this manufacturing dominance is a performance lead that has compounded over a decade. Apple’s ability to move to the next node first allows it to pack more transistors into the same thermal envelope, maintaining a performance-per-watt lead over the x86 ecosystem.

The transistor count growth is linear, but performance per watt is the real metric. The shift to N3E in the A18/M4 generation prioritized cost and yield over pure density scaling (compared to N3B), which explains the relatively modest transistor count jumps compared to previous generations. The Neural Engine has seen the most exponential growth, jumping from 0.6 TOPS in A11 to 35 TOPS in A17/A18, reflecting Apple’s strategic pivot to on-device AI years before the “AI PC” hype cycle began.

![](https://substackcdn.com/image/fetch/$s_!jU4H!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5db79be6-7c20-4af5-bf20-073e6fcdbd56_3234x2067.png)

![](https://substackcdn.com/image/fetch/$s_!IUPy!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F176c3a2f-dde5-4573-a923-db0b5925c877_3270x1031.png)

![](https://substackcdn.com/image/fetch/$s_!Ci1L!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F02d45a1f-87c8-4119-91a9-bedde9bd8070_3322x1110.png)

Since 2013, Apple has consistently shipped industry-first features 12-24 months ahead of competitors.

### Apple Silicon Technical Advantages

Apple’s performance leadership stems from architectural bets made a decade ago. While Intel and Qualcomm chased 5GHz+ clock speeds, Apple pursued ‘wide and slow’, executing more work per cycle at lower frequencies.

### Front-End Architecture: Decode Width Parity

Apple introduced 8-wide decode with A14/M1 in 2020, four years ahead of competitors. But by 2025, the competitors caught up.

![](https://substackcdn.com/image/fetch/$s_!00WK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F488a6e86-3660-419e-933b-dcd1883c81f4_1612x846.png)

Decode width is no longer Apple’s moat. The advantage has shifted to cache hierarchy, vertical integration and extremely efficient smaller E-cores.

### Cache Hierarchy: Where Apple Still Leads

Apple’s philosophy: massive fast L1, large shared L2, and a System-Level Cache (SLC) before DRAM. The SLC allows CPU, GPU, and Neural Engine to share data without hitting slow system memory.

![](https://substackcdn.com/image/fetch/$s_!GAx7!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8af7977b-b9e9-42a2-b60b-6bf8b9bad677_2000x985.png)

Apple’s SLC advantage is 3-4x larger than competitors with full CPU/GPU sharing. AMD’s Strix Halo matches on size but CPU cores cannot access it.

![](https://substackcdn.com/image/fetch/$s_!zTFs!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb09390ab-b7c5-4d9c-97e6-dc7718a72be5_1610x674.png)

Apple and Qualcomm Oryon match on L1 size, latency and cache hierarchy, as the original Nuvia design team was largely poached from Apple. Intel’s L0/L1.5 tier structure adds latency.

### Unified Memory Architecture

Traditional PC architectures have separate memory pools for CPU and GPU, requiring data copies. Apple Silicon uses Unified Memory Architecture: the GPU reads the exact same memory address as the CPU.

This eliminates the “copy penalty” critical for AI workloads. A 20GB LLM loads once. The Neural Engine and GPU access it simultaneously. Qualcomm mobile chips use shared LPDDR5X but lack Apple’s fine-grained coherency. AMD Strix Halo’s MALL is GPU-only.

### Vertical Integration

Apple’s efficiency edge comes from owning the less attractive silicon: custom Power Management ICs and storage controllers enable millisecond-level dynamic voltage and frequency scaling. The chip races to sleep, completing bursts at high power and dropping to near-zero idle faster than x86 competitors.

The iPhone 17 Pro’s vapor chamber was co-designed with A19 Pro’s thermal envelope. Apple knows the exact sustained power budget (5-7W) and designs the chip accordingly. Qualcomm must design for worst-case thermal across Samsung, Xiaomi, and OnePlus implementations.

What’s changed in 2024-2025:

1. Decode parity: Intel, AMD, Qualcomm all reached 8-wide in 2024 2. SLC adoption: Qualcomm added 8MB SLC; Intel added 8MB memory-side cache 3. L1 parity: Qualcomm Oryon matches Apple’s 320KB L1 at similar latency 4. Android benchmarks closing in on iPhone’s 5. Xiaomi’s own XRing chips with extensive vertical integration on design, power, software

Apple’s remaining advantages: larger SLC (32MB vs 8-10MB), true unified memory with full CPU/GPU coherency, and vertical integration enabling thermal co-design. The gap has narrowed, but Apple still holds the efficiency crown.

*Next we’ll dive further into specifics: Apple wafer demand and economics at TSMC, including our forecasts through the end of the decade at the A14 node. We’ll quantify Apple N2 demand and how that affects their need for older nodes - surprisingly, som older nodes are seeing increased demand from Apple. More numbers are shown for demand by chip and you’ll see the change as the company (tried to) diversify beyond the iPhone. We’ll also put numbers on the HPC phenomena as, discussed earlier, Nvidia demand encroaches Apple at the leading edge.*

*And there’s more: packaging economics, what TSMC’s ex-Apple business looks like, Apple’s in-house efforts to replace Broadcom modems, competing efforts to copy Apple’s vertical integration, a look at the trickle down effects in the supply chain beyond TSMC, and what the future of the TSMC + Apple partnership looks like.*
