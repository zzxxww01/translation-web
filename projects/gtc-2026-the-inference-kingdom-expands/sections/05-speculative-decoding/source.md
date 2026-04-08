A different way LPUs could improve decode phase latencies is by accelerating a speculative decoding setup, where we deploy draft models or Multi-Token Prediction (MTP) layers onto LPUs.

For a decoding step of context N tokens, adding k additional tokens during forward pass (a warm prefill of k new tokens) marginally increases the latency when k << N. Using this property, speculative decoding uses a small draft model or MTP layers to predict k new tokens, saving time since small models have lower latency per decode step. To verify the draft tokens, the main model only needs one warm prefill of k new tokens, at the latency cost of roughly a single decode step. Speculative decoding usually boosts output token per decode step by 1.5 to 2 tokens, depending on the draft model / MTP accuracy. With its low latency capabilities, LPUs can further increase the latency savings and improve throughput.

![](https://substackcdn.com/image/fetch/$s_!cvnL!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4b9a77e7-dc29-4321-8f63-1c508cebc7e5_1335x671.jpeg)

Source: SemiAnalysis

For LPUs, deploying a draft model or MTP layers is quite different from applying AFD. FFNs are stateless, while draft models and MTP layers require dynamic KV cache loading. Each FFN is around hundreds of megabytes, whereas draft models and MTP layers take up tens of gigabytes. To support this memory usage, LPUs can access up to 256 GB of DDR5 per Fabric Expansion Logic FPGAs on the LPX compute tray.
