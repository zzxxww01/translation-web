FlashInfer 等深度学习内核库在加载数据时会同时使用 TMA 和 async copy。TMA 和 async copy 具有不同的性能特征：TMA 擅长处理具有规则访存模式的大数据量加载，但延迟较高；而 async copy 能够处理不规则的访存模式，但存在数据量限制。我们将说明在何种条件下应如何取舍。在此，我们对 FlashInfer 在 MHA 和 MLA 内核中使用的配置进行了基准测试。

从吞吐量来看，当飞行中数据量小于 32 字节时，async copy 略微优于 TMA，但 TMA 随后便会赶上，并能继续扩展至 128 KiB。从延迟来看，在飞行中数据量达到 12 KiB 之前，async copy 的延迟略低于 TMA，但超过该数据量后，TMA 的延迟会大幅增加。

https://substackcdn.com/image/fetch/$s_!mtqT!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F74e024c1-60ab-44e4-8acb-69760e4fcba2_1600x678.png

https://substackcdn.com/image/fetch/$s_!ax25!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F838e8420-6671-4ffe-afdd-66c2581ada03_1600x677.png

在实际应用中，Blackwell MLA 内核使用 async copy 进行动态页面加载，而其 MHA 内核仅使用 TMA。FlashInfer 的 Blackwell MHA 内核大多由 TRT-LLM 贡献，因此我们只能通过分析二进制文件来推测这些内核的具体行为。我们发现，与 Hopper 类似，所有 Blackwell TRT-LLM 内核均使用 TMA。我们推测，在动态页面加载方面，这些内核沿用了 Hopper 内核的机制：使用 4D TMA 并将页面索引作为最后一个维度，在需要时对 TensorMap 对象进行索引。为了明确这些内核的确切运行机制，我们呼吁英伟达开源 FlashInfer TRT-LLM 内核，以造福社区。
