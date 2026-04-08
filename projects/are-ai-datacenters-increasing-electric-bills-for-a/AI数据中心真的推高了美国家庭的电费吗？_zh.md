# AI数据中心真的推高了美国家庭的电费吗？

## 引言

### 电价误区、PJM（覆盖含新泽西州在内美国东部13个州的电网运营商）糟糕的市场设计、容量电价暴涨 9.3 倍、ERCOT（德克萨斯州电力可靠性委员会）与 PJM 电网可靠性及扩容对比

作者：[Aishwarya Mahesh](https://substack.com/@powerbytes)、[Jeremie Eliahou Ontiveros](https://substack.com/@jeremieeliahouontiveros)、[Ajey Pandey](https://substack.com/@ajeypandey)及另外2人

2026年3月3日

## AI数据中心推高了美国家庭的电费吗？

SemiAnalysis 携手 Fluidstack 将于 3 月 15 日举办一场为期 48 小时的全栈 AI 基础设施黑客松，以此拉开 GTC 大会的帷幕。本次活动涵盖从电力接入到预填充（Prefill）、从破土动工到解码（Decode）生成的全栈环节。届时将有来自 OpenAI、GPU MODE 和 Thinking Machines 的嘉宾发表演讲，并提供算力赞助与GPU集群访问权限。快来与顶尖人才并肩共创：在此申请（https://luma.com/SAxFSHack）。

关于数据中心负荷增长及其对电价影响的议题，外界仍存在广泛误解，这与[我们近期辟谣的耗水谬论](https://newsletter.semianalysis.com/p/from-tokens-to-burgers-a-water-footprint)如出一辙。2025年6月，当地居民电价在一夜之间出现[约20%的暴涨](https://www.pa.gov/governor/newsroom/2025-press-releases/gov-shapiro-s-legal-action-again-averts-historic-price-spike-acr)，该议题随之成为2025年新泽西州选举的焦点。甚至有人将矛头指向该州为微软建设的300兆瓦Nebius AI数据中心，但考虑到该数据中心[超过85%的电力均为自发自用](https://newsletter.semianalysis.com/p/how-ai-labs-are-solving-the-power)，这种指责纯属无稽之谈。AI数据中心真的是导致居民电费飙升20%的罪魁祸首吗？

本报告通过剖析美国最大的两大能源市场（它们同时也是最大的AI数据中心枢纽）来探讨这一问题：PJM互联区域（覆盖含新泽西州在内美国东部13个州的电网运营商）以及ERCOT（负责管理得克萨斯州电网）。在“孤星之州”得克萨斯，过去三年的电价基本保持稳定。反观PJM区域的6700万居民，其2026年的电费账单预计将比“前AI数据中心”时代平均上涨约15%？为何会出现如此显著的分化？简而言之，实证数据表明，罪魁祸首是政府政策，而非AI。

![](https://substackcdn.com/image/fetch/$s_!YaBK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff4cbff97-5557-4b44-aaa1-539add752ebc_2400x1125.png)

来源： SemiAnalysis Energy Model, PJM, Monitoring Analytics

在PJM，我们认为糟糕的市场设计是罪魁祸首。PJM辖区家庭电费上涨了15%，其中大部分涨幅归咎于一个常被误解且颇为晦涩的机制：BRA容量拍卖。如下图所示，2025/26年度拍卖价较上年暴涨9.3倍。更糟糕的是，这种暴涨基于“模拟”推演，并未反映实际状况。它很大程度上取决于统筹机构（PJM）的供需预测，而我们将在后文指出，该机构历来屡现严重的预测失误。

![](https://substackcdn.com/image/fetch/$s_!4uxO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9e61dd7a-0a0b-4903-9694-84e6529ae506_3179x1543.png)

来源： PJM BRA Report

许多人将矛头指向激增的AI数据中心，这情有可原。PJM地区正处于这场AI热潮的最前沿，谷[歌重点在俄亥俄州哥伦布市周边训练其Gemini模型](https://newsletter.semianalysis.com/p/multi-datacenter-training-openais)，而位于印第安纳州和俄亥俄州的[Anthropic/亚马逊的“雷尼尔项目”（Project Rainier）](https://newsletter.semianalysis.com/p/amazons-ai-resurgence-aws-anthropics-multi-gigawatt-trainium-expansion)与[Meta的“普罗米修斯”（Prometheus）项目](https://newsletter.semianalysis.com/p/meta-superintelligence-leadership-compute-talent-and-data)，均跻身我们统计的[全球前五大AI数据中心](https://www.youtube.com/watch?v=a-9egkpaZUw)之列。此外，PJM辖区内还坐落着全球最大的数据中心枢纽——北弗吉尼亚。

现在来看看得克萨斯州。该州同样在经历规模相当的AI基础设施建设，OpenAI、谷歌DeepMind和Anthropic都在此地建造超大型设施。然而，得州的电力期货在过去一年里仅波动了几个百分点。没有9倍的暴涨，没有危机，这源于截然不同的市场设计。

![](https://substackcdn.com/image/fetch/$s_!bTKf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F30a916ae-8f6f-462a-a184-7622bd295775_1808x1110.png)

来源： Bloomberg

我们来深入剖析。本报告将重点聚焦ERCOT和PJM，因为它们不仅是美国最大的两个能源市场，更是这场AI革命的震中。我们将深度拆解两者各自的市场设计，解析它们如何应对激增的AI数据中心负荷增长，以及这些影响最终将如何传导至普通家庭。

随后，在付费专区，我们将探讨其对供应链的影响。我们认为，市场制约因素正在发生剧烈转变，而许多人却对此毫无察觉。这种转变将深刻影响各大AI领域的赢家，包括独立发电商（IPPs，如Vistra、Constellation、Talen等）、设备供应商，以及类似加密货币矿企的数据中心开发商。

对于寻求更深入分析的机构，请订阅我们的[能源模型](https://semianalysis.com/energy-model/)和[数据中心行业模型](https://semianalysis.com/datacenter-industry-model/)。后者按季度追踪并预测了2017至2032年间超过5000个独立设施及其电力容量。能源模型则在此基础上构建了能源供需分析，具体方法是追踪并预测全美每一座发电厂的运营情况，估算其真实的有效载荷承载能力（ELCC），分析并网队列动态，并将其与我们的数据中心需求侧数据进行匹配。

让我们先简要解析一下“容量”究竟是什么，以及它是如何传导至你每月的电费账单中的，然后再进一步深入剖析市场设计。

*本报告由 SemiAnalysis 与领先的期货经纪与清算公司 Archer Daniels Midland Investor Services（ADMIS）联合撰写。*

## 容量：为95%时间闲置的发电厂买单

总体而言，家庭月度电费账单主要由以下几项费用构成：

- **电量**：在放开管制的地区（包括PJM覆盖的13个州以及ERCOT/德克萨斯州），这项费用取决于批发价格，即电力的实时供需情况。

- **容量**：这项费用在ERCOT中并不存在，但在PJM中却至关重要。它取决于**容量**的供需情况，即那些每年仅在必要的用电高峰期才会启动数小时的电力资源。在PJM，这项费用每年通过一场大型拍卖来确定。

- **输配电（T&D）**：电力输配网络的费用。

> 这一领域依然受到高度监管。输配电企业通常赚取预先设定的、受监管的股本回报率。因此，输配电资产的利用率会影响终端消费者的电价。我们在本报告中不会对此展开探讨，而是将其留待未来的深度报告再作剖析。

- **其他**：税费、零售附加费、辅助服务等。由于这些费用因地区而异，我们在此不做深入探讨。

![](https://substackcdn.com/image/fetch/$s_!Y-ZQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6a888155-3f13-42d0-b47c-2633abbebb27_2848x1504.jpeg)

来源： SemiAnalysis estimates, EIA

容量市场的设立初衷，是确保家庭和企业始终能获得所需的电力，哪怕是在夏季或冬季的用电高峰期。作为背景参考，在单日内，**仅纽约市一地的电力负荷波动就可高达 2 吉瓦（GW）**，而作为对比基数的日常峰值仅为 **6 至 8 吉瓦。**当热浪来袭、所有人同时开启空调时，该市的用电负荷甚至会飙升至 **10 吉瓦**。

在PJM市场，为了确保在需要时有足够的电力容量，我们向发电厂所有者支付费用，使其资产在全年超过95%的时间里保持待命状态。该价格由每年举行一次的远期拍卖决定，随后分摊给该地区的所有电力用户。如下文详述，在2025/26交付期，这一价格暴涨了9.3倍。

相比之下，ERCOT是一个“纯电能市场”，没有单独的容量拍卖机制。实时价格信号决定了电力的“稀缺性”，并以此激励发电厂解决供需缺口。我们在报告后文中会详述一些技术细节，但两者的根本区别在于，ERCOT不存在中心化的年度容量拍卖，而是依靠实时的市场力量。

## PJM：160亿美元的模拟

容量市场设计的核心问题在于，它直接受制于作为中央计划者的PJM所做出的供需预测。任何预测偏差都可能导致数十亿美元的无谓支出。在2025至2026年的拍卖中，这笔支出总额高达160亿美元，最终被分摊给PJM辖区内的每一位居民和每一家企业。

### 基础剩余拍卖的运作机制

PJM 通过前文提及的远期容量市场来支付系统容量费用，该市场被称为[基础剩余拍卖 (BRA](https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2025-2026/2025-2026-base-residual-auction-report.pdf))。这是一项提前两年举行的年度拍卖：例如，PJM 针对 2027/28 年度的容量需求，会在 2025 年底进行拍卖。

与以美元/兆瓦时（即特定小时内消耗的电能）为交易单位的批发能源市场不同，BRA 的交易单位是美元/兆瓦·日（即特定日期内配置的峰值功率）。PJM 会根据其需求预测，决定需要配置多少兆瓦的发电机、电池及其他资源，以满足预计的最大电力负荷（外加备用容量率），随后启动拍卖机制来确定这些容量的成本。电网上的所有成本最终都由用户承担，因此，当这场容量拍卖的价格飙升时，涨幅自然会直接传导至普通家庭的电费账单上。

直到最近，BRA 始终在兑现其承诺。2025 年夏季，PJM 辖区内酷热难耐，6 月 23 日和 24 日更是创下了 PJM 历史上第三高和第四高用电峰值的纪录。但电力供应并未中断，因为系统具备充足的发电容量来满足负荷需求。

但现在，维持这种可靠性的代价极其高昂。2024年6月至2025年5月（2024/25服务期），容量成本为29美元/兆瓦日。而在当前的2025/26服务期，容量价格暴涨9.3倍至270美元/兆瓦日，部分地区甚至逼近450美元/兆瓦日。随后的2026/27和2027/28年度拍卖继续以创纪录的价格出清。市场普遍认为价格本会更高，但联邦监管机构强制设定了329美元/兆瓦日的价格上限。2025年12月17日举行的最新一次拍卖，已连续第二年触及该价格上限。

![](https://substackcdn.com/image/fetch/$s_!48ZG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdf36a940-6317-428c-9e9e-f171b1d7c3f2_3179x1543.png)

来源： PJM BRA Report

[PJM将“失控的”电力成本归咎于极端天气以及超大规模云厂商数据中心与AI的用电需求，这一叙事也随之渗透到了主流新闻报道中。](https://insidelines.pjm.com/maintaining-grid-reliability-through-highest-peaks-in-a-decade/)但这种解释掩盖了PJM自身的责任，因为容量价格是提前一年多设定的，其依据正是PJM自行设计的模拟模型。

### 模拟模型的底层机制

容量价格基于一条人为设定的供需曲线，内部称之为[可变资源需求曲线 (VRR曲线)。](https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2026-2027/2026-2027-bra-report.pdf)VRR曲线是基于PJM的内部预测模型构建的，而非基于市场对未来走势的预期。数据中心负载的预期增长使得这条曲线上的出清价格发生偏移，从而在完全脱离公开竞价过程的情况下推高了价格。

![](https://substackcdn.com/image/fetch/$s_!H6mE!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc7cfa0ed-0954-4a3a-9ebf-dd7c2609aaa2_1814x1230.png)

然而，VRR曲线是基于错综复杂的假设构建的，其中许多假设依赖于非公开模型和专有数据。即使预测负荷仅有小幅变动，也会引发出清价格的大幅波动。容量市场对预测参数极度敏感，数据中心负荷预测哪怕只有几吉瓦的偏差，也会酿成灾难性后果：这会改变出清点附近的曲线形态，进而导致价格飙升。

### 数据中心被归咎为容量价格飙升的罪魁祸首

[PJM的内部市场监测机构 (IMM](https://www.monitoringanalytics.com/reports/reports/2025/IMM_Analysis_of_the_20252026_RPM_Base_Residual_Auction_Part_G_20250603_Revised.pdf))——一家根据联邦能源监管委员会 (FERC) 要求设立的独立监测实体——对2025/26年度市场进行了替代情景模拟，让外界罕见地一窥PJM原本极不透明的方法论。根据该市场监测机构的说法，数据中心难辞其咎：

- 从预测中**剔除所有数据中心**后，PJM的峰值负荷减少了7,927兆瓦，进而导致总容量支付额**减少了93.3亿美元**——较实际价格下降了64%。

- **仅保留已通电的数据中心**使峰值负荷减少了4,654兆瓦，进而导致总容量支付额**减少77.4亿美元**——较实际价格下降了53%。在采用无限制VRR曲线的**2026/27**年拍卖参数下，IMM估计数据中心的总负荷约为11,993兆瓦。

根据IMM的分析，与假设不存在该负荷的电网相比，仅数据中心带来的增量负荷增长这一项，就足以解释容量成本为何大约翻倍。[IMM指出，2025/26年新增约7.9吉瓦的数据中心需求，2026/27年新增约12吉瓦。](https://www.monitoringanalytics.com/reports/reports/2025/IMM_Analysis_of_the_20252026_RPM_Base_Residual_Auction_Part_G_20250603_Revised.pdf)其他任何因素的影响都远不及此。

但是，所有这些模拟都掩盖了一个更深层次的问题：决定电价的核心拍卖机制**同样建立在模拟的基础之上**。VRR曲线是一条人为设定的供需曲线，其依据是PJM自行制定的预测。如果该预测不准确，这些误差就会扭曲整个容量市场。

而我们认为，该预测确实不准确。我们的测算方法在PJM辖区内追踪了每一个数据中心的精确建设时间表，结果表明PJM的预测可能过于乐观。这并非因为需求不足，而是由于数据中心建设延期（正如我们在行业模型中所强调的）、GPU生产与组装延迟（正如我们在加速器模型中所解释的），以及其他供应链问题。新硬件平台在初期往往存在缺陷，需要比以往更长的时间才能实现满负荷运转。

![](https://substackcdn.com/image/fetch/$s_!prZB!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff6daac55-f442-4fb9-a3bc-5ecc70c7a318_3180x1716.png)

来源： SemiAnalysis Datacenter Model, PJM

下文就是一个绝佳的例证。PJM自身的数据表明，其连未来一年的预测都做不准。2024年，数据中心负载预测较2023年的预测下调了800MW。2025年，这种情况再次发生：数据中心负载预测较仅一年前（即2024年）的预测又下调了1.1GW！

![](https://substackcdn.com/image/fetch/$s_!U3MK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F482f7f80-0d44-44d8-877b-c9e4be675c83_2222x708.png)

来源： PJM, Monitoring Analytics

### 远期电能价格却呈现出另一番景象

PJM的电能市场仍更接近于一个真正的市场，其供需平衡决定了动态变化的每兆瓦时（MWh）电价。这些价格在热浪期间飙升，在气候温和时回落，并依靠分散的市场参与者来追踪天然气价格、输电拥堵情况以及可再生能源发电量——正如一个正常市场应有的运作方式。

作为最具流动性的基准，PJM西部枢纽远期价格反映了能源交易员对未来的预期。在2028年和2030年窗口期，该价格上涨了12%至20%，2026年窗口期的涨幅还要略高一些。这些涨幅固然可观，但与容量市场9.3倍的暴涨完全无法相提并论。PJM的容量市场机制高度依赖模拟，其引发的价格冲击并未得到远期电能市场的印证。交易员投入的是真金白银，承担的是真实风险，他们并没有在定价中反映出PJM模拟VRR曲线所制造的那种恐慌。

![](https://substackcdn.com/image/fetch/$s_!aZkY!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F72c39ddb-b566-436e-8655-7e8517b918ed_1808x1110.png)

来源： Bloomberg

### PJM的供给侧预测同样基于模拟

PJM的预测与方法论同样影响着预测的供给侧。在AI数据中心热潮爆发的前一年，问题就已经开始显现。如下所示，短短四年间，总申报容量缩减了约35GW。这部分供给究竟去哪儿了？

![](https://substackcdn.com/image/fetch/$s_!0RvI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6ea967ff-1bf5-4d18-8612-fc7098521e9d_3179x1742.png)

来源： PJM

如下图所示，尽管煤电退役是最核心的驱动因素，但PJM还对方法论进行了重大调整，导致近20GW的电力供应凭空消失。其中，一项针对天然气发电厂核算方法的变更，更是让14GW的供应量在一夜之间蒸发。

![](https://substackcdn.com/image/fetch/$s_!lio-!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6f936070-e91d-4ce3-9b91-f9f59e93c834_3979x1919.png)

来源： PJM

### 容量价格如何推高居民电费账单

2026/27年基础剩余拍卖 (BRA) 的出清价格达到329美元/兆瓦日，这意味着PJM电网内的每一个用电负荷都将面临实质性的成本攀升。这些成本最终会通过终端零售电价收回，体现为公用事业公司、电力供应商以及大型企业客户所需缴纳的更高昂的容量电费。整体而言，这场拍卖意味着**总计高达160亿美元的容量支出，折合约每兆瓦12万美元。**

为了估算对零售电费账单的影响，我们需要以下数据点：

· 每户家庭平均用电量：在PJM，这一数据为每月880千瓦时。

· “负荷因子”，即平均用电量与峰值用电量之比。经验数据显示，40%是一个常见值。

· 容量电价：以329美元/兆瓦·日为基准，将其除以每天的小时数，再结合0.4的负荷因子，即可得出34美元/兆瓦时（即3.4美分/千瓦时）。

将3.4乘以月用电量（880千瓦时），得出每月29.9美元的支出。鉴于拍卖已经出清，我们几乎可以断定，家庭每月将比两年前多支付25到30美元！

![](https://substackcdn.com/image/fetch/$s_!YaBK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff4cbff97-5557-4b44-aaa1-539add752ebc_2400x1125.png)

来源： SemiAnalysis Energy Model, PJM, Monitoring Analytics

现在，让我们将目光转向德克萨斯州，看看那里的电价是如何应对 AI 数据中心大规模激增的。

## ERCOT：同等负载增长，无价格冲击

德克萨斯州电力可靠性委员会（ERCOT）的市场机制要简单易懂得多。它采用统一的市场机制，基于实时电价来平衡供需。ERCOT 并没有设立两个独立的市场，也不会做出直接左右市场需求的预测。

### 稀缺定价而非容量拍卖

ERCOT没有采用由年度拍卖驱动的容量市场，而是采用了基于运行备用需求曲线 (ORDC) 的实时稀缺价格加成机制。当电力供需平衡变得过于紧张时——例如所有人的空调都在同一时间运转——实时电价就会飙升，从每兆瓦时10至50美元的正常水平，飙升至每兆瓦时5000美元的上限，并在输电受限地区产生额外的价格加成。

![](https://substackcdn.com/image/fetch/$s_!pKKs!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7c2ea8ff-d1ba-4c7b-b934-26a53ba74b88_1799x1114.png)

这种稀缺定价结构使得每年运行时间不足100小时的容量资源（燃气调峰电厂、电池等）能够收回成本，因为这屈指可数的运行时间，依然能为一座50兆瓦的电厂或电池系统创造数百万美元的年营收。

换言之：在PJM，中央调度机构负责分析系统、确定容量需求，并保证向提供容量的电厂所有者支付费用。而在ERCOT，没有任何保底承诺，资产所有者必须自行分析并判断市场容量是否充足。实时价格信号就是反映市场供需瓶颈的直接证据。

### ERCOT的需求预测：规模惊人——却大多被忽视

这种差异尤为耐人寻味，因为ERCOT同样也会发布需求预测，且其预测数据规模惊人。2025年4月发布的[《2025年长期负荷预测》](https://www.ercot.com/files/docs/2025/04/29/Long-term-Load-Forecast-RPG.pdf)指出，数据中心是峰值负荷增量的最大单一驱动因素。部分基于德克萨斯州输电服务提供商的申报数据，ERCOT预计到2030年，潜在的数据中心负荷将达到77.9 GW——这一数字是上一年度预测值（29.6 GW）的两倍多，创下了史无前例的单年上调幅度。

![](https://substackcdn.com/image/fetch/$s_!Dqhd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F11a823b3-3e3f-4f95-9b4c-6a9ce585f4a9_1800x961.png)

来源： ERCOT

若按字面理解，该预测意味着一场结构性的需求冲击，其量级相当于在当前的负荷曲线上叠加一个全新的ERCOT系统。但实际上，没有人相信这些数字，市场也基本将其无视。

连ERCOT自己也承认其预测落空，并改弦更张。在2025年5月的《容量、需求与储备报告》中，他们主动进行了折算削减：常规申请按49.8%折算，经高管签字确认的申请按55.4%折算，且所有投运日期均推迟180天。ERCOT内部的电网分析师言下之意是，在真正动工之前，他们不会全盘按照开发商上报的规模来进行规划。

![](https://substackcdn.com/image/fetch/$s_!sY9J!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1e31a199-bfe3-45c6-9d33-2a6a48cc4fcb_1800x961.png)

来源： ERCOT

但这里的区别在于，ERCOT的负载预测和并网排队限制并不直接决定电价。PJM的预测会生成一条模拟供需曲线，进而直接决定系统容量成本的上下限。ERCOT则将需求预测用于指导系统规划、输电扩容和资源充裕度研究，而非作为直接的定价输入变量。ERCOT的这种方法内置了审慎机制，能够在投机性需求影响市场结果前将其过滤。

### 数据中心负荷增加，电力稀缺性反而下降

实体系统的表现证实，ERCOT的策略行之有效。2024年夏季，电网已承受了超过90吉瓦的破纪录峰值负荷，并在2025年5月创下了78.4吉瓦的春季负荷纪录。德克萨斯州超大规模云服务商的用电需求增长已极其庞大，但此后并未发生过限电。

能源交易员所看到的电价同样没有出现暴涨。远期价格——尤其是2026年、2028年和2030年的合约——在过去一年中上涨了11%至17%，这一涨幅虽然显著且与PJM大致相当，但并未出现容量价格飙升9倍的现象。

![](https://substackcdn.com/image/fetch/$s_!bTKf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F30a916ae-8f6f-462a-a184-7622bd295775_1808x1110.png)

来源： Bloomberg

[《2024年ORDC双年报告》](https://www.ercot.com/files/docs/2024/10/31/2024-biennial-ercot-report-on-the-ordc-20241031.pdf)指出，与以往周期相比，当前系统拥有更多的在线备用容量，从而保障了平稳、从容的增长。太阳能、风能、电池储能以及化石燃料调峰电厂均以充足的规模并网，为系统提供了缓冲。其可衡量的实际效果是，与往年相比，触发稀缺定价的小时数以及在稀缺定价上的总支出均有所下降。尽管电力需求不断攀升，但如今在ERCOT管辖区内，能源的稀缺程度反而有所缓解。如今，要将系统推入真正的稀缺状态，所需的吉瓦级新增需求甚至比两年前还要多。在对外发布的信息中，ERCOT对数据中心增长的关注点，也并不包含对资源稀缺的担忧。

![](https://substackcdn.com/image/fetch/$s_!bbjn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faeb83ece-fc7c-4534-b358-0b494e4cacef_1740x1100.png)

来源： ERCOT, SemiAnalysis annotation

批发市场远期价格曲线表明，交易员相信ERCOT能够消化这一增长。他们押注于供应扩张、储备改善以及[SB 6限电](https://www.bakerbotts.com/thought-leadership/publications/2025/july/texas-senate-bill-6-understanding-the-impacts-to-large-loads-and-co-located-generation)权限，认为这能在长期内缓解电力短缺。这种怀疑态度与ERCOT自身对开发商提交的申请进行风险折减的做法如出一辙。系统运营商在其预测中对数据中心原始的用电主张进行了折减；而市场则在远期价格中对这些主张进行了折价。

ERCOT的行动速度也要快得多：相较于PJM，其关键优势之一在于仅覆盖单一州，且不受FERC管辖。相比之下，PJM则必须应对FERC以及13个州。

## 冬季风暴“弗恩”：为可靠性买单 vs 实际交付

冬季风暴“弗恩”（2026年1月24日至27日）构成了首次真实世界的压力测试，既检验了PJM创下历史新高的2025/26年度容量价格，也考验了ERCOT在运行压力下的市场纪律。

### ERCOT：未现危机

ERCOT的电网在1月的严寒中经受住了考验。电网运营商发布的天气预警仅停留在预防层面。[实际需求低于预测，未触发任何紧急程序，系统维持了充足的备用容量。](https://www.bakerbotts.com/thought-leadership/publications/2025/july/texas-senate-bill-6-understanding-the-impacts-to-large-loads-and-co-located-generation)除了冬季风暴中常见的常规输配电故障外，得州电网未面临任何问题。

这充分证明，得州已从灾难性的冬季风暴乌里中汲取了深刻教训。乌里风暴后实施的各项改革措施——包括强制对天然气生产与发电设施进行冬季防寒改造、提升天然气与电力系统的协同能力，以及强化电网运行规程——在真实环境的考验下均被证明行之有效。

ERCOT的实时电价峰值约为300美元/兆瓦时。

### PJM：270美元/兆瓦-日换来21 GW的容量失效

PJM电网的表现则要惨烈得多。尽管容量市场已通过创纪录的出清价格将数据中心负载风险计入定价，该电网仍因设备冻结和燃料输送故障，损失了约21 GW的发电容量——这相当于在拍卖中成功出清机组总量的15%。

[美国能源部被迫根据《联邦电力法》第 202(c) 条发布紧急命令](https://www.utilitydive.com/news/doe-issues-emergency-orders-for-texas-new-england-and-pjm-markets-Fern-reliability/810464/)，授权电网运营商绕过环保限制，调用全国数据中心和工业站点约 35 GW 的备用发电容量——而这些容量原本根本不具备参与基本剩余拍卖（BRA）的资格。

实时电价反映了这种运行压力。PJM全系统平均电价达到700美元/兆瓦时，数据中心密集的弗吉尼亚州Dominion区域电价更是飙升至1800美元/兆瓦时。

这也暴露了 PJM 容量市场的另一个缺陷。在 PJM，发电厂无论如何都能获得报酬，即使在关键时刻无法供电。而在 ERCOT，发电厂只有在备用容量率紧张，且实际发电并向电网输送电力时，才能创造可观的营收——因此，它们有充分的动力在严寒天气下保持设备的正常运转。

### 风暴揭示的真相

这场风暴暴露了 PJM 容量市场的根本性脱节。容量价格高企源于对数据中心负荷增长的预测——这一风险确实兑现了。然而，实际的运行故障却源于防寒改造不足和燃料基础设施脆弱，而容量市场并未提供解决这些隐患的激励机制。PJM 暴涨 9.3 倍的容量价格本该买来可靠性。但它并没有。

ERCOT并未将投机性的数据中心增长计入高昂的容量费用，然而在面临考验时，其强制性的运营改革却确保了电网的稳定。成本更低，成效更优。

风暴期间DOE确认的35 GW数据中心备用发电也印证了一个重要事实：只要整合得当，数据中心完全可以作为电网资源发挥作用。尽管ERCOT无需激活这些备用资源便成功应对了风暴，但它们的存在构成了一个巨大的可靠性缓冲，而这两个市场均未能在前瞻性规划中对其进行系统性定价。这是一个监管机构与投资者都应密切关注的尚未开发的资产类别。

## 未来展望

### 政治余波已然显现

PJM基于模拟测算的定价机制，已使其容量市场沦为政治众矢之的。在2025/26交付年拍卖价格飙升之后，宾夕法尼亚州州长乔什·夏皮罗向FERC正式提出申诉，指控BRA规则有失公允。随后，一项经FERC批准的和解协议强制实施了更为严格的价格上限——即针对2026/27和2027/28交付年的临时价格区间限制。这正是2027/28交付年拍卖的出清价格与前一年几乎持平的根本原因。

但这一价格上限并未触及底层机制。VRR曲线和需求预测方法均原封不动。这种权宜之计还引发了新问题：备用容量裕度跌破了PJM自身设定的可靠性目标。尽管电网仍在正常运行并维持着一定的备用容量，但该裕度正在不断萎缩。同时，由于未来价格上限存在监管不确定性，容量市场吸引新建发电项目投资的能力已大打折扣。

业界曾尝试改革PJM的市场结构，但面临的监管阻力与各方利益博弈极其激烈。PJM曾试图引入无容量支撑负荷（NCBL）规则——这本质上是一种对未能确保自身容量的大型负荷进行限电的机制——但遭到利益相关方的一致谴责并最终撤回。[FERC针对大型负荷与数据中心发布的拟议规则制定的提前通知（ANOPR）](https://www.mayerbrown.com/en/insights/publications/2025/11/ferc-large-load-interconnection-preliminary-rulemaking-key-takeaways-for-data-center-developers-other-large-load-projects-and-investors)标志着联邦层面的审查正在趋严，但总而言之，FERC的任何规则制定都将耗时数年，且必将面临法律挑战。

### 监管不对称性

ERCOT之所以能更迅速地采取行动，得益于其更为精简的监管架构。由于ERCOT的服务辖区完全位于得克萨斯州境内，得州立法机构与公共事业委员会能够对其进行直接监管。第6号参议院法案 (SB 6) 仅在一个立法会期内，便完成了通过、签署并正式生效的全部流程。相比之下，PJM的服务辖区横跨13个州及哥伦比亚特区，其监管权限归属于FERC。若要复制类似SB 6 的负荷削减权限，不仅需要FERC的批准，甚至可能牵涉联邦层面的立法，整个过程将耗时数年，而非短短数月。

这种结构性不对称具有持久性，且具备投资价值。相比PJM改革其容量市场架构的步伐，ERCOT在调整自身市场规则与运营要求方面，将始终保持更快的响应速度。对于正在制定10年期选址决策的超大规模云厂商而言，这种监管敏捷性与当前的电价差异同等重要。

## 赢家、输家与不断转移的市场瓶颈

这就引出了我们的下一部分：赢家与输家。PJM预测中的一个关键问题在于其缺乏全局视野。下文我们将探讨不断转移的市场瓶颈，以及这对于GE Vernova、卡特彼勒 (Caterpillar)和Bloom Energy等现场燃气解决方案设备供应商，维谛技术 (Vertiv)等设备供应商，Vistra和Talen Energy等独立发电商 (IPPs)，以及数据中心开发商与加密货币矿工究竟意味着什么。

付费订阅者可向下滚动至免责声明下方，阅读本报告的其余部分。

## 免责声明

## SemiAnalysis免责声明

> **分析师认证与研究独立性。**

本报告署名分析师特此声明，本报告所表达的所有观点均准确反映了我们对任何及所有标的证券或发行人的个人看法。我们的薪酬在过去、现在或未来均不会直接或间接与本报告中的具体建议或观点挂钩。

SemiAnalysis LLC（下称“本公司”）是一家独立的股票研究机构。本公司不是美国金融业监管局（FINRA）或美国证券投资者保护基金（SIPC）成员，也不是注册经纪交易商或投资顾问。SemiAnalysis没有任何其他受监管或不受监管的业务活动会与其提供独立研究产生冲突。

**研究与信息的局限性。**

本报告仅定向分发给SemiAnalysis LLC的合格机构客户或专业客户。报告内容仅代表作者本人的观点、见解与分析。所载信息不构成财务、法律、税务或任何其他专业建议。报告引用的所有第三方数据均来自公认可靠的公开渠道。但本公司对该等信息的准确性或完整性不作任何明示或暗示的保证。在任何情况下，本公司均不对此类材料的正确性或后续更新承担责任。对于因使用上述数据而导致的任何损失或机会错失，本公司概不负责。

本报告包含的任何内容或公司分发的任何材料，均不应被视为出售任何证券或投资的要约，也不构成购买任何证券或投资的要约邀请。接收到的任何研究或其他材料，均不应被视为个性化投资建议。投资决策应作为整体投资组合策略的一部分。在做出任何投资决策前，请务必咨询专业的财务、法律及税务顾问。对于基于从SemiAnalysis LLC获取的信息或研究而做出的投资决策，由此引发的任何直接或间接、附带或后果性损失或损害（包括利润、营收或商誉损失），SemiAnalysis LLC概不负责。

**严禁复制与分发。**

任何用户均不得重制、修改、复制、分发、出售、转售、传播、转移、授权、转让或发布本报告本身及其包含的任何信息。尽管有前述规定，获准使用测算模型的客户可对其中的信息进行更改或修改，但前提是仅供该客户自行使用。本报告无意提供或分发用于任何非法或被地方、州、国家及国际法律法规禁止的目的；若在某司法管辖区内提供或分发本报告会导致本公司须接受任何形式的注册或监管，则本报告亦不适用于该地区。

**版权、商标与知识产权。**

SemiAnalysis LLC及本报告中包含的任何徽标或标记均为专有资料。未经SemiAnalysis LLC明确书面同意，严禁使用上述名称、徽标与标记。除非另有说明，本报告的页面或显示界面，以及其中包含的信息与材料的版权，均为SemiAnalysis LLC所有的专有财产。未经授权使用本报告中的任何材料，可能触犯多项法规与法律，包括但不限于版权法、商标法、商业机密法或专利法。

**ADMIS 免责声明**

本文所含数据、评论与意见仅由ADM Investor Services, Inc.（简称ADMIS）提供，纯粹用作信息参考。这些内容绝不应被视为Archer Daniels Midland Company的数据、评论或意见。本报告所含信息源自发布之时被认为可靠且准确的渠道，但我们未作独立核实，因此不保证其准确性或完整性。报告中所述意见可能随时更改，恕不另行通知。本报告不构成参与买卖期货合约或相关商品期权交易的邀约。 交易期货合约或商品期权存在巨大的亏损风险。投资者应结合自身财务状况，审慎评估此类投资的内在风险。未经ADMIS明确书面同意，严禁复制或转发本报告。再次声明，本报告所含数据、评论或意见均由ADMIS提供，而非阿彻丹尼尔斯米德兰公司提供。版权所有 (c) ADM Investor Services, Inc.

资料来源与参考文献：

1. SemiAnalysis数据中心行业模型

2. [https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2025-2026/2025-2026-base-residual-auction-report.pdf](https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2025-2026/2025-2026-base-residual-auction-report.pdf)

3. [https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2026-2027/2026-2027-bra-report.pdf](https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2026-2027/2026-2027-bra-report.pdf)

4. [https://insidelines.pjm.com/maintaining-grid-reliability-through-highest-peaks-in-a-decade/](https://insidelines.pjm.com/maintaining-grid-reliability-through-highest-peaks-in-a-decade/)

5. [https://www.monitoringanalytics.com/reports/reports/2025/IMM_Analysis_of_the_20252026_RPM_Base_Residual_Auction_Part_G_20250603_Revised.pdf](https://www.monitoringanalytics.com/reports/reports/2025/IMM_Analysis_of_the_20252026_RPM_Base_Residual_Auction_Part_G_20250603_Revised.pdf)

6. [https://www.pa.gov/governor/newsroom/2025-press-releases/gov-shapiro-s-legal-action-again-averts-historic-price-spike-acr](https://www.pa.gov/governor/newsroom/2025-press-releases/gov-shapiro-s-legal-action-again-averts-historic-price-spike-acr)

7. [https://www.ercot.com/files/docs/2025/04/29/Long-term-Load-Forecast-RPG.pdf](https://www.ercot.com/files/docs/2025/04/29/Long-term-Load-Forecast-RPG.pdf)

8. [https://www.ercot.com/files/docs/2025/05/15/CapacityDemandandReservesReport_May2025.pdf](https://www.ercot.com/files/docs/2025/05/15/CapacityDemandandReservesReport_May2025.pdf)

9. [https://www.ercot.com/files/docs/2025/06/17/ERCOT-Monthly-Operational-Overview-May-2025.pdf](https://www.ercot.com/files/docs/2025/06/17/ERCOT-Monthly-Operational-Overview-May-2025.pdf)

10. [https://www.ercot.com/files/docs/2024/10/31/2024-biennial-ercot-report-on-the-ordc-20241031.pdf](https://www.ercot.com/files/docs/2024/10/31/2024-biennial-ercot-report-on-the-ordc-20241031.pdf)

11. [https://www.bakerbotts.com/thought-leadership/publications/2025/july/texas-senate-bill-6-understanding-the-impacts-to-large-loads-and-co-located-generation](https://www.bakerbotts.com/thought-leadership/publications/2025/july/texas-senate-bill-6-understanding-the-impacts-to-large-loads-and-co-located-generation)

12. [https://www.spglobal.com/commodity-insights/en/news-research/latest-news/electric-power/042325-outlook-2025-texas-summer-power-prices-may-top-2024-levels-on-weather-strong-gas](https://www.spglobal.com/commodity-insights/en/news-research/latest-news/electric-power/042325-outlook-2025-texas-summer-power-prices-may-top-2024-levels-on-weather-strong-gas)

13. [https://www.rtoinsider.com/121911-pjm-capacity-auction-clears-max-price-falls-short-reliability-requirement/](https://www.rtoinsider.com/121911-pjm-capacity-auction-clears-max-price-falls-short-reliability-requirement/)

14. [https://elibrary.ferc.gov/eLibrary/docinfo?accession_number=20241230-5225](https://elibrary.ferc.gov/eLibrary/docinfo?accession_number=20241230-5225)

15. [https://www.reuters.com/business/energy/power-prices-surge-winter-storm-spikes-demand-us-data-center-alley-2026-01-25/](https://www.reuters.com/business/energy/power-prices-surge-winter-storm-spikes-demand-us-data-center-alley-2026-01-25/)

16. [https://www.usnews.com/news/top-news/articles/2026-01-25/power-prices-surge-as-winter-storm-spikes-demand-in-us-data-center-alley](https://www.usnews.com/news/top-news/articles/2026-01-25/power-prices-surge-as-winter-storm-spikes-demand-in-us-data-center-alley)

17. [https://www.ercot.com/files/docs/2026/01/28/ERCOT-Post-Event-Report-Winter-Storm-Fern.pdf](https://www.ercot.com/files/docs/2026/01/28/ERCOT-Post-Event-Report-Winter-Storm-Fern.pdf)

18. [https://www.utilitydive.com/news/doe-issues-emergency-orders-for-texas-new-england-and-pjm-markets-Fern-reliability/810464/](https://www.utilitydive.com/news/doe-issues-emergency-orders-for-texas-new-england-and-pjm-markets-Fern-reliability/810464/)

19. [https://www.publicpower.org/periodical/article/department-energy-asks-grid-operators-be-prepared-make-backup-generation-resources-available-needed](https://www.publicpower.org/periodical/article/department-energy-asks-grid-operators-be-prepared-make-backup-generation-resources-available-needed)

自2025年中期以来，我们的[数据中心行业模型](https://semianalysis.com/datacenter-industry-model/)显示市场制约因素发生了巨大反转。过去能源曾是核心瓶颈，但我们现在看到，2027年“实质性”的数据中心供应量将超过AI和非AI计算的实际需求。

![](https://substackcdn.com/image/fetch/$s_!p39e!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbcb595a9-8399-43b7-8ea5-d7465e58e0f7_1800x882.png)

来源：[SemiAnalysis数据中心行业模型](https://semianalysis.com/datacenter-industry-model/)

现场燃气发电的兴起极大缓解了能源瓶颈。[一个多月前，我们曾指出市场中已有12家不同的设备制造商获得了超过400兆瓦的订单](https://newsletter.semianalysis.com/p/how-ai-labs-are-solving-the-power)。我们最新的统计显示这一数字已增至15家，涉及的总规模或规划产能已达数吉瓦。[请在我们的模型中查看具体厂商、容量及部署地点](https://semianalysis.com/datacenter-industry-model/)。柴油发电机制造商如今正全面押注现场燃气发电，因为他们意识到其核心市场的“附加率”（即每兆瓦数据中心容量对应的平均柴油备用兆瓦数）正在快速下降。这为整个现场燃气发电市场新增了超过10吉瓦的制造产能。

![](https://substackcdn.com/image/fetch/$s_!oMuQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2ff493c8-6ff5-41ea-bc53-9bbbfdcbffed_1894x1396.png)

来源：ERCOT

瓶颈也正从能源转向施工建设。ERCOT的数据显示，“获批通电”的园区甚至没有满负荷用电。这通常是因为变电站虽已建成并网，但建筑或机架尚未完工。在[数据中心模型](https://semianalysis.com/datacenter-industry-model/)中指出数据中心延期，是我们近期最热衷的工作之一。至今我们战绩斐然，最亮眼的表现包括率先指出微软延期、在三季度财报前预判Coreweave延期，以及点名甲骨文和Nebius。此外，我们还锁定了许多其他即将面临延期、但尚未被市场察觉的设施。

因此，公用事业公司对2027年及以后的许多预测都被高估了。即使公用事业公司声称其预测有ESA和LOA支撑，且具备“财务承诺”背书，他们也没有意识到，这些承诺对超大规模云服务商而言根本无关紧要。即使按10万美元/兆瓦（此类承诺的上限）计算，这一金额也比建设数据中心外壳的成本低100倍以上，比建设英伟达（NVIDIA）集群低300倍以上。

正如我们近期发布的机构专享文章《英伟达作为AI的中央银行》所指出的，超大规模云厂商正利用电力资源将其他竞争对手挤出市场，并迫使客户采用其定制芯片。这在电网侧引发了大规模的重复下单，导致许多公用事业公司高估了需求预测。

最后，我们预计到2027年，全局瓶颈将从电力转向芯片。整个行业将无法采购到足够的存储和逻辑芯片，更严重的短缺即将到来。

因此，我们认为能源瓶颈正在缓解，对核心电网瓶颈风险敞口过大的独立发电商将面临下行风险。

![](https://substackcdn.com/image/fetch/$s_!OgV8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffcdfdb12-4764-42d2-b50d-498326636f63_2208x1952.jpeg)

来源：SemiAnalysis 存储模型

对于加密货币矿工和数据中心开发商而言，竞争将更加激烈。电网供电依然是稀缺资源，但交付时间往往不可靠。例如，PJM电网承诺在2027至2028年交付的任何兆瓦级电力容量，都面临巨大不确定性。交付时间的确定性至关重要，现场发电因此成为首选方案。事实上，我们预计到2028年，美国新建数据中心超过50%的新增电力容量将来自表后发电。然而，真正有保障的电网供电享有极高溢价，且极易转手售出。最理想的情况是变电站已建成并通电，这让现有的比特币挖矿资产变得极具吸引力。

##
