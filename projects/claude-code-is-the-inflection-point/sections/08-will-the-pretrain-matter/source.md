A more interesting question to ask is: does pretraining even matter anymore? Using the TCP/IP analogy for agents, having better packets on TCP/IP might not matter as much as having better coordinated features. Kimi 2.5 is an example. The most interesting information from that release isn’t state-of-the-art benchmark performance but rather the agent orchestration.

Every incremental model this year is going to heavily focus more on agent orchestration as well as performance, akin to reasoning did last year. And as Anthropic has moved passed benchmarks, comparing just model to model performance doesn’t make sense anymore, it will be about what agents can achieve together. OpenAI might have been caught flat-footed and missed the strategic inflection. Just as Anthropic and Gemini didn’t fully understand or push the RL and chain-of-thought inflection initially, it now seems like Anthropic is currently in the lead of agentic inflection.

Kimi 2.5 from Moonshot AI is a perfect showcase of the models to come. Kimi focused exclusively on the orchestration layer. Kimi 2.5 open-sourced everything in their release except for their agent orchestration layer. PARL or Parallel Agent Reinforcement Learning is a sign of what is to come. Using agents leads to better than Opus 4.5 performance according to in-house benchmarks. Sonnet 5 for example is clearly oriented towards agent swarms akin to how PARL works at Kimi 2.5.

Kimi 2.5’s new orchestration engine (closed source)

![](https://substackcdn.com/image/fetch/$s_!fOEe!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffce483cf-4a0a-4291-b937-6650a5ed848c_1191x646.png)

Source: [Kimi paper](https://www.kimi.com/blog/kimi-k2-5.html)

![](https://substackcdn.com/image/fetch/$s_!psG2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2260d62d-0cce-4be8-9cb6-e50fdf9dae6f_1183x627.png)

*source: Kimi 2.5*

Agent orchestration is the new CoT. Broad parallelization of agents will be the next capability akin to how having longer chain of thought tokens leads to better results. Soon there will be entire armies of agents spawned to complete a task at scale!

![](https://substackcdn.com/image/fetch/$s_!kH7c!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F67c9c93f-d03a-4dd6-8d5a-30b0c61bb846_1191x688.png)

*source: Kimi 2.5*

This seems as ripe of a frontier as the initial o1 performance gains, but for the first time it’s not OpenAI in the lead.

But before the excitement of limitless agent scaling, there is an issue that will be where competition actually is this year. Anthropic in [recent research](https://alignment.anthropic.com/2026/hot-mess-of-ai/) found that “**across all tasks and models, the longer models spend reasoning and taking actions, the more incoherent they become. This holds whether we measure reasoning tokens, agent actions, or optimizer steps**.”

[Power users of the models report the same](https://x.com/NathanFlurry/status/2014876907247149251), and the author mostly agrees that longer context windows devolve into incoherence.

![](https://substackcdn.com/image/fetch/$s_!YQxQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcbc120a1-eddc-42f4-b5ef-100791815e28_997x633.png)

Source: Anthropic

This frames the advantage that Anthropic’s token efficiency has, and why we think that task in the minimum amount of tokens is going to be one of the primary benchmarks of quality. The more coherence in a single context window, the more agents can be scaled up, etc. Token efficiency at the model level is likely going to tip off who is actually at the lead.

But amid the new rise in Claude Code, Anthropic is limited by FLOPs and MWs, not in terms of capability, and this new non-consumer driven explosion in demand is the key inflection point to watch for 2026. With accelerating users comes accelerating compute demands, and we think that Anthropics coming $350 billion dollar valuation is going to fund their expansion into the GW game in a big way. Below is our representation of the catchup in power that Anthropic is pushing.

![](https://substackcdn.com/image/fetch/$s_!7xxX!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7572d353-1443-483a-a286-4cb33d1413f9_927x585.png)

*source: SemiAnalysis [Tokenomics Model](https://semianalysis.com/tokenomics-model/)*

This is how Anthropic wins. But it’s OpenAI’s turn to show the world that they can pre-train a new model and potentially take the pole position again. The race seems more open than it was last year, and we are excited to see the pace of change continue.

On a parting note, we are going to share some of the information work we’ve been doing at SemiAnalysis with our new Claude Code overlords. Seeing really is believing, and we believe we are in a new era of time when the marginal cost of creating software as well as processing information has gone to zero. Things will change at an accelerated rate from here.
