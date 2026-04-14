An area ripe for scaling is combining different models to think together in service of a single problem. At a high level, this is how Grok 4 Heavy, Gemini Deep Think, and GTP5-Pro work.

![](https://substackcdn.com/image/fetch/$s_!zfNX!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F99c932f8-16e6-41c1-979d-4fecbe893678_1012x717.png)

Source: xAI

In practice, the details can vary. For example, aggregating answers from different agents can involve something basic like the most common answer, having the models confer between themselves to pick one, or having a separate model read all the answers and pick one. We expect many incoming products to leverage more sophisticated multi-agent architectures.

The first example that went mainstream of such a system was Google’s AlphaEvolve, which locked several different agents under different roles in one loop. The overall architecture in this instance had sampler models that assembled prompts from a database containing previously discovered solutions to a problem, an ensemble models to generate new and improved solutions, and an evaluation system to verify answers.

These components were strung together in an evolutionary loop and their results were continuously checked by the verifiers. After a specific improvement over state-of-the-art solutions for a given problem were made, or when diminishing returns were reached given additional cycles, the loop ended.

![](https://substackcdn.com/image/fetch/$s_!gQcy!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F67410dcd-d8ca-42d6-a63b-07d6ca923eb6_878x695.png)

Source: AlphaEvolve, Google

Since then, many different architectures have popped up, some targeted at specific evals. As an example, researcher [Jeremy Brennan](https://jeremyberman.substack.com/p/how-i-got-the-highest-score-on-arc-agi-again) leveraged a multi-agent architecture built on top of Grok 4 to get a record on ARC-AGI. The actual method is rather simple, involving Grok 4 generating instructions for each task. Then, each instruction is given to another agent that tests these instructions on the training examples. If a perfect solution emerges, these are locked in and applied to the held-out test grid. Otherwise, they enter an iterative refinement cycle.

![A black screen with colorful arrows](https://substackcdn.com/image/fetch/$s_!8kGI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F662d0269-0b70-451e-b252-2c3b1d96a4c2_937x611.jpeg)

Source: ARC-AGI Leaderboard at the time of Jeremy’s submission.

Other architectures only use subagents. [In one case](https://arxiv.org/pdf/2509.07506), 4 distinct o4-mini subagents achieved 1.3x speedup on average on existing, production grade SG Lang Kernels. Specifically, existing CUDA kernels are plucked from SG Lang and isolated such that they can be evaluated on a standalone basis. Then it passes through a loop between four agents. One agents conducts testing to validate the kernel on a pass or fail basis, and the other conducts detailed profiling to identify performance deltas. The third agent plans targeted edits, while the fourth implements them.

![](https://substackcdn.com/image/fetch/$s_!DD3G!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F45e34ae7-126b-4c3b-ab59-3675c36c5e3b_1258x603.png)

Source: [Wei et al.](https://arxiv.org/abs/2509.07506)

Note that this does not necessitate an increase in model capability, either. While inference costs are significantly higher, the value of the problems these agents can solve is higher than the cost of running them. This will especially be true in areas like science and coding.

Some methods even report cost decreases on asks, like [recursive language models](https://alexzhang13.github.io/blog/2025/rlm/). In this case, an orchestrator calls other models recursively throughout a task. These systems showed exceedingly high performance on long context evaluations, as context can be cleverly split between the subagents and the orchestrator.

OpenAI are actively exploring ideas like self-play and bringing principles from AlphaGo into LLMs, and we view them as the leaders in this particular space. AlphaGo was unique because it achieved superhuman performance on chess and go through playing games against itself, not against any other humans.

Current LLM systems are rather primitive, and in principle are not that distinct from the model running in one for loop. This is powerful in practice: Claude Code is a billion dollar ARR product largely off of simple ideas that stitch together a more autonomous agent. However, it is important to look to what capabilities will look like when more sophisticated multi-agent cooperation come to production.

Improved architectures for agent cooperation will similarly unlock the capability for LLMs to tackle larger and larger projects. In principle, this is not too dissimilar to humans being able to build larger projects in groups relative to individually.
