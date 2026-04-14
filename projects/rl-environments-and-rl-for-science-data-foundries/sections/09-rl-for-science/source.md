LLMs unlock a new frontier where models can search, plan, and propose experiments. With the right tools, agents will also be able to execute them. RL enables the harnessing of the feedback from those experiments into information the model can use to improve, enabling a loop of self-improvement given the right conditions.

There are several companies leveraging this, and one such company is Periodic Labs. which aims to build an AI scientist trained through lab generated data.

The goal is to create a closed-loop RL systemwith rewards grounded in physical experiments. Models use tools, including other smaller specialised models, to test out hypotheses and validate ideas. Then, these ideas are tested out in increasingly high fidelity simulators, which later inform physical experiments.

This way, subagents handle what they are good at and general LLMs can be used for orchestrating. Orchestration may also extend to physical tools, like characterizing materials, for example.

![Fig. 1](https://substackcdn.com/image/fetch/$s_!Tibh!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F67ec8066-bec8-4d85-afb9-0c08b0b62bf2_936x670.png)

*Sample existing closed loop system. Source: [Wang et al](https://www.nature.com/articles/s41467-024-55655-3), 2025*

This process of testing ideas through increasingly high-fidelity methods to derisk experiments before running them in a lab maps roughly onto a graduate student’s typical workflow.

![](https://substackcdn.com/image/fetch/$s_!nwQx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F38ce44d5-ee80-4656-9a39-4b1a91873de6_1460x666.png)

*Periodic’s closed loop system. Source: Rohan Pandey.*

Open-source models can be used as a starting point and mid-training can be done to extend capabilities. Mid-training is continued pre-training (next token prediction), which can be used for extending a model’s cutoff date, improving domain knowledge on specific topics, and or priming them for high compute RL. For example, when OpenAI models see a refreshed cutoff date, it is due to continued mid-training on top of the model.

In highly specific scientific domains, mid-training will lead to higher quality models after post training. Meta, in their recent code specific model, found that the benefits of mid-training extended even after other stages (e.g., SFT) were applied. Meta used 1T tokens for mid-training for a recent model, but we expect OpenAI to be using somewhere between 5-10x more.

![](https://substackcdn.com/image/fetch/$s_!DVxi!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F949e444d-605d-44bc-ab24-8b39d9b00554_1460x471.png)

Source: Meta

An example of data that it added into the mid-training stage is environment trajectories from previous runs. These are the collected rollouts that were generated when a previous version of the model was undergoing RL.

![](https://substackcdn.com/image/fetch/$s_!nZ31!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7ea859aa-bfe3-44a3-b203-8a6785c66335_1077x913.png)

Source: Meta

To supply data for RL and mid-training, Periodic is building a large physical lab to run experiments and produce experimentally verified reward signals. This is in line with other efforts, as DeepMind is also starting an automated materials science research lab in 2026.

Running your own experiments yields complete knowledge of input variables and outcomes, something not guaranteed when training purely on published papers, which often disagree even with comparable metrics. Another domain which requires significant lab work is biology. It is also a domain in which the labs have had diverging approaches.
