RL is highly effective at teaching models to use tools. Through using open-source tooling, some startups now offer tailored RL services to large enterprises. The space is comprised of smaller YC startups like RunRL and Osmosis, but also ones started by experienced researchers like Applied Compute and Adaptive ML.

Often, Qwen models are used for this as they are easy to post-train and require little resources to run. Qwen has a variety of models, including small dense ones, which require less skill and set up.

After custom post-training, these models run on rented hardware. Currently, Baseten serves many these small, custom models. Typical targets include Salesforce and AWS Terminal and creating or closing Jira tickets. It is also possible to get models to be reliable at using MCPs, for example to extract data from SEC filings.

These RL as a service startup are joined by the labs, with OpenAI recently spinning up a “Reinforcement Fine Tuning” (RFT) service. OpenAI RFT’s goal is to let any customer with sufficient data RL an OpenAI model so it is tuned to the customer’s tasks and domains.

In practice, the service has fallen short. We believe it is unstable and too expensive for most customers. As such, we are seeing demand for these services mostly flow to young startups. These young, YC companies do not have strong margins. Indeed, they often lose money. However, they are able to serve users at 5x less compared to what it would cost on OpenAI’s platform, gaining market share.

In the longer term, this will change. OpenAI’s is targeting large enterprises who can spend millions, and in the aggregate, the labs will capture most of the revenue. For OpenAI, this will be done through the “Strategic Deployment” team, whose goal is to work directly with a customer to build custom models. OpenAI was early to bet on this service as an enterprise use case, and **enterprise** growth outpaced consumer in 2025 for the company.

![](https://substackcdn.com/image/fetch/$s_!kiYf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc103b69d-c1f2-4a3e-8780-abd93fb63602_1040x995.png)

Source: OpenAI

Anthropic is also entering the game. We believe Anthropic has its own RFT-like service that is more stable and more sample-efficient than OpenAI’s. Anthropic might expose it through the API, but is also actively hiring “Forward Deployed Engineers,” as OpenAI does, presumably serving the same function as the strategic deployment team at OpenAI.

Anthropic is bringing on large volumes of Trainium, which is economically attractive for RL in part due to low $/HBM. HBM generally contributes a large part of the chip’s BOM, but Amazon sourced it directly, reducing costs. RL workloads are mostly inference, which is memory bound. This means having a low TCO chip like Trainium positions customers in a place to make strong margins off this service if they optimize the throughput a sufficient amount.

* [Amazon’s AI Resurgence: AWS & Anthropic's Multi-Gigawatt Trainium Expansion](https://newsletter.semianalysis.com/p/amazons-ai-resurgence-aws-anthropics-multi-gigawatt-trainium-expansion) - Jeremie Eliahou Ontiveros, Dylan Patel, and 2 others · September 3, 2025

As noted, there is substantial upside in training custom models. One area in which we are particularly excited about is scientific discovery, within which custom models can make large amounts of progress.

RL as a service is also offered by a number of other companies such as ThinkingMachines Tinker as well as Applied Compute and Adaptive ML. All three have more success then OpenAI and Anthropic so far in this market.
