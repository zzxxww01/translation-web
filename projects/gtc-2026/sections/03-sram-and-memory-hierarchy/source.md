We have written about the role of SRAM in the memory hierarchy, but the quick recap is that SRAM is very fast (low latency and high bandwidth) but this comes at the expense of density and therefore cost.

SRAM machines such as Groq’s LPU therefore enable very fast time to first token and tokens per second per user but at the expense of total throughput, as their limited SRAM capacity quickly gets saturated by weights, with little left over for KVcache that grows as more users are batched. GPUs win for throughput and cost as we have shown. This is why Nvidia has decided to combine these architectures to get the best of both worlds: accelerate parts of decode that are more latency sensitive and are not as memory heavy on a low-latency SRAM-heavy chip like the LPU, while memory hungry attention is performed on GPUs that come with a lot of fast (but not SRAM fast) memory capacity.

![](https://substackcdn.com/image/fetch/$s_!6Cix!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa939a961-40da-4762-b7d2-1ebb2423e9a2_2188x350.png)

Source: SemiAnalysis

This brings us to the Groq 3 LPU or LP30, with LPU gen 2 being skipped over. This chip has no Nvidia design involvement. The SerDes issues affecting v2 appear to be fixed. Behind the paywall, we will reveal the SerDes IP vendor which may come as a surprise. Nvidia also announced an LP35 which is a minor refresh of the LP30 which will remain on SF4 and will require a new tapeout. It will incorporate NVFP4 number format but given Nvidia is prioritizing time to market we don’t expect any other drastic design changes.

![](https://substackcdn.com/image/fetch/$s_!iPH0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F39025ad5-927c-4619-b929-88d5555be853_1590x860.jpeg)

Source: Nvidia

LPU 3’s near reticle size die layout is very similar to LPU 1. a significant amount of area taken is up by the 500MB of on-chip SRAM, with a very small amount of area dedicated to MatMul cores that offer 1.2 PFLOPs of FP8 compute – a fraction of compute compared to Nvidia GPUs. This compares to LPU 1 with 230MB of SRAM and 750 TFLOPs of INT8, with the performance increase mostly driven by node migration from GF16 to SF4. As a single monolithic die, advanced packaging isn’t required.

One of the benefits of relying on SF4 is that it isn’t [constrained like TSMC’s N3, which is putting a cap on accelerator production and is a key reason why the industry remains compute constrained.](https://newsletter.semianalysis.com/p/the-great-ai-silicon-shortage) This is in addition to not having [HBM which is also constrained](https://newsletter.semianalysis.com/p/memory-mania-how-a-once-in-four-decades). This allows Nvidia to ramp production of the LPU without sacrificing or eating into their valuable TSMC allocation or HBM allocations, representing true incremental revenue and capacity that noone else can access.

Since Nvidia has taken over, the next generation LP40 will be fabricated on TSMC N3P and use CoWoS-R, and Nvidia will contribute more of their own IP such as supporting the NVLink protocol rather than Groq’s C2C. This will be the first LPU to be extremely co-designed alongside the Feynman platform. Groq’s original plans for LPU Gen 4 was also with TSMC and Alchip as the back-end design partner. Alchip’s involvement is now redundant with Nvidia able to perform backend design on their own. One of the technical innovations planned is hybrid bonded DRAM to extend on-chip memory with only a slight decrease in latency and bandwidth vs SRAM, but much higher performance compared to DRAM. SK Hynix was tapped as the supplier of the DRAM to be used for the 3D stacking. All of this and more was detailed long ago in the [Accelerator model](https://semianalysis.com/accelerator-hbm-model/).

![](https://substackcdn.com/image/fetch/$s_!4-mW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbf0a9df3-57f3-43b2-a090-67f9dbdee3d9_2218x1215.png)

Source: Nvidia, [SemiAnalysis Accelerator Model](https://semianalysis.com/accelerator-hbm-model/)
