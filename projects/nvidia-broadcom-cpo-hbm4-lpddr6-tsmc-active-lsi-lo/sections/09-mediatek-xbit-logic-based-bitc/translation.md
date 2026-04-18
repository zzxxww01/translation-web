https://substackcdn.com/image/fetch/$s_!m8pd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa42110ab-a204-4a5f-8977-830bd38e06ea_1283x461.jpeg

SRAM高电流存储单元密度与基于逻辑的多位触发器的跨节点对比。来源：联发科，ISSCC 2026

https://substackcdn.com/image/fetch/$s_!NbiN!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fda693b39-6780-47ce-ac48-bf8a5b5a489f_2880x1620.jpeg

SRAM存储单元微缩的局限性：面积与电压约束。来源：联发科，ISSCC 2026

SRAM微缩已死。 尽管逻辑面积从N5到N2减少了40%，但8晶体管高电流SRAM存储单元的面积仅减少了18%。6晶体管高电流（6T-HC）存储单元的情况更糟，仅减少了2%。辅助电路的微缩效果更明显，但这并非免费的午餐。

众所周知，N3E的高密度存储单元相比N3B有所倒退，其密度回落到了N5的水平。在这篇论文中，联发科揭示了高电流存储单元的情况。N3E的高电流存储单元面积相比N5增加了1-2%，其密度则从约39.0 Mib/mm²降至约38.5 Mib/mm²。需要指出的是，这些数据并未计入辅助电路的开销。

https://substackcdn.com/image/fetch/$s_!_Cbb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe8879827-c259-4dfd-a9ae-79a59dbfc37d_2880x1620.jpeg

8晶体管存储单元在逻辑规则下的NMOS/PMOS布局挑战。来源：联发科，ISSCC 2026

https://substackcdn.com/image/fetch/$s_!oxdV!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd4abf3fe-77e4-4333-a1c8-da1eeedb5789_2520x1408.jpeg

联发科10晶体管xBIT平衡型存储单元电路设计。来源：联发科，ISSCC 2026

在现代逻辑工艺节点中，6晶体管存储单元包含4个NMOS和2个PMOS晶体管，而8晶体管存储单元则分别包含6个和2个。NMOS与PMOS晶体管数量不相等，这需要特殊的布局规则，从而降低了版图效率。联发科的新型存储单元是一个10晶体管单元，命名为xBIT，其构成为4个NMOS和6个PMOS晶体管，或者反之亦然。这两种变体的存储单元可以组合排列成一个矩形块，包含20个晶体管，存储2比特数据。

https://substackcdn.com/image/fetch/$s_!n1LG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa550e975-e262-4350-8c6f-380c90b3ae01_2520x1408.jpeg

xBIT与晶圆代工厂8晶体管存储单元密度及功耗对比。来源：联发科，ISSCC 2026

与工艺设计套件中的标准8晶体管存储单元相比，xBIT的密度提升了22%至63%，在字线宽度较低时增益最大。功耗也得到显著改善，平均读写功耗降低了30%以上，在0.5V电压下漏电降低了29%。在0.9V电压下，其性能与8晶体管存储单元相当；在0.5V电压下，其速度虽比8T存储单元慢16%，但已足以避免成为处理器瓶颈，且其工作电压范围足够宽，适用于电压频率调节。

https://substackcdn.com/image/fetch/$s_!xu_9!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6f2a3a1a-a796-4979-8477-fab6bf41c58d_1699x1094.jpeg

xBIT舒姆图。来源：联发科，ISSCC 2026

联发科还展示了xBIT存储单元的舒姆图，其工作频率可从0.35V电压下的100MHz，提升至0.95V电压下的4GHz。

我们将在后续的通讯文章中，对SRAM及其微缩化影响因素进行深入探讨。
