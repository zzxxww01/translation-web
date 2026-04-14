Scientific experiments can vary wildly in time required for completion. In biology, plenty of experiments take days to complete. These longer timelines require long rollouts, meaning rewards will be sparse. Sparse rewards provide less signal for the model to learn from.

![A screenshot of a computer](https://substackcdn.com/image/fetch/$s_!0_LC!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F31e4836d-b56b-4d50-b74a-c3119c191f47_937x296.png)

Source: Nvidia, TogetherAI, SemiAnalysis

One way around this would be to reward the model’s steps, not just its result. This rewards the model’s process and thinking, as opposed to just the final action. While it can be difficult to correctly identify what a “correct” step looks like, it can be approximated through the use of rubrics. In fact, this is exactly how OpenAI grades problems on open ended research tasks in a recent eval, Frontier Science, which measures a model’s ability to perform scientific research tasks. In practice during experiments, tasks can be split into individually rewarded ones that shrink down the grading time horizon.

![](https://substackcdn.com/image/fetch/$s_!HRMu!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbebca705-7e8a-491b-bd76-887242074973_1067x1008.png)

Source: OpenAI

Long rollouts are also terrible for GPU utilization, which is why many of the labs have been utilizing methods like in-flight weight updates. Here, weights are exchanged and straggler rollouts continue with stale KV Caches. This allows for training to continue while straggler rollouts finish. The result can yield a 2x improvement on the amount of iterations for the same wall clock time.

![](https://substackcdn.com/image/fetch/$s_!orCV!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0eb2e6c0-c770-46c2-9a0a-ad28f85be884_1345x1120.png)

Source: [Piché et al](https://arxiv.org/pdf/2509.19128v1), 2025

Another bottleneck lies within the available data. Scientific literature often includes results that disagree with each other even on basic questions, making it difficult to construct reliable training sets. Biology is somewhat less challenging because existing open-source data is more common. AlphaFold was trained on data from the Protein Data Bank, which contained 170,000 samples. FutureHouse’s Ether0 used the Open Reaction Database. Additional efforts like EvE will continue to provide valuable platforms for model providers.

Though pharma also posses large swaths of closed source datasets. We expect to see more partnerships between frontier labs, which have the ML expertise pharma companies struggle to attract, and pharma companies, which have the biological data and clinical knowledge the labs lack.

![A diagram of a machine](https://substackcdn.com/image/fetch/$s_!zcwh!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2aed2777-73b3-4f31-b8ab-6683aa0b73fc_937x527.png)

Source: Novo Nordisk

While there are obstacles, including some outlined above, there is so much low hanging fruit to capture that we expect efforts focused on high compute RL for science to be extremely valuable rather quickly.

Many of the capabilities that have enabled the vast increase in progress have relied on scaling RL. While there is still plenty to go, there is one other dimension that is showing early promise. This can be done with current models, though at substantially higher costs. Below we dive into an additional frontier opening right in front of our eyes.
