The fundamental tradeoff with LLM inference is throughput versus latency. *Interactivity* (tok/s/user) describes how fast each user of a system receives tokens – it is the inverse of time per output token (TPOT). *Throughput* (tok/s) describes how many total tokens a system can crank out across all users. One can achieve higher total throughput by batching requests, but each request will be allocated less FLOPs and thus complete slower. This is analogous to the choice of riding a metro bus vs a race car. The metro bus serves many riders, but also makes frequent stops which takes time, but the cost of the metro bus can be amortized across many passengers. The race car can only carry one or two passengers, but it will make few if any additional stops meaning a faster travel time overall, but it is much more expensive to ride per passenger. The metro bus might make more sense for people heading to the park on a weekend, while the race car might be better for bringing a celebrity to their destination. There is no one size fits all solution.

![](https://substackcdn.com/image/fetch/$s_!M543!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F18c9a3dd-3777-44d5-a3e2-b4d28140df38_2106x1380.png)

Source: SemiAnalysis

Most benchmark results we will show in this article are InferenceX is a curve. It is important to analyze throughput at various levels of interactivity/latency instead of just looking at maximum achieved throughput (which normally can only be achieved at a single low interactivity). With inference, there is no one size fits all use case. The level of interactivity and throughput needed depends on the use case. For instance, real-time speech models require extremely low latency so that the end user can maintain a natural “conversation” with the LLM, whereas a basic QA chatbot may allow for higher latency. We leave it up to the reader to look at the curve and apply this principle to identify where their use case falls on the throughput-interactivity curve.

The Cost/Perf per TCO vs Interactivity/End-to-End Latency curve mostly follows the Throughput vs Interactivity/End-to-End Latency Curve: More tokens/hour leads to a lower cost per token as fixed $/hour costs are amortized over more tokens produced.

### Prefill and Decode Phases

Inference contains two main phases: prefill and decode. *Prefill* occurs during the first forward pass of a request’s lifetime. It is computationally intensive since all tokens in the request are processed in parallel. This phase is responsible for “filling up” the KV cache for a sequence. After prefill, responses are generated (or *decoded*) one token at a time. Each forward pass loads the entire KV cache for a sequence from HBM, while only performing the computation for a single token, making decode memory (bandwidth) intensive.

When prefill and decode performed on the same engine, prefill constantly disrupts decode batches leading to worse overall performance.

### Disaggregated Prefill

Disaggregated prefill (aka PD disaggregation or simply “disagg”) is the practice of separating the prefill and decode phases across separate pools of GPUs or clusters. These separate prefill and decode pools can be tuned independently and scaled to match the needs of workloads.
