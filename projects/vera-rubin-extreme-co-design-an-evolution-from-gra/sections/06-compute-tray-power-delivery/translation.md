在计算托盘层级，50VDC电力通过机箱后部的汇流排夹进入计算托盘。随后，电力通过内部汇流排线缆传输至机箱中部。从内部汇流排线缆开始，供电路径被分流至三个目的地。第一和第二条路径分别通向左右两侧的Strata Board，由内部汇流排线缆直接向其输入50VDC电力。第三条路径则通向机箱前部的配电模块。内部汇流排线缆会将50VDC电力输送至一个走线于PCB中板下方的汇流排装置，进而连接至PCB中板另一侧的电源分配板（PDB）。这与Grace 布莱克威尔的设计不同，后者的50VDC电力是直接输入PDB的。

随后，电源分配板向计算托盘内的所有板卡输送12VDC电力。

https://substackcdn.com/image/fetch/$s_!waXS!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcc71c2bc-25a1-4ac8-93e1-e880143cdcee_1148x2332.png

来源： Nvidia VR NVL72 Component BoM and Power Budget Model

50VDC 通过 Strata 板卡两侧的 50V 电源连接器之一进入板卡。接着，50VDC 由 Strata 板卡底部的 IBC 模块降压至 12VDC。随后，在馈入 Rubin GPU 和 Vera CPU 之前，12VDC 会由电压调节模块进一步降压至 1VDC。Strata 直接接收 50VDC，而 Grace Blackwell 的 Bianca 板卡则从电源分配板接收 12VDC。由于 Strata 板卡的功耗约为 4800W（相当于半个普通服务器机架的 TDP），而 Bianca 仅为 3000W，因此必须以更高的电压向板卡供电。将 50VDC 至 12VDC 的转换环节移至更近的位置，其优势在于能够降低电流并提升传输效率。

由于功率损耗与电流之间存在平方关系，50V、96A 条件下的功率损耗仅为 12V、400A 时的 1/17。

我们在 VR NVL72 组件物料清单与功率预算模型 中，列出了各类电压调节模块所需的所有功率半导体的用量与平均售价。

- 英伟达的圣诞礼物：GB300 与 B300——推理（Reasoning）与推断、亚马逊、内存与供应链 - Dylan Patel、Myron Xie 与 Daniel Nishball · 2024 年 12 月 25 日

维拉与鲁宾之间的功率动态分配依然存在，这一特性延续自我们上文报道过的 GB300。通过在 GPU 和 CPU 之间共享总计 4800W 的功率，该特性实现了更高效的电源规划。在对 GPU 需求极高的负载下，每个 GPU 会分配到 2300W 功率，剩余的 200W 留给 CPU。当 GPU 的功耗需求下降时，维拉便可动态提升至更高功率，从而在避免过度配置电源的同时，最大限度地减少 GPU 的空闲时间。

对于机箱前端的模块——ConnectX-9、BlueField-4 以及管理模块——电源分配板会向每个模块提供 12VDC 的电源。50VDC 直流电在电源分配板处降压至 12VDC，随后电源分配板通过铜制汇流排装置，将 12VDC 电源输送给相邻模块。ConnectX-9 的电源连接器位于模块顶部，紧邻 Paladin HD2。
