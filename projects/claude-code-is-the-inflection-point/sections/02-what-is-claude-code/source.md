Claude Code is a terminal-native AI agent that is not focused on IDE or a chatbot sidebar like Cursor. Claude Code is a CLI (command line interface) tool that reads your codebase, plans multi-step tasks, and then executes these tasks. It might be incorrect to think of Claude Code only as focused on Code, but rather as Claude Computer. With full access to your computer, Claude can understand its environment, make a plan, and iteratively complete this plan, the whole-time taking direction from the user.

Claude Code does more than just code and is the best example of an AI Agent. You can interact with a computer with natural language to describe objectives and outcomes rather than implementation details. Provide Claude (the CLI) an input such as a spreadsheet, a codebase, a link to a webpage and then ask it to achieve an objective. It then makes a plan, verifies details, and then executes it.

It is a glimpse of the future, but it is also here today in software already. Your favorite engineers are vibe coding:

* **Andrej Karpathy**, [who coined the term vibe coding 1 year ago](https://x.com/karpathy/status/1886192184808149383?s=20), is [openly discussing the phase shift](https://x.com/karpathy/status/2015883857489522876?s=20), and specifically says “I’ve already noticed that I am slowly starting to atrophy my ability to write code manually. Generation (writing code) and discrimination (reading code) are different capabilities in the brain.”

* **Malte Ubl, CTO of Vercel**, claims that his “new primary job” is “to tell AI what it did wrong”

[￰4￰

Malte Ubl@cramforce

This year I understood bash, filesystems, the Postgres wire protocol, and sqlite deeper than I ever would have if my new primary job wouldn't be to tell AI what it did wrong

￰5￰

Anthropic @AnthropicAI

AI can make work faster, but a fear is that relying on it may make it harder to learn new skills on the job. We ran an experiment with software engineers to learn more. Coding with AI led to a decrease in mastery—but this depended on how people used it. https://t.co/lbxgP11I4I

4:10 PM · Jan 31, 2026 · 74.3K Views

21 Replies · 14 Reposts · 558 Likes](https://x.com/cramforce/status/2017631686142644691?s=20)

* **Ryan Dahl, creator of NodeJS,** says that “the era of humans writing code is over”

[￰6￰

Ryan Dahl@rough\_\_sea

This has been said a thousand times before, but allow me to add my own voice: the era of humans writing code is over. Disturbing for those of us who identify as SWEs, but no less true. That's not to say SWEs don't have work to do, but writing syntax directly is not it.

4:02 PM · Jan 19, 2026 · 7.25M Views

970 Replies · 2.74K Reposts · 20.1K Likes](https://x.com/rough__sea/status/2013280952370573666?s=20)

* **David Heinemeier Hansson**, creator of Ruby on Rails, is having some sort of anticipated nostalgia, reminiscing about writing code by hand while writing code by hand:

[￰7￰

DHH@dhh

Writing Ruby code by hand in a text editor feels like such a luxury. Maybe this will soon be a lost art, but that's just all the more reason to enjoy the privilege to its fullest while we still have it.

￰8￰

2:11 PM · Dec 2, 2025 · 52.6K Views

54 Replies · 44 Reposts · 968 Likes](https://x.com/dhh/status/1995858288710476080?s=20)

* **Boris Cherny**, creator of Claude Code says that “Pretty much 100% of our code is written by Claude Code + Opus 4.5”

[￰9￰

Boris Cherny@bcherny

@karpathy As always, a very thoughtful and well reasoned take. I read till the end. I think the Claude Code team itself might be an indicator of where things are headed. We have directional answers for some (not all) of the prompts: 1. We hire mostly generalists. We have a mix of senior

2:44 AM · Jan 27, 2026 · 1.29M Views

162 Replies · 411 Reposts · 6.85K Likes](https://x.com/bcherny/status/2015979257038831967?s=20)

* Even **Linus Torvalds** is vibe coding: [https://github.com/torvalds/AudioNoise](https://github.com/torvalds/AudioNoise)

But it isn’t just coders, here at SemiAnalysis our Analysts and Technical Staff have different roles and responsibilities. The Datacenter Model team needs to review hundreds of documents every week. Our AI Supply Chain team needs to inspect BOMs with thousands of line items. Our Memory Model team needs to build forecasts in near-real time as spot market prices explode. Our Technical Staff need to maintain a live dashboard for [InferenceMAX,](https://inferencemax.semianalysis.com/) including nightly runs of the latest software recipes across 9 different system types/clusters. From regulatory filings to permits, spec sheets to documentation, config to code, the way that we interact with our computers has changed.

As an example, our industry model analysts now use Claude Code to generate a plethora of helpful diagrams and analyses to parse and communicate important trends within large data sets:

Here’s an input:

![](https://substackcdn.com/image/fetch/$s_!ds_u!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F456e53bb-cf1f-4e16-94cf-7ad23cb32e08_900x936.png)

Source: SemiAnalysis, Claude Code

And here’s the output:

![](https://substackcdn.com/image/fetch/$s_!1CW1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F29cab5bf-fe5d-46e0-b93b-9caaf5a7d1ea_1043x585.png)

Source: SemiAnalysis, Claude Code

Coders will stop doing code and rather request jobs to be done on their behalf. And the magic of Claude Code is *it just works*. Many famous coders are finally giving into the new wave of vibe coding and now realizing that coding is effectively close to a solved problem that is better off supported by Agents than humans.

The locus of competition is shifting. Obsessions over linear benchmarks as to what model is “best” will look quaint, akin to how fast your dial-up is compared to DSL. Speed and performance matters, and the models are what power agents, but performance will be measured as the net output of packets to make a website, not the packet quality itself. The website features of tomorrow is going to be the orchestration through tools, memory, sub-agents, and verification loops to create outcomes and not responses. And all information work is finally addressed by models.

Opus 4.5 is the engine that makes this all possible, and what is important in linear benchmarking might not matter at all for agentic long horizon tasks. More on that later.
