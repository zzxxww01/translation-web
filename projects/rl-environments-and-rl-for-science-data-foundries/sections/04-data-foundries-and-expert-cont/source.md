The reason environment tooling in general is useful is because environments are being created across many different domains: Chip design environments so models can aid in the design process, accounting ones for model to do taxes, and EHR software for medical use workflows are but few examples.

While software engineers construct the environment itself, often the workflows are created, described, and graded by domain specific contractors involved in the environment creation process. Finance professionals help define financial tasks, doctors for medicine, lawyers for law, etc.

Labs will go through human data contractor firms, who we will touch on shortly, who are looped in for their input on specific task creation. Contracts typically last at least a quarter and can be part time or full time. Contractors design tasks, write expected solutions, specify reward signals, and in some cases, grade model solutions. These reward signals can be in the form of rubrics, the writing of which can also involve contractors, or strict verifiers. These are the sort of experts that would be contracted to help build evals like GDPval.

![](https://substackcdn.com/image/fetch/$s_!lCmR!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F44e8dce0-9fc7-4835-bd97-ac730132e885_1880x802.png)

*Data processing pipeline from OpenAI. OpenAI has a private internal platform for contractors, named Feather, which data is processed through. Image Source: OpenAI*

Firms like Mercor, Handshake, Surge, and Aboda.ai are used to hire these experts across many professional domains. Surge is the more established and larger player, with revenue we believe is closer to $1B ARR.

Most of these firms started out as AI interviewers or job matching companies, but ultimately found that being a connector between the labs and contractor experts is more valuable.

Coding is in the most amount of demand, but spending on non-professional domains like photography, music, and design has picked up. As mentioned, the labs want to not just increase the number of tasks they post-train over for a given domain, but also the breadth and variety.

Revenue for these providers is mostly concentrated around western labs like Anthropic, OpenAI, and Google. However, we think Surge is also active internationally, selling to Chinese labs like Moonshot and Z.ai. Indeed, we believe access to these RL environments played a huge part in increasing the capabilities for Kimi K2 Thinking and GLM-4.6. When companies advertise increased capabilities in PowerPoint deck or Excel sheet creation, that is directly downstream of additional RL training.

Chinese VC firms are actively trying to stand up Chinese data foundry competitors so they can fully serve the local ecosystem at cheaper prices than western ones. Most Chinese labs are still early to scaling RL: Qwen is currently spending around 5% of their pre-training compute on post-training. Successful homegrown data foundry business will drastically accelerate the transition, compute permitting, of course.

![](https://substackcdn.com/image/fetch/$s_!qotS!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F70e2bbd2-5bd8-4410-aace-24fef73f4e63_1606x1003.png)

Source: Aboda.ai, SemiAnalysis

In the case above, contractors provide full solutions with explanations. Contractors can also and grade model outputs with feedback on errors. This data can be sourced in any language and translated by another model if needed.

Firms like Mercor are also producers of a significant amount of grading rubrics, which can be used in a variety of different domains. Currently, most rubrics are written by humans, though there are some companies, like the LLM Data Company, trying to have models write grading rubrics. This can be done through, for example, connecting performant models to highly reliable MCPs to extract information to then be used in a structured rubric.

![](https://substackcdn.com/image/fetch/$s_!GqlC!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0265b727-8cc7-4774-98f9-023dea365b99_1493x1744.png)

*LLM Generated Rubric. Source: The LLM Data Company*

We think there is significant upside to this approach, though AI labs currently focus on consuming human generated data. In the long run, as models get better, reliability and quality will improve. As mentioned, all the labs are chasing AI-automated AI research.

Given the diversity of options, understanding data procurement decisions is critical to informing lab strategies. This paradigm is [not like pre-training where everyone had access to the same data](https://newsletter.semianalysis.com/p/scaling-reinforcement-learning-environments-reward-hacking-agents-scaling-data).
