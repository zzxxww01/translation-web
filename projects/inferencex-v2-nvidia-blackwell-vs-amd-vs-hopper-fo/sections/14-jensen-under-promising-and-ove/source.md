At GTC 2024, Jensen was on stage promising up to 30x performance gains from H100 to GB200 NVL72, [everyone thought it was classic marketing lookmaxxing and would not be achievable in real world.](https://newsletter.semianalysis.com/p/nvidia-blackwell-perf-tco-analysis) Many looked to come up with labels for this perceived use of a reality distortion field so they could crack more Jensen Math jokes. Indeed – [we did point to the comparison of 30x performance difference between the worst case](https://newsletter.semianalysis.com/i/175661150/benchmarking-the-h200-on-its-bad-hair-day) for H200 on FP8 to a reasonable case of the GB200 on FP4.

* [Nvidia Blackwell Perf TCO Analysis - B100 vs B200 vs GB200NVL72](https://newsletter.semianalysis.com/p/nvidia-blackwell-perf-tco-analysis) - Dylan Patel and Daniel Nishball · April 10, 2024

![](https://substackcdn.com/image/fetch/$s_!9ywW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4fec3378-2cf4-4c1c-a40d-bcbd788c9a70_3022x1964.jpeg)

Source: [Nvidia GTC 2024](https://newsletter.semianalysis.com/p/nvidia-blackwell-perf-tco-analysis)

But it turns out the joke is on them. Fast forward almost two years later, and we can now see that it wasn’t marketing hype lookmaxing after all, and Jensen was actually under promising on Blackwell performance the whole time. From our testing, Blackwell is so good at large scale MoE inferencing compared to even a strong H100 disagg+wideEP FP8 baseline that it, at 116 toks/s/user, delivers up to 98x better perf on GB200 NVL72 FP4 and up to 100x better perf on GB300 NVL72 FP4! Maybe the new Jensen Math rule is that he delivers double whatever he promises in terms of token throughput. The more you spend, the more you save indeed!

![](https://substackcdn.com/image/fetch/$s_!rxr1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F70638c7e-69a6-43f2-96a4-23766bcabbd2_2121x1248.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Even when factoring in the increased total cost of ownership of Blackwell and Blackwell Ultra, we see a 9.7x(40 tok/s/user) up to 65x(116 tok/s/user) improvement in tokens per dollar compared to Hopper. [You can explore Hopper vs Blackwell performance in detail on our free website](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_prec=fp4%2Cfp8&i_metric=y_costh&i_log=1#inference). Blackwell performance is so good compared to Hopper that we needed to an log scale to our dashboard in order to visualize it.

![](https://substackcdn.com/image/fetch/$s_!7m9y!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F402b23af-7ad6-46e4-97af-a5698ea2bd87_2176x1416.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

As mentioned earlier in the article, B300 servers only connect at most 8 GPUs using the 900GByte/s/GPU NVLink scale-up network whereas GB300 NVL72 servers connect 72 GPUs using the NVlink scale-up network. So when we need more than 8 GPUs (but less than 72 GPUs) for the inference setup, we need to bring in multiple nodes of B300 servers to form our inference system which means communications falls back to the lower InfiniBand XDR scale-out network featuring 800Gbit/s (uni-di) per GPU of bandwidth. Compare this to a rack scale GB300 NVL72 which connects 72 GPUs over NVLink delivering 900GByte/s (uni-di) per GPU of bandwidth and we can see that the rack-scale server allows the GPUs in the inference setup to talk to each other with over 9x higher bandwidth compared to the case of the multiple nodes of B300 servers.

SemiAnalysis is free open source software and reader-supported. To receive new posts and support our work, consider becoming a free or paid subscriber.

![](https://substackcdn.com/image/fetch/$s_!x_1H!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8664f48c-037c-45cc-b6f8-1999ed0cee0e_2298x1430.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Admittedly the GB300 NVL72 has a higher all-in cost per GPU, but this only reduces the bandwidth per TCO advantage to being 8x faster. The bandwidth advantage of the rack-scale architecture directly drives a much lower cost per token. Google TPU, AWS Trainium and Nvidia are the only AI chips to have rack scale system designs deployed today. Engineering samples and low volume production of AMD’s first rack scale MI455X UALoE72 system will be in H2 2026 while due to manufacturing delays, the mass production ramp and first production tokens will only be generated on an MI455X UALoE72 by Q2 2027.

![](https://substackcdn.com/image/fetch/$s_!UGuH!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F58c7b664-76a7-454b-ac99-036b0b6f4abb_2132x1456.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)
