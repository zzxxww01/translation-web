![](https://substackcdn.com/image/fetch/$s_!6xHo!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F44e44d5f-8aeb-4974-9868-cd834fe74993_2560x1440.png)

*ARM’s CSS Offerings Balance Customization with Development Cost. Source: ARM*

ARM’s core IP licensing business has been very successful in the datacenter market, with nearly every hyperscaler adopting their Neoverse CSS designs for their custom CPUs. To date, over 1 Billion Neoverse cores have been deployed across datacenter CPUs and DPUs, with 21 CSS licenses signed across 12 companies. With increasing core counts and hyperscale ARM CPU ramps, datacenter royalty revenue more than doubled Year-over-Year, and they are projecting CSS to represent over 50% of royalty revenue in the next couple of years. Read our article here to learn more about ARM’s business model and how CSS extracts more value.

* [Arm and a Leg: Arm's Quest To Extract Their True Value](https://newsletter.semianalysis.com/p/arm-and-a-leg-arms-quest-to-extract) - Dylan Patel, Myron Xie, and 2 others · September 14, 2023

However, ARM is taking things further in 2026 and will be offering full datacenter CPU designs, with Meta as its first customer. This CPU, codenamed Phoenix, changes the business model by becoming a chip vendor, designing the entire chip from cores to packaging. This means that ARM will now compete directly with its customers who license the Neoverse CSS architecture. ARM, who are majority owned by SoftBank, are also designing custom CPUs for OpenAI as part of the Stargate OpenAI Softbank venture. Cloudflare is also looking to be a customer for Phoenix. We have detailed COGS, margin, and revenue in [Core Research](https://semianalysis.com/core-research/).

Phoenix has a standard Neoverse CSS design and layout that is similar to Microsoft’s Cobalt 200. 128 Neoverse V3 cores are connected with ARM’s CMN mesh network across two half-reticle size dies made on TSMC’s 3nm process. On the memory and I/O front, Phoenix features 12 channels of DDR5 at 8400 MT/s and 96 lanes of PCIe Gen 6. Power efficiency is competitive, with a configurable CPU TDP of 250W to 350W.

With this, Meta now has their own ARM CPU to match the likes of Microsoft, Google and AWS. As an AI head node, Phoenix enables coherent shared memory to attached XPUs over PCIe6 via an Accelerator Enablement Kit. We will detail the next generation ARM “Venom” CPU design for our subscribers below, including a significant memory change.
