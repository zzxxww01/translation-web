我们对单条 MMA 指令的延迟进行了基准测试，并将对比结果绘制如下。在所有配置中，延迟在 N=64 到 128 之间均呈线性增长；N=256 时的延迟激增，很可能是由于 N 值从 128 直接跨越到 256 造成的。具体到各个协作线程阵列 (CTA) 组的 MMA，在 1SM MMA 中，无论 N 值大小，M=64 和 M=128 的延迟都非常接近；而在 2SM MMA 中，M=256 的延迟增长速度略快于 M=128，这与我们的理论估算相符。对比不同数据类型可以发现，1SM MMA 在数据类型间的延迟差异微乎其微，但 2SM MMA 则表现出明显的分化。

https://substackcdn.com/image/fetch/$s_!21tK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6a0575f8-c15a-4688-943c-2331a0a753ce_1600x695.png

我们注意到，各类数据类型的延迟排序呈现出一个微小但高度一致的规律：

> S8 < BF16 = E4M3 = F4 < MXF8 = MXF4

我们认为，整数运算具备更高的能效，因此 S8 的速度最快；而比例因子计算则给 MXF8 和 MXF4 带来了少量的额外开销。

https://substackcdn.com/image/fetch/$s_!8pOu!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4812fa68-0ae7-40d9-920c-2eb1f55b2d51_1600x1020.png
