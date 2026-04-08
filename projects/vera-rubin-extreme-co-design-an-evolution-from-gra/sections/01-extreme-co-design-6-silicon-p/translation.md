https://substackcdn.com/image/fetch/$s_!ZQyU!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7cdeb372-67f9-4140-889e-2f8f493cda0a_1984x1141.png

来源： SemiAnalysis, Nvidia

相较于GB200，鲁宾的密集FP4和FP8 FLOPS提升了约3.5倍，而FP16 FLOPS的增长则较为温和，约为1.6倍，这突显出英伟达继续将FP4/FP8作为主要的扩展路径。在内存方面，其HBM容量与GB300持平，而HBM带宽的提升则更为激进，达到约2.8倍。总体而言，该架构优先侧重于带宽与低精度计算。

https://substackcdn.com/image/fetch/$s_!m2IG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6e9330b4-7407-4dcb-8a2b-fb323371ffba_2218x1210.png

来源： SemiAnalysis, Nvidia

### 鲁宾

https://substackcdn.com/image/fetch/$s_!u2L6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbe50555c-6427-42ca-b58e-97716f2558c9_4800x2700.png

来源： Nvidia

鲁宾的设计是布莱克威尔合乎逻辑的演进，它转向了3纳米工艺，并将I/O拆分为芯粒，同时保留了两颗光罩极限尺寸（reticle-sized）裸片搭配8栈HBM的相同基本结构。其35 PFLOPS的密集FP4算力相比布莱克威尔GB200提升了3.5倍，具体通过以下方式实现：

- 将流式多处理器数量从160个增加至224个

- 将流式多处理器中的张量核心宽度翻倍，达到每时钟周期32768个FP4 MAC

- 将时钟频率提升25%，从1.90GHz增至2.38GHz

此外，英伟达声称，通过采用更新的第三代Transformer引擎（取代了前几代架构中的2:4结构化稀疏），其FP4有效性能最高可达50 PFLOPS。我们将在下文详细剖析鲁宾的这一架构特性。

值得注意的是，张量核心宽度的翻倍仅适用于 FP4 和 FP8，而 BF16 和 TF32 的规格与布莱克威尔保持一致，这导致其性能仅提升至布莱克威尔的 1.6 倍。这一架构决策反映了英伟达的判断：大多数训练和推理工作负载将从 TF32 和 BF16 转向 FP8 和 FP4。

在内存方面，升级至 HBM4 意味着每个堆叠的总线宽度翻倍，运行速率达到 10.8 GT/s，从而实现 22TB/s 的总带宽；在与 GB300 保持相同 288GB 容量的情况下，其带宽达到了布莱克威尔的 2.75 倍。相比 GTC 2025 上最初公布的 13TB/s，内存带宽已得到显著提升。为了追赶 AMD MI450 的内存带宽，英伟达向 DRAM 供应商提出了更高的 HBM4 引脚速率要求，这远超 JEDEC 规范中的 HBM4 速率标准。

尽管英伟达的目标是 22TB/s，但据我们了解，内存供应商在满足英伟达的要求时正面临挑战，因此我们认为首批出货的带宽很可能会略低一些，更接近 20TB/s。我们已经向加速器与 HBM 模型的订阅用户深入探讨了这对SK海力士、三星和美光的影响。美光已远远落后于三星和SK海力士，我们认为他们实际上已在鲁宾 HBM4 的竞争中出局。我们在加速器与 HBM 模型中提供了关于验证测试和引脚速率的更多细节。

NVLink-C2C 芯粒内置了用于连接维拉 CPU 的 SerDes，其带宽翻倍至 1.8TB/s；而在芯片的另一端，尺寸更大的 NVLink 6 芯粒则配备了 36 条定制的“400G”SerDes 链路，为所有 72 颗鲁宾 GPU 提供翻倍的 NVLink 带宽。

晶体管数量攀升了60%，达到3360亿。

