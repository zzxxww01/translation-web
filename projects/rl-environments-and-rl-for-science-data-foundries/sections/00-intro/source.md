### Worker Automation, RL as a Service, Anthropic's next big bet, GDPval and Utility Evals, Computer Use Agents, LLMs in Biology, Mid-Training, Lab Procurement Patterns, Platform Politics and Access

By [AJ Kourabi](https://substack.com/@ajkourabi1) and [Dylan Patel](https://substack.com/@semianalysis)

Jan 06, 2026 · Paid

*We’re hiring for AI Analysts and Tokenomics Analyst roles. [Apply here](https://app.dover.com/SemiAnalysis/careers/ddbb65b5-1f71-4c20-835f-7c6860ed5d7f) or reach out directly.*

Last June, we argued that scaling RL is the critical path to unlocking further AI capabilities. As we will show, the past several months have affirmed our thesis: major capability gains are coming from ramping RL compute. Pre-training continues to see further optimizations, but the lab’s are laser focused on scaling compute for RL.

* [Scaling Reinforcement Learning: Environments, Reward Hacking, Agents, Scaling Data](https://newsletter.semianalysis.com/p/scaling-reinforcement-learning-environments-reward-hacking-agents-scaling-data) - Dylan Patel and AJ Kourabi · June 8, 2025

The best example of this is demonstrated by OpenAI. The company has used the same base model, GPT-4o, for all their recent flagship models: o1, o3, and GPT-5 series. Gains in the performance of OpenAI’s models for 18 months were being driven by post-training and scaling up RL compute alone. OpenAI has now fixed their pretraining problems, so with that vector of scaling unlocked, progress will be even more rapid.

![](https://substackcdn.com/image/fetch/$s_!cYt8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7e50fdb7-cb85-4d29-b665-bf4743c5d3f6_1142x634.png)

This is not to say that pre-training is dead: Anthropic, xAI, and especially Google all derived significant gains from scaling up pre-training. But OpenAI’s progress last year and ability to keep up using an older base model was existence proof of the efficacy of post-training.

Scaling up RL is difficult as it requires a steady stream of tasks the model needs to solve and learn from. Pre-training had the entire internet to train on, but equivalent corpus for RL is yet to be fully created. Most RL data and tasks must be constructed from scratch, which can be quite labor intensive.

Making the models “do the homework” started with math problems, which are easy to grade. Methods have since advanced, including branching out to newer domains like healthcare and financial modelling. To do this, models are placed in increasingly specialized “environments” that require the model to do these tasks.

Aggregating tasks and data can be done manually, or through the curation of high signal user data. The latter is what gives companies like Windsurf and Cursor the ability to post-train their own competitive models despite not having the resources of a lab.

These post-training efforts have improved model capability in domains like coding, but also model *utility*: models are more usable in everyday tools like Excel and PowerPoint.

To measure how much models are improving in utility and capability, OpenAI created an eval called GDPval. This eval covers 1000+ tasks across 44 occupations, picked from sectors that representing >5% of the economy. Many of these tasks are digital but require several hours to complete for a human. These tasks were created in conjunction with experts, averaging 14 years of experience.

Models are asked to solve these problems, given a prompt and a set of supporting documents. Tasks include filing a tax return for a fictitious human, creating slides as a client advisor for a resort, and creating commercials from a given set of stock footage. Grading occurs through experts picking between a model’s answer and a human expert’s answer. This win rate, if equal, would then mean that a model’s performance is then in parity with a human expert. The best current model, GPT-5.2, scores around 71%, meaning its work is tied to or preferred from human outputs 71% of the time.

![](https://substackcdn.com/image/fetch/$s_!utwm!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F370d577f-508c-40df-b6d4-857bf1225db8_1022x575.png)

*Sample task set from GDPval. Source: OpenAI*

While GDPval has some issues (e.g., skewed toward unusually specific digital work) it is the best example of how evaluations are shifting from measuring abstract intelligence to real world utility. This stands in contrast to most of the previous model evaluations, which focused on things like mathematical knowledge or PhD level scientific questions graded via multiple choice.

The underlying trend is models being able to operate autonomously for longer. With improved capabilities over shorter and longer horizons, AI companies think that models can help invent the next version of themselves. OpenAI, for their part, target having autonomous AI researchers by a March of 2028. Anthropic projects that in 2027, systems like Claude will be able to autonomously find breakthroughs that would otherwise take years to achieve.

![](https://substackcdn.com/image/fetch/$s_!2Q1-!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4d7a943d-bd4c-4a9a-8be7-c63038e40a79_1568x883.png)

Source: Anthropic

But this journey will require significant amounts of data and task curation. Computer use environments for example require considerable amount of rote software engineering including replicating existing websites on the internet. This can be slow for the labs to do which is why much of it has been outsourced.
