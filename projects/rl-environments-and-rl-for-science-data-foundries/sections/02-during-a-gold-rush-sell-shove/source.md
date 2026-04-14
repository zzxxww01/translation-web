During a Gold Rush, sell shovels. In an RL Scaling Boom, sell RL environments. More than 35 companies have popped up whose goal is to do exactly this across a variety of domains.

One set of companies focus on cloning websites. For example, environment companies hire overseas developers to replicate the UI of sites like DoorDash or Uber Eats and sell the mockups to labs. Labs then train agents to navigate the site so in production the agent can perform required functions reliably and consistently.

These “UI gyms” often cost about $20,000 per website, and OpenAI has purchased hundreds of sites for ChatGPT Agent training and development. These environments are a one time purchase and are reused for future models. Trajectories and logs from previous runs are preserved and fed back into various stages of training, like mid-training.

![](https://substackcdn.com/image/fetch/$s_!kvQ_!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F04032584-5b2e-4b30-afa9-ba2fcc0f9ab9_2140x780.png)

Source: [A public talk by Karina Nguyen](https://karinanguyen.com/talks/), SemiAnalysis

Other companies branched out into more sophisticated environments than just a website. Examples include Slack, Salesforce, AWS terminals, Microsoft OneDrive, Gmail, Discord, and Atlassian. The goal is for agents to autonomously operate in these software platforms, learning and better understanding how to navigate and operate within them.

These platforms, once built, can be combined to represent higher fidelity tasks and workloads. Putting together platforms like Slack, an API endpoint to a browser, and a coding editor can construct an increasingly realistic software task for the model. This enables interactions to be more multi-turn as opposed to a single shot, for example pinging the model halfway through its process via Slack to request a feature change.

Some of the companies building these sorts of environments, include [Habitat](https://www.habitat.inc/), [DeepTune](https://deeptune.com/), [Fleet](https://www.fleetai.com/), [Vmax](https://vmax.ai/), [Turing](https://www.turing.com/), [Mechanize](https://www.mechanize.work/), [Preference Model](https://www.preferencemodel.com/), Bespoke Labs, Veris.ai and many others. Even within these companies there is significant diversity in quality or focus. Some companies focus on UI gyms, like Turing, while others like Mechanize focus on software engineering tasks. Almost all companies are seed stage companies with less than 20 employees, focused on 1 to 3 customers at most.

Most aforementioned companies close source their environments and serve them in exclusive contracts to the labs. Some, however, like Prime Intellect open source theirs and are fostering the [Environments Hub](https://www.primeintellect.ai/blog/environments), which aims to be a one stop shop for RL environments.

Others are building tooling for environments. [HUD](https://www.hud.so/) for example has tooling that allows for the wrapping any given software (e.g., a game, browser, google sheets) in a dockerized container, enabling its use as a scalable RL environment. Each container has two layers: the environment backend (the actual software being wrapped) and an MCP server that sits on top and exposes tool definitions the agent can call. When an agent issues a tool call like `click(x,y)` or `type(text)`, the MCP server translates it into an action on the underlying software and returns the resulting observation. This is generally scaled into many parallel instances. Each task includes a prompt, setup conditions, and success criteria that return a reward signal. Every tool call and observation is captured via telemetry, which is useful for debugging but also collected and fed into training at later stages.

![](https://substackcdn.com/image/fetch/$s_!FnWW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa0e265cb-a9a1-4cc2-8baa-3b1a353d98a1_1480x1620.png)

The highest in demand environments are coding environments. Understanding how these are built, structured, and assembled can provide a unique view into the infrastructure and engineering effort underpinning the progress we see today.