值得注意的是，鲁宾并未提及稀疏FLOPS。在前几代产品中，2:4结构化稀疏曾被用来让营销宣传中的FLOPS数值翻倍。然而，该技术的实际采用率极低，尤其是在低精度运算下，因为这种僵化的稀疏结构会强制将一半的数值归零，从而导致精度损失。程序员基本上无视了结构化稀疏，因为它缺乏实用性，这也进而促使硬件设计发生了转变。布莱克威尔Ultra GB300将密集FP4算力提升了50%，同时保持稀疏FP4 FLOPS不变；而AMD的MI355X则为了节省芯片面积，停止在MXFP8、MXFP6和MXFP4格式上支持结构化稀疏。

鲁宾架构改进版Transformer引擎中的自适应压缩引擎是一项关键特性。它能够在运算过程中实时动态计算稀疏性，剔除数据流中的零值而不强行将非零值归零，从而重新提升天然具备较高稀疏度的推理性能，在保持模型精度的同时实现性能提升。这一过程在基于布莱克威尔架构构建的现有模型上可自动实现，无需引入新的编程模型或进行特定优化。尽管采用训练后量化或量化感知训练的模型可以通过微调来最大化自适应压缩的加速效果，但这并非享受动态压缩红利的硬性前提。

这意味着工作负载越稀疏，性能就越接近宣传的50 PFLOPS峰值性能。因此，英伟达将50 PFLOPS这一数字宣传为FP4推理性能，而35 PFLOPS的FP4训练数据则对应密集型工作负载。由于精度得以保持，这让营销团队能够宣称鲁宾的FLOPS达到了GB200的5倍——这是将50 PFLOPS的动态压缩FP4与10 PFLOPS的密集FP4进行对比得出的结论。实际的GEMM性能能否达到50 PFLOPS，取决于张量中包含多少个零值。零值越多，性能就越接近该峰值；张量中的零值越少，加速幅度就越小。总的来说，得益于自动化实现的优势，我们预计鲁宾的自适应稀疏压缩将比结构化稀疏获得高得多的实际采用率。

话虽如此，许多机器学习系统工程师仍对这种新型稀疏性能否取得良好效果持怀疑态度，并且英伟达宣称的50 PFLOPS极有可能像前几代产品一样，纯粹是营销噱头。

鲁宾的芯片级TDP最高增至2300W，而布莱克威尔为1000至1400W。供应链传闻称，存在两款功耗与性能规格不同的“SKU”：2300W的Max-P版本和1800W的Max-Q版本。然而，这并非两款不同的硬件SKU，而是英伟达根据用户的工作负载需求提供的两种默认功耗配置。英伟达认为，Max-Q能提供最佳的每瓦性能。Max-P则能提供最高的绝对性能，但这会带来效率损失。运行Max-P设置会导致机架功耗增加20%，但性能提升幅度却远不及这20%的功耗增幅。

这些功耗配置均由软件管理。用户还可以根据自身需求，任意设定最大功耗（只要单颗GPU不超过2300W即可），这一点在历代GPU中也一向如此。多家超大规模云厂商和实验室已选择在较低功耗下运行其GPU，以此来优化每瓦性能，并兼顾供电能力的限制。

https://substackcdn.com/image/fetch/$s_!tbcG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F61396626-3359-4a08-8dfa-58f7ed911443_2012x1118.png

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

在鲁宾封装的机械结构方面也进行了升级，加入了升级版的均热盖与加强环。相比之下，布莱克威尔B200和B300封装仅配备了均热盖。均热盖能够让散出封装的热量分布得更加均匀，同时也能为封装提供机械支撑，从而防止发生翘曲。

对于鲁宾而言，其均热盖是一个由两块独立盖板组成的模块。除了均热盖之外，封装结构中还加入了加强筋，以提供更强的机械支撑，从而避免发生翘曲。均热盖的表面还将覆盖一层电镀金。此举旨在防止液态金属第二层热界面材料引发腐蚀，该材料位于均热盖与冷板之间。

### 维拉

https://substackcdn.com/image/fetch/$s_!XgXK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb0795695-2bda-4134-a982-12e59acc76f9_3000x3040.jpeg

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

