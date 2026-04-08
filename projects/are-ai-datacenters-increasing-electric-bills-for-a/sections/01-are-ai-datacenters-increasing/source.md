*SemiAnalysis x Fluidstack is launching GTC with a 48-hour, full-stack AI infrastructure hackathon on March 15th from Power to Prefill, Dirt to Decode. With speakers from OpenAI, GPU MODE, and Thinking Machines, plus compute grants and GPU cluster access, come build with the best: [APPLY HERE](https://luma.com/SAxFSHack).*

The topic of datacenter load growth and impact on power prices remains broadly misunderstood, akin to the [water consumption myth that we debunked recently](https://newsletter.semianalysis.com/p/from-tokens-to-burgers-a-water-footprint). It was at the forefront of the 2025 New Jersey elections, after a [~20% jump](https://www.pa.gov/governor/newsroom/2025-press-releases/gov-shapiro-s-legal-action-again-averts-historic-price-spike-acr) in residential electricity rates overnight in June 2025. Some even began finger-pointing at the 300MW Nebius AI Datacenter for Microsoft in the state, a laughable claim given [>85% of its power is self-generated](https://newsletter.semianalysis.com/p/how-ai-labs-are-solving-the-power). Are AI datacenters really causing households to pay electricity 20% more expensive?

This report explores the question by analyzing the two biggest energy markets in the US, which are also the largest AI Datacenter hubs: the PJM interconnection area – the grid operating covering 13 eastern US states (including New Jersey) - and ERCOT, who oversees the electric grid in Texas. In the Lone Star State, prices have been roughly stable for the last three years. On the other hand, the 67 million residents of the PJM area are set to see their bill increase by an average of ~15% in 2026 relative to the “pre-AI-Datacenter” era? Why such a divergence? In short, empirically the fault is government policy, not AI.

![](https://substackcdn.com/image/fetch/$s_!YaBK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff4cbff97-5557-4b44-aaa1-539add752ebc_2400x1125.png)

Source: [SemiAnalysis Energy Model](https://semianalysis.com/energy-model/), PJM, Monitoring Analytics

In PJM, we think poor market design is the main culprit. Most of the 15% increase in household electricity bills in PJM is driven by a widely misunderstood and somewhat obscure mechanism: the BRA capacity auction. The 2025/26 auction increased 9.3x over the prior year, as shown below. Worse: this increase is driven by a “simulation” and doesn’t reflect actual conditions. Is is largely a function of the demand and supply forecast made by a central planner (PJM), which as we’ll explain, has a history of huge miscalculations.

![](https://substackcdn.com/image/fetch/$s_!4uxO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9e61dd7a-0a0b-4903-9694-84e6529ae506_3179x1543.png)

Source: PJM BRA Report

Many are finger-pointing at the surge in AI datacenters, and it is understandable. The PJM area is at the forefront of the AI boom, with G[oogle notably training its Gemini model around Columbus Ohio](https://newsletter.semianalysis.com/p/multi-datacenter-training-openais), while [Anthropic/Amazon’s “Project Rainier”](https://newsletter.semianalysis.com/p/amazons-ai-resurgence-aws-anthropics-multi-gigawatt-trainium-expansion) and [Meta’s “Prometheus”](https://newsletter.semianalysis.com/p/meta-superintelligence-leadership-compute-talent-and-data) in Indiana and Ohio are both in our [world’s top 5 largest AI Datacenters](https://www.youtube.com/watch?v=a-9egkpaZUw). PJM also hosts the world’s largest datacenter hub: Northern Virginia.

Now look at Texas. The state is witnessing an equivalent AI buildout, with OpenAI, Google DeepMind, Anthropic all building massive facilities. Yet power futures in Texas have moved only a few percent in the past year. No 9x spike, no crisis, very different market design.

![](https://substackcdn.com/image/fetch/$s_!bTKf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F30a916ae-8f6f-462a-a184-7622bd295775_1808x1110.png)

Source: Bloomberg

Let’s dig in. This report focuses on ERCOT and PJM since they’re the two largest energy markets in the country, and are epicenters of the AI revolution. We’ll dig into their respective market design, explain how they’ve reacted to booming AI Datacenter load growth, and how that will flow to households.

Then, behind paywall, we discuss the supply chain implications. We believe that market constraints are dramatically shifting and many are missing it. This shift impacts major AI winners such as IPPs (Vistra, Constellation, Talen..), equipment suppliers, datacenter developers like cryptominers.

For institutions looking for deeper analysis, subscribe to our [Energy Model](https://semianalysis.com/energy-model/) and [Datacenter Industry Model](https://semianalysis.com/datacenter-industry-model/). The latter tracks and forecasts quarter-by-quarter, 2017-2032, over 5,000 individual facilities and their electrical capacity. The Energy Model builds an energy supply & demand analysis on top of it, by tracking and forecasting operations for every single power plant in the US, estimating their true ELCC, analyzing interconnection queue dynamics, and matching against our datacenter demand-side data.

Let’s start with a brief explainer of what “capacity” actually is, how it flows to your monthly bill, and then dig further into market designs.

*This report is a collaboration between SemiAnalysis and Archer Daniels Midland Investor Services (ADMIS), a leading futures brokerage and clearing firm.*
