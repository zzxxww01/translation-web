一个更有趣的问题是：预训练本身还重要吗？如果将智能体比作 TCP/IP 协议，那么优化协议中的数据包（packets），其重要性可能远不如优化协同功能。Kimi 2.5 就是一个例证。该版本发布中最引人注目的信息，并非其顶尖的基准测试性能，而是其智能体编排能力。

今年发布的每一个增量模型，都将更侧重于智能体编排及性能，这与去年业界对推理能力的追逐如出一辙。随着 Anthropic 超越了单纯的基准测试，仅仅比较模型间的性能已无意义，未来的关键在于智能体协同能达成何种成就。OpenAI 可能因此被打了个措手不及，错失了这一战略拐点。正如 Anthropic 和 Gemini 最初未能完全理解或推动 RL 和思维链的变革一样，现在看来，Anthropic 正引领着智能体化的拐点。

月之暗面 (Moonshot AI) 的 Kimi 2.5 完美展示了未来模型的形态。Kimi 将全部精力集中在编排层上。在 Kimi 2.5 的发布中，除了智能体编排层，其他所有部分都已开源。其并行智能体强化学习 (PARL) 技术预示了未来的发展方向。根据内部基准测试，通过运用智能体，Kimi 的性能表现已超越 Opus 4.5。例如，Sonnet 5 的设计显然也面向智能体集群，其工作方式与 Kimi 2.5 的 PARL 技术颇为相似。

Kimi 2.5 全新的编排引擎（未开源）

https://substackcdn.com/image/fetch/$s_!fOEe!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffce483cf-4a0a-4291-b937-6650a5ed848c_1191x646.png

来源：Kimi 论文

https://substackcdn.com/image/fetch/$s_!psG2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2260d62d-0cce-4be8-9cb6-e50fdf9dae6f_1183x627.png

来源：Kimi 2.5

智能体编排就是新的 CoT。智能体（指能够自主规划并执行复杂任务的 AI）的大规模并行化将成为下一代核心能力，其作用逻辑与更长的思维链 Token 带来更优结果如出一辙。很快，系统将大规模生成成群结队的智能体大军，以完成各项任务！

https://substackcdn.com/image/fetch/$s_!kH7c!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F67c9c93f-d03a-4dd6-8d5a-30b0c61bb846_1191x688.png

来源：Kimi 2.5

这一前沿阵地潜力巨大，堪比最初 o1 模型实现的性能飞跃。但这是第一次，领跑者不再是 OpenAI。

然而，在为智能体无限扩展感到兴奋之前，有一个问题必将成为今年真正的竞争焦点。Anthropic 在近期研究中发现：“在所有任务和模型中，模型花费在推理和执行动作上的时间越长，其表现就越语无伦次。无论我们衡量的是推理 Token、智能体动作还是优化器步数，这一结论都成立。”

模型的重度用户也反馈了同样的情况，本文作者也基本认同这一观点：更长的上下文窗口最终会退化为语无伦次的输出。

https://substackcdn.com/image/fetch/$s_!YQxQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcbc120a1-eddc-42f4-b5ef-100791815e28_997x633.png

来源：Anthropic

这凸显了 Anthropic 在 token 效率方面的优势。这也解释了为什么我们认为，用最少的 token 完成任务将成为核心的质量基准之一。单一上下文窗口内的连贯性越强，智能体（指能够自主规划并执行复杂任务的 AI）的扩展空间就越大。模型层面的 token 效率很可能将揭示谁才是真正的领跑者。

然而，在 Claude Code 强势崛起之际，制约 Anthropic 的是 FLOPS 和电力（MW），而非模型能力。这种非消费者驱动的新一轮需求爆发，是 2026 年值得关注的关键拐点。用户增长加速必然带来计算需求飙升。我们认为，Anthropic 即将达成的 3500 亿美元估值，将为其大规模进军吉瓦（GW）级电力博弈提供充裕资金。下图展示了 Anthropic 正在推进的电力追赶态势。

https://substackcdn.com/image/fetch/$s_!7xxX!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7572d353-1443-483a-a286-4cb33d1413f9_927x585.png

来源：SemiAnalysis [Tokenomics 模型](https://semianalysis.com/tokenomics-model/)

Anthropic 正是凭此制胜。但现在轮到 OpenAI 向世界证明，他们能够预训练出新模型，并有望重夺领跑地位。这场竞赛似乎比去年更具悬念，我们对持续变革的步伐感到兴奋。

在文章最后，我们将分享 SemiAnalysis 团队与我们的新晋霸主 Claude Code 共同完成的一些信息处理工作。眼见为实。我们笃定自己正处于一个全新时代：在这个时代，创建软件和处理信息的边际成本已降至零。从此刻起，事物变革的速度将不断加快。