英伟达在CPU领域采取了激进的策略，维拉的性能较Grace实现翻倍，这得益于其采用了3纳米光罩极限尺寸的计算裸片，并将内存控制器与I/O拆分为独立的芯粒。核心数量从72个增加至88个，裸片上实际光刻了91个核心，旨在通过预留冗余来提升良率。这些核心标志着英伟达定制化ARM CPU设计的回归，其“Olympus”核心现已支持SMT多线程技术，总处理线程数达到176个。L3缓存容量也提升了40%，达到162MB。内存总线位宽翻倍至1024-bit，速率提升至9600MT/s，从而实现了2.5倍的带宽；同时，借助8个SOCAMM模块，最大内存容量增至三倍，达到1.5TB。与鲁宾GPU相连的NVLink-C2C带宽同样实现翻倍，达到1.8TB/s。此外，该架构现已支持PCIe6与CXL3.1标准。

这一切使得晶体管数量增至原来的2.2倍，达到2270亿个。

### NVLink 6 交换机

https://substackcdn.com/image/fetch/$s_!p8aL!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F722c91c0-0b9e-43c6-9ca6-76714eb7fa70_3000x3048.jpeg

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

尽管机架级交换带宽翻了一番，但每个机架内的 NVLink 交换机芯片数量也随之翻倍至 36 颗，如今每个交换机托盘可容纳 4 颗交换机芯片。这意味着全新的 NVLink 6 交换机芯片与 NVLink 5 交换机一样，维持了 28.8T 的总带宽，其端口数量减半，但得益于采用“400G”双向 SerDes，单端口速率实现了翻倍。这种方案使得高带宽交换机能够继续维持单片裸片设计，从而降低了设计复杂度。芯片布局与英伟达此前的交换机保持一致：两侧为 I/O 接口，中央逻辑区域则是交叉开关以及算力达 3.6 TFlop 的 SHARP 网内计算加速模块。

### ConnectX-9

https://substackcdn.com/image/fetch/$s_!so7W!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcb34a228-9fff-45eb-8851-68a1d54acf66_1781x1780.jpeg

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

ConnectX-9 主要是 ConnectX-8 的迭代升级，保留了相同的 800G 网络带宽和 48 通道 PCIe6 交换能力。不过，CX-9 现在采用 4x200G PAM4 SerDes 来支持 800G 以太网，而此前的 CX-8 仅在 InfiniBand 架构下支持该速率。在鲁宾平台上，英伟达将单颗 GPU 配置的网卡数量翻倍，从而实现了两倍的横向扩展带宽。

### BlueField-4

https://substackcdn.com/image/fetch/$s_!Wfwi!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F60828488-61bb-416d-a9c8-df3e8fe3c284_2506x1673.jpeg

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

BlueField-4 的设计路线与 BlueField-3 截然不同。英伟达并未选择将计算与网络功能集成进行定制流片，而是直接复用其大型 Grace CPU 裸片，将其与 ConnectX-9 裸片进行共封装，从而打造出一款具备海量算力的 800G DPU。128GB 的 LPDDR5 内存为该 Grace CPU 提供数据，其带宽为标准版 Grace 的一半。这一内存容量达到了 BlueField-3 的 4 倍。此外，BlueField-4 还可兼作存储控制器，每个上下文内存存储系统中均配备了四颗 BF-4 芯片。

### Spectrum-6

https://substackcdn.com/image/fetch/$s_!qbIl!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2e1932aa-e7cf-438e-bc2a-984a03d9cd25_3000x2983.jpeg

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

尽管 Spectrum-6 CPO 并非鲁宾 NVL72 机架的一部分，但它凭借翻倍的基数，能够支持更大规模的横向扩展集群。该设计保留了与 Spectrum-5 相同的特性，由 8 个 IO 芯粒环绕主交换芯片构成。通过 512 个 200G SerDes 实现了 102.4T 的交换带宽。封装上的 32 个 3.2T 光引擎将这些电信号转换为光链路，每个引擎均配有可拆卸的光纤连接器。SN6810 搭载了一颗该芯片，而 SN6800 则内置四颗，通过多路复用构建出一个 409.6T 的交换机盒。此外，SN6600 还将提供一款带有可插拔 OSFP 笼子的非 CPO 版本。在我们看来，非 CPO 版本将会更为普及。
