张量内存加速器 (TMA)（Tensor Memory Accelerator (TMA)）（PTX 指令：cp.async.bulk.tensor，SASS 指令：UTMALDG）是 Hopper 架构引入的异步数据拷贝引擎，专门用于将大量数据从全局内存搬移至共享内存 (SMEM)。单个线程即可启动 TMA 执行地址生成、地址重组与越界处理，从而释放其他线程去执行独立任务。在此，我们对 2D 张量版本 (cp.async.bulk.tensor.2d) 进行基准测试，以代表典型的 TMA 用法。

参考 FlashInfer 注意力算子，我们对 TMA 进行了基准测试：每个 SM 仅分配 1 个 CTA，但每个 CTA 启用 1 到 4 个 warp，并从中各取 1 个线程来发射不同 box 尺寸的 TMA 指令。下图展示了在不同飞行中字节数下的最佳吞吐量。

我们使用以下配置对 TMA 进行基准测试：

- 每个 SM 的 CTA 数量：1

- 每个 CTA 的线程数：128（4 个 warp）

- TMA box 尺寸：2D 形状，从 32x8 递增至 128x128

https://substackcdn.com/image/fetch/$s_!IhCY!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7a47a042-7c59-4cc1-8459-665852a23321_1600x720.png

与 LDGSTS 相比，TMA 需要大得多的数据量才能达到峰值吞吐量。
