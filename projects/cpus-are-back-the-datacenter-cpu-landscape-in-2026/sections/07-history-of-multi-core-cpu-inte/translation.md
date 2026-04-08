要理解 2026 年 CPU 的设计变革与理念，必须先弄清多核 CPU 的工作原理，以及互连架构随核心数量增长的演进历程。既然有多个核心，自然需要将它们连接起来。2005 年问世的早期双核设计（如英特尔的奔腾 D 和至强 Paxville）仅仅是两个独立的单核。核心间通信必须在封装外部进行，数据通过前端总线 (FSB) 传至北桥芯片，而北桥芯片同时也搭载了内存控制器。

同样在 2005 年推出的 AMD 速龙 64 X2 则算得上是真正的双核处理器。它将两个核心与集成内存控制器 (IMC) 集成在了同一块裸片上。这使得核心之间、核心与内存及 IO 控制器之间，能够通过片上 NoC（片上网络）数据网络直接在芯片内部进行通信。

https://substackcdn.com/image/fetch/$s_!BLWt!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3fc1fbd3-39c1-4650-ab74-54f841f233fc_2329x1801.png

英特尔 Tulsa 裸片图。来源：英特尔，Hot Chips 2006

英特尔随后的 Tulsa 处理器配备了由两个核心共享的 16MB 三级缓存，该缓存同时充当片上的核心间数据网络。后文将会看到，随着核心数量飙升至数百个，这些片上数据网络将成为数据中心 CPU 设计的关键因素。
