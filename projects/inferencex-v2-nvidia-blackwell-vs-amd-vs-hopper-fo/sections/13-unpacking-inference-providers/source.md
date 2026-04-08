Below is a list on OpenRouter of all inference providers that serve DeepSeek R1 0528 FP8 along with their cost per million input/output tokens and average interactivity listed on. Disregarding Chutes, the middle of the pack provider serves at an interactivity of around 35 tok/s/user.

![](https://substackcdn.com/image/fetch/$s_!b5bS!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fce79108c-8341-4100-86de-943d8ca3c34e_916x1190.png)

Source: [OpenRouter](https://openrouter.ai/deepseek/deepseek-r1-0528/performance)

We can then use real InferenceX data to interpolate the cost per million input/output tokens at an interactivity level of 35 tok/sec/user, which is a reasonable interactivity level given the data above.

As we mention later in the article, this is best understood as *baseline* data and not completely representative of real-world inference, mainly because InferenceX benchmarks on random data and disables prefix caching. In other words, performance/cost will be *at least* this good. It is also important to note that there are not data points for *each GPU* at *each* interactivity level. Thus we cannot make *exact* comparisons at each degree of interactivity. We nevertheless think the bar chart comparisons presented below are (very) reasonable interpolations in lieu of using exact data points.

Comparing disagg+wideEP configs at this interactivity level, we see just how effective distributed inference techniques are when it comes to both perf/TCO and overall throughput. We also see how large scale up domains (like GB300 and GB200 NVL72) absolutely dominate in total throughput per GPU.

It is interesting to note that at this interactivity level (on an 8k1k workload type), the B200 can achieve the best perf/TCO when MTP is enabled. Below we also list the Total Cost of Ownership (TCO) (Owning – Hyperscaler) for each GPU:

![](https://substackcdn.com/image/fetch/$s_!ZFIh!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff200bfa6-02b5-464f-a4ea-ffe88cb6ed49_2520x81.png)

Source: [SemiAnalysis TCO Model](https://semianalysis.com/ai-cloud-tco-model/)

![](https://substackcdn.com/image/fetch/$s_!WB-s!,w_474,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffd2a22ee-c300-4fbd-a782-bdf5ac918c02_1882x1776.png)

Source: SemiAnalysis InferenceX

Let’s use the findings above to dig deeper into the unit economics of serving LLMs at scale. From the OpenRouter data above, we see that Crusoe serves at 36 tok/sec/user at $1.35/M input tokens and $5.40/M output tokens. If we assume no cache hits and that Crusoe is using at least H200s with SOTA inference techniques like MTP, disagg, and wide EP, the data above suggests they incur a cost of *no more than* $0.226$/M input tokens and $2.955/M output tokens for a profit margin of up to 83% gross margin (depreciation counted in cost of goods sold) on input tokens and 45% gross margin on output tokens.

SemiAnalysis InferenceX is free open source software and reader-supported. To receive new posts and support our work, consider becoming a free or paid subscriber.

Of course, these assumptions may not be *exactly* correct and these calculations don’t account for downtime or underutilization, but this gives an idea of some cool math you can do with InferenceX data. More analysis on the economics of inference can be found in the [SemiAnalysis Tokenomics Model](https://semianalysis.com/tokenomics-model/).

The OpenRouter data also shows Nebius AI Studio (Fast) serving DeepSeek FP4 at 167 tok/sec/user at $2/M input, $6/M output tokens. Adjusting the interactivity level in InferenceX accordingly and we see the following data.

![](https://substackcdn.com/image/fetch/$s_!28az!,w_474,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff41d237c-16c2-4a9d-b681-a6668b01f62b_2398x1526.png)

Source: SemiAnalysis InferenceX

At this high of interactivity, it becomes necessary to employ speculative decoding techniques like MTP to achieve high enough throughput to make inference economical. Luckily, MTP can increase throughput with relatively low risk to overall model accuracy. We will go on to talk more about MTP, and how it can be applied to increase throughput / decrease cost, in later sections of this article.

Lastly, we show one more chart of an FP8 DeepSeek workload served at 125 tok/s/user. This is another low latency workload where MTP considerably improves economic viability. As with the previous example, we note that at these higher ranges of interactivity, the cheapest configs all use MTP.

![](https://substackcdn.com/image/fetch/$s_!E0-S!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fccabb1a5-220a-4623-a615-245053808f24_2086x1738.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

### Nvidia Disagg Prefill and WideEP

EP requires all-to-all communication, where every GPU needs to send tokens to every other GPU. This is extremely bandwidth hungry. Recall that Nvidia’s servers have two separate networking domains – the scale-up NVLink domain, and the Scale-out Domain, usually using InfiniBand or Ethernet as the networking protocol.

* NVLink domain (within the NVL72 rack): 72 GPUs connected via NVLink with 900 GB/s uni-directional bandwidth per GPU. This is roughly 7-10x the bandwidth of the InfiniBand/Ethernet based scale-out network.

* InfiniBand/RoCEv2 Ethernet (outside of the NVL72 rack): Typically 400-800 Gbit/s per GPU uni-directional (50-100 GB/s). Note that all our testing for Nvidia was conducted on InfiniBand based clusters.

TP shards every layer’s weight matrices across GPUs. This means that every single token at every single layer requires up to two all-reduce communications (one after the column-parallel GEMM, one after the row-parallel GEMM). For EP, all-to-all is done only at MoE layers. Each GPU sends only the tokens routed to each expert. This means cheaper comms across all layers for EP vs TP.

Because EP’s all-to-all communication bandwidth requirements scale with the number of participants, staying within the high-bandwidth NVLink domain before having to cross the slower IB/Eth fabric is better. With NVL72, EP across 72 GPUs is possible without ever leaving NVLink, whereas previous generations (with only 8-GPU NVLink domains) could only do EP across 8 GPUs at NVLink speed before hitting the slower IB/Eth networks.

SemiAnalysis InferenceX is free open source software and reader-supported. To receive new posts and support our work, consider becoming a free or paid subscriber.

Wide EP also has a major advantage in weight loading efficiency. For a model like DeepSeek R1, decode is memory-bandwidth-bound: the bottleneck is how fast GPUs can load weights from HBM. With wide EP (e.g., DEP32), 32 GPUs collectively hold and load the 670B weights once, each loading only its shard (~21B). The total HBM bandwidth of all 32 chips is applied to loading a single copy of the model. By contrast, with narrower EP and more DP replicas (e.g., 5xDEP8), each of the 5 replicas needs its own full copy of the 670B weights, that’s 5×670B = 3.35T of redundant weight loading across the system. EP amortizes weights across chips; DP replicates them. This is why wider EP, enabled by high-bandwidth interconnects like NVLink, delivers significantly better throughput per GPU.

![](https://substackcdn.com/image/fetch/$s_!7EhO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7ed2a472-3511-4b29-afbd-0c593795085a_2434x1430.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Generally, TP is preferred at lower concurrencies due to load balancing. At small batch sizes, EP suffers from uneven token-to-expert routing, leaving some GPUs underutilized while others are overloaded. TP avoids this since each GPU holds a slice of every expert and always gets an equal share of work. At lower concurrency, the cost of this load imbalance outweighs TP’s additional communication overhead.

At higher concurrencies, this tradeoff changes. Expert activation becomes more evenly distributed across larger batch sizes, and EP’s communication and weight-loading advantages dominate over TP’s expensive per-layer all-reduce. In the middle of the curve, hybrid TP+EP configurations balance both concerns using small TP groups within each expert for load balancing while EP is used across the wider set of GPUs to amortize weights and reduce communication.

For higher interactivity levels (low batch size), large scale-up world sizes tend not to deliver stronger performance. B300 disagg over IB has the same performance as GB300 with NVL72, since the workload is latency-bound, not bandwidth-bound. The massive NVLink bandwidth advantage of NVL72 doesn’t matter because not even the much slower IB link is saturated by the tiny batches of tokens in flight.

Prefill/decode disaggregation also plays a role. Prefill is compute-heavy and bursty; decode is memory-bandwidth-bound and steady-state. When they share the same GPUs, they interfere with each other, causing latency jitter and wasted capacity. Separating them onto dedicated GPU pools lets each run a workload matched to its characteristics, improving effective utilization. This is why disaggregated B200 configs outperform single-node B200 in the middle of the throughput-interactivity curve. PD separation combined with wider EP across more GPUs over IB amortizes weights more efficiently than cramming both phases onto a single 8-GPU node.

[Side Note: the 10x inference engineers at TogetherAI noticed an pattern for multi-turn traffic where the requirements of first turn prefill is much different from the following turns prefill’s and disaggregrated it leading to better TTFT performance.](https://www.together.ai/blog/cache-aware-disaggregated-inference)

![](https://substackcdn.com/image/fetch/$s_!_Tls!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbfdcb99e-dc02-4468-bd72-b25a7be6c15d_2380x1386.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)
