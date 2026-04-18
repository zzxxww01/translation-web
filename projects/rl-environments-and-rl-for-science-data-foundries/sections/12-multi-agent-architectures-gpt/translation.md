一个具备扩展潜力的领域，是将不同模型结合起来，共同思考以解决单一问题。从高层次看，这正是 Grok 4 Heavy、Gemini Deep Think 和 GTP5-Pro 的工作原理。

https://substackcdn.com/image/fetch/$s_!zfNX!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F99c932f8-16e6-41c1-979d-4fecbe893678_1012x717.png

来源：xAI

在实践中，具体细节可能有所不同。例如，汇总不同智能体的答案可以采取一些基础方法，比如选择最常见的答案；也可以让模型之间相互商议以选定一个答案；或者让一个单独的模型阅读所有答案并做出选择。我们预计，许多即将推出的产品将采用更复杂的多智能体架构。

此类系统中第一个进入主流视野的案例是谷歌的 AlphaEvolve，它将多个扮演不同角色的智能体锁定在一个循环中。在这个具体架构中，包含采样模型（负责从包含先前已发现问题解决方案的数据库中组装提示）、集成模型（负责生成新的、改进的解决方案）以及验证系统（负责核实答案）。

这些组件被串联在一个进化循环中，其输出结果持续由验证器进行检查。当针对特定问题的解决方案相对于现有最优方案取得特定改进后，或者当额外循环带来的收益递减时，该循环即告终止。

https://substackcdn.com/image/fetch/$s_!gQcy!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F67410dcd-d8ca-42d6-a63b-07d6ca923eb6_878x695.png

来源：AlphaEvolve，Google

自那时起，各种架构层出不穷，其中一些专为特定评估任务设计。例如，研究员 Jeremy Brennan 利用基于 Grok 4 构建的多智能体架构，在 ARC-AGI 基准测试中创下纪录。其方法其实相当简单：先由 Grok 4 为每项任务生成指令，再由另一智能体在训练示例上测试这些指令。若出现完美解决方案，则锁定并应用于预留测试集；否则，便进入迭代优化循环。

https://substackcdn.com/image/fetch/$s_!8kGI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F662d0269-0b70-451e-b252-2c3b1d96a4c2_937x611.jpeg

来源：Jeremy 提交时的 ARC-AGI 排行榜。

另一些架构则仅使用子智能体。例如，4 个独立的 o4-mini 子智能体在现有的生产级 SGLang 内核上平均实现了 1.3 倍的加速。具体而言，现有的 CUDA 内核从 SGLang 中抽取出来进行独立评估。随后，它通过四个智能体之间的循环进行处理：第一个智能体进行测试，以通过或失败为基础验证内核；第二个智能体进行详细性能剖析，以识别性能差异；第三个智能体规划有针对性的编辑；第四个智能体则负责实施这些编辑。

https://substackcdn.com/image/fetch/$s_!DD3G!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F45e34ae7-126b-4c3b-ab59-3675c36c5e3b_1258x603.png

来源：Wei 等人

值得注意的是，这并不必然要求模型能力本身的提升。尽管推理成本显著增加，但这些智能体所能解决问题的价值，超过了运行它们的成本。在科学和编程等领域，这一点尤其明显。

有些方法甚至报告了任务成本的降低，例如递归语言模型。在这种情况下，一个编排器在整个任务过程中递归地调用其他模型。这些系统在长上下文评估中表现出极高的性能，因为上下文可以巧妙地分配在子智能体和编排器之间。

OpenAI 正在积极探索自我对弈等理念，并将 AlphaGo 的原理引入 LLM；我们认为他们是这一特定领域的领导者。AlphaGo（及其后续版本AlphaZero）的独特之处在于，它通过自我对弈而非与人类对弈，在围棋（以及后来的国际象棋等游戏）上实现了超人的性能。

当前的LLM系统还相当初级，原则上与在单一循环中运行的模型并无本质区别。但这在实践中已足够强大：Claude Code这项年经常性收入达十亿美元的产品，其核心不过是用简单思路拼凑出一个更自主的智能体。然而，重要的是展望当更复杂的多智能体协作投入生产时，系统能力将呈现何种面貌。

改进的智能体协作架构同样将释放 LLM 处理越来越大型项目的能力。从原理上看，这与人类能够通过团队协作完成比个人单独工作更庞大的项目并无太大不同。
