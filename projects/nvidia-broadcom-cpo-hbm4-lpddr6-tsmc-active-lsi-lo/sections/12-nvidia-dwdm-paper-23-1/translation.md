光学信号格式的选择将影响纵向扩展（scale-up）共封装光学（CPO）产品的上市时间表。英伟达正在加速生产其COUPE光学引擎，该引擎支持每通道200G PAM4，旨在短期内用于横向扩展（scale-out）交换。

https://substackcdn.com/image/fetch/$s_!gqo1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa1a30ce9-0d17-45f9-9e83-026ba5f0a876_2880x1620.jpeg

英伟达DWDM架构概览。来源：英伟达，ISSCC 2026

然而，在ISSCC上，英伟达提出了使用每波长32 Gb/s的方案，并通过DWDM复用8个波长。第9个波长以半速率（即16 Gb/s）用于时钟转发。

时钟转发意味着可以通过移除时钟数据恢复（CDR）电路以及其他相关电路，使串行器/解串器设计在一定程度上得以简化，从而提升能效和芯片海岸线（shoreline）效率。

早在今年三月，恰在OFC 2026之前，光学计算互连多源协议（OCI MSA）宣布成立，该协议将专注于200 Gb/s双向链路，其发送和接收均采用4个50G NRZ波长，并通过同一根光纤双向传输。是不是有人提到了OCS？

https://substackcdn.com/image/fetch/$s_!Eh4Q!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F62c2c764-5aab-4981-aedc-1e6ba3864cf4_2869x1869.jpeg

OCI MSA 光学链路规格。来源：[OCI MSA](https://oci-msa.org/)

有趣的是，光学计算互连多源协议（OCI MSA）并未使用额外的波长进行时钟转发。这似乎表明，将所有波长保留用于实际数据传输是其优先考虑的事项。

英伟达已发表的关于纵向扩展（scale-up）共封装光学（CPO）的研究大多集中在密集波分复用（DWDM）技术上。然而，当今的CPO光学引擎主要围绕200G PAM4 DR光学构建，这更适合横向扩展（scale-out）网络。OCI MSA围绕DWDM制定纵向扩展光学标准，正好化解了这一矛盾。现在情况已很明确：英伟达及其他厂商将主要采用DWDM进行纵向扩展，而采用DR光学进行横向扩展。

OCI MSA还展示了不同的实现方案：一种是板载光学（OBO），另一种是通过基板集成在专用集成电路（ASIC）封装上的CPO版本，以及第三种将光学引擎直接集成在硅中介层上的版本。中间图（b）所示的实现方案，在未来几年内将是用于纵向与横向扩展CPO的最常见方案。不过，该方案仍需要某种形式的串行化链路来穿过ASIC基板，并且两端仍需要某种形式的串行器/解串器（SerDes）。例如，UCIe-S协议就可以用于此类传输。

https://substackcdn.com/image/fetch/$s_!r0uo!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F02eb01f6-1c42-4388-b07d-744346a1d768_2262x1962.jpeg

光学引擎集成层级（板载光学、基板CPO、中介层CPO）。来源：[OCI MSA](https://oci-msa.org/)

实现共封装光学（CPO）的“终极挑战”，在于将光学引擎直接集成到硅中介层上，并如上图（c）所示，通过并行化的裸片到裸片（D2D）连接与专用集成电路（ASIC）相连。这有望显著提升海岸线带宽密度，实现更高的端口数（radix），并改善能效。因此，这种实现方案能以其他方案无法企及的方式释放CPO的优势。但要实现它，仍需数年时间，并依赖于先进封装技术的进一步发展。
