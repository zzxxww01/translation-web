尽管 AMD 在单节点 FP4 上的表现还算过得去，在 FP8 分布式推理上也与运行 SGLang 的 B200 有一战之力，但目前 AMD 开源推理软件栈的症结在于：虽然各项独立的推理优化跑起来不错，但真实客户在部署时往往会将多种优化组合使用。顶尖 AI 实验室都在同时启用 FP4、分离式推理以及宽专家并行，而这正是 AMD 翻车的地方。

SemiAnalysis 是一款免费开源软件且由读者支持。为了接收新文章并支持我们的工作，请考虑成为免费或付费订阅者。

AMD 的软件依然不达标。SemiAnalysis 和 AMD 内部的理论极限性能建模 (Speed of Light) 均表明，在 FP4 精度下，结合宽专家并行的分离式推理，其性能理应优于 MI355X 的单节点推理。遗憾的是，软件依然是掣肘 AMD GPU 的巨大瓶颈。AMD 管理层必须进一步优化工程人才的资源配置，例如，把工程资源从 ATOM 这种根本没人用的单节点自嗨项目中撤出，转而集中精力解决上述分离式推理、宽专家并行与 FP4 之间推理优化的可组合性问题。

目前软件表现拉胯，归咎于缺乏重点，以及未能准确把握行业现状而导致优先级错乱。所有顶尖实验室都已用上了分离式推理和宽专家并行；AMD 必须停止死磕单节点，将核心精力重仓投入到开源解决方案的多节点推理上。

在开源分布式推理、宽专家并行以及 FP4 的可组合性方面，AMD 已经落后了半年多。这点从英伟达和 SGLang 团队在六个月前就已大秀其在 DeepSeek 上的 NVFP4 性能中便可见一斑。

https://substackcdn.com/image/fetch/$s_!IGhQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Feddd9541-ed5a-4e49-aab2-291d49fd7e68_2132x1252.png

来源：SemiAnalysis InferenceX
