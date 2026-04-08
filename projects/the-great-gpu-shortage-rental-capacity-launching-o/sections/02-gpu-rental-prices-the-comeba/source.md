But how did the market come to this point? Only six months ago, most market observers were skeptical on GPU terminal value and assumed an inexorably steep fall in GPU rental rates over time. Financial analysts chastised any Neocloud or Hyperscaler that used a 6-year depreciation period for its GPU compute assets. Let’s quickly recap the story so far before we discuss how trends could evolve in the future.

Before late 2025, the prevailing expectation across the ecosystem was that Hopper (i.e. H100 and H200) rental prices would drop considerably as Blackwell deployments ramped given the latter’s much lower cost of compute. Instead, the opposite happened in late 2025: demand for H100s was holding firm, and in many cases, *strengthening*. The rapid adoption of open-weight models and accelerating inference demand at that time was the first sign of the insatiable wave of compute demand coming to market.

January was the next inflection point for compute when memory pricing, across both DRAM and NAND pricing, went from rising aggressively for several quarters, to going completely parabolic, with LPDDR5 and DDR5 contract prices tracking toward ~4x and ~5x year-on-year increases respectively in 1Q26 based on our [Memory Model](https://semianalysis.com/memory-model/).

To manage margin risk stemming from this rapid hike in component costs, OEMs began repricing AI servers at levels that significantly exceeded the underlying increase in component costs. This complicated the cluster capital investment processes as higher server acquisition costs compressed prospective project returns, forcing some operators to slow-roll or abandon deployments. In effect, supply that would have otherwise come online was being withheld, tightening the rental market further.

![](https://substackcdn.com/image/fetch/$s_!9C0b!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Feef5eb94-8f3d-4a6e-b718-f1a44fb1d051_1821x783.png)

Source: [SemiAnalysis AI TCO Model](https://semianalysis.com/ai-cloud-tco-model/)

Amid the server procurement disarray cause by this AI Server Pricing Apocalypse, GPU rental demand was clearly accelerating, with most remaining spare capacity taken up completely during January and February. By March – it became increasingly impossible to find any H100s, H200s or B200 rental capacity for any term. Rental pricing broke above $2/hr/GPU for a 1y contract by late January, and then shot up 15-20% by mid-to-late February vs end January and is set to rise another 15-20% month-on-month by the end of March.

A major driver of demand early this year arose from native media generation - Seedance and Nano Banana are driving massive increases in token throughput as users generate and refine images and video at scale. But the most visible driver of demand is the emergence of multi-agent workloads executing multi-step workflows, operating at high concurrency and iterating continuously, leading to parabolic growth in token and compute consumption.

Look no further than the [trends regarding Claude Code that we have already called out](https://newsletter.semianalysis.com/p/claude-code-is-the-inflection-point) in many articles. SemiAnalysis as a company has, over the past 7 days, consumed billions of tokens costing around ~$5/M tok on average, but the return on time saved and expansion of workflows and capabilities far exceeds that cost. SemiAnalysis now deploys a suite of AI tools across workflows beyond simple search and summarization – notably dashboarding, automated scraping, large-scale data wrangling and agentic financial modelling.

We are tracking the overwhelming demand through proxies like [Claude Commits Daily](https://semianalysis.com/institutional/claude-commits-daily/). At the current trajectory, we believe that Claude Code will be 20%+ of all daily commits by the end of 2026. While you blinked, AI consumed all of software development. Institutional clients who are interested in the data set can reach out to our [API documentation team](https://semianalysis.com/institutional/api-documentation/).

![](https://substackcdn.com/image/fetch/$s_!NBsi!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9aaf29c7-7e4d-4ffe-a4b5-f3a20b77c99c_2761x1579.png)

Source: SemiAnalysis [Tokenomics Dashboard](https://semianalysis.com/institutional/tokenomics-dashboard/)

It seems that almost everyone in our circle is an avid user of Claude Code – yet we recognize that our circle of contacts are immersed in everything AI and Semiconductors, and thus they are just the tip of the spear. For many Fortune 500 companies and to the broader world, Claude Code and the Agentic world are but a quirky side story that may come up on their Facebook feeds or their favorite NPR podcasts. They are completely unaware of the tidal wave of productivity and upheaval that the agentic world is about to unleash upon the world.

![](https://substackcdn.com/image/fetch/$s_!yIvt!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F39c3c02b-9b11-4133-b28d-36a107865030_1024x683.jpeg)

Source: SemiAnalysis, Generated by Google Gemini

As those in the broader economy that recognize the amazing return on investment from using AI Tools join us in surfing this tidal wave, there will continue to be a step shift higher in token consumption over time. The debate on the true return of using AI is now a settled question – the use of AI tools can deliver value an order of magnitude greater than the cost of using the tools. The shift up and to the right in the demand curve for tokens is providing a powerful and relatively inelastic (for now) force driving up GPU rental pricing.

Put simply – if the return on investment from using AI tools is 5-10x, then there is clearly a long way to go in GPU rental pricing before prices rise enough to curtail demand. It would not surprise us for the increases in rental pricing to exert further upward pressure on server and component costs.
