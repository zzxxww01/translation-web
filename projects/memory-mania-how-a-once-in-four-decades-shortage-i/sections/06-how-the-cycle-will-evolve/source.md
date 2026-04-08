History suggests that even the largest memory supercycles do not last indefinitely, and we believe this cycle will be no exception. That said, as we have previously maintained, we think this cycle could be larger and last longer than prior cycles. In our view, the supercycle can extend through 2027, with conditions becoming more challenging and volatile in late 2027 and into 2028—a view some may consider aggressive, but one echoed by many industry participants we spoke with, though not universally shared. A few things we think are going to happen, and some are already happening:

* **More fab pull-ins and capacity expansion:** We expect additional fab schedule pull-ins across all three major memory suppliers as capacity expansion plans accelerate, and we are already seeing early evidence of this trend. SK hynix has pulled in the schedules for both its M15X and Yongin Phase 1 fabs. Micron is also accelerating capacity, pulling in its Idaho 1 ramp from 2H27 to mid-2027, while its recent acquisition of PSMC’s fab adds up to ~45k wafers per month of potential capacity, which is expected to begin contributing wafer output in 2H27 with gradual ramp-up timeframe. Capacity expansion will come more meaningfully when memory supplier’s cleanroom coming online mostly by the end of 2027, and we might hear additional news on its future capacity expansion plan.

* **Significant node migration:** As previously outlined, we believe the industry will undergo large-scale node migration to 1b and 1c over the next two years, which is confirmed by ASML and LRCX’s management in the latest earnings call. This shift is driven by 1) a significant need to increase bit output without much new wafer capacity and 2) 1c-based HBM4E in 2027

* **Ongoing HBM acceleration and sustained pressure on commodity:** We believe memory suppliers will continue to prioritize HBM as their top strategic focus, given its structurally superior returns and long-term growth potential relative to commodity DRAM. While conventional DRAM is also entering a highly favorable pricing environment, HBM represents a more sustainable and strategically important opportunity over the long term. As a result, we expect the tension between allocating capacity to HBM versus commodity DRAM to remain top of mind for memory company executives.

A unifying theme across these three developments - fab pull-ins, accelerated node migration, and increased HBM prioritization - is rising demand for WFE. To enable this development, memory suppliers are likely to materially increase DRAM capex to support fab build-outs, advanced-node transitions, and incremental HBM wafer capacity. The market has already priced in at least some of this cycle, especially in logic, after the TSMC 2026 capex came in much higher than expected, with much stronger conviction for the capex increase in the next few years.

We expect this dynamic to increasingly extend into the memory ecosystem, benefiting both front-end and back-end equipment suppliers. In fact, just this week, ASML management also expressed a very strong memory outlook for EUV driven by 1) Strong HBM wafer capacity expansion and EUV layer count requirement, 2) Strong demand for node migration to 1b and 1c from the suppliers.

All 3 leading memory producers are increasing EUV layer counts in newer processes. This is necessary for scaling in general, and helps with HBM performance as it becomes a larger part of the product mix.

![](https://substackcdn.com/image/fetch/$s_!bxgD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb33e346a-a9b6-4360-8524-fd0fc99b2756_864x541.png)

Source: [SemiAnalysis WFE Model](https://semianalysis.com/wafer-fab-model/) - [Sales@SemiAnalysis.com](mailto:Sales@SemiAnalysis.com)

There are a few clear areas where EUV can replace DUV multipatterning, most in the congested region where access transistors (the devices that allow read and write to the memory cell) meet the memory storage capacitors (which stores the charge representing a 1 or 0). Contacts between access transistor source and storage capacitor, along with the transistor drain to bitline, are probably the first to go to EUV. They are cylindrical vias with small dimension in both X and Y, which generally makes them more difficult than narrow lines. It’s similar to 7nm logic, where the tightest pitch via layers were the first to adopt EUV.

Next the bitline, wordline, gate, and active area cuts are good candidates for EUV. Narrow lines are relatively easy to produce with DUV multipatterning (pitch splitting), but cutting the line ends is very difficult. You can see in the diagram below how small the tip-to-tip distance needs to be in some cases - look at the ends of the bitlines. Other line ends aren’t shown but have a similar challenge.

We wrote more about this 6F2 architecture, how it scales, and what will break first as it continues to scale in future nodes [as part of our VLSI 2025 recap](https://newsletter.semianalysis.com/i/174558662/dram-4f2-and-3d).

![](https://substackcdn.com/image/fetch/$s_!M1y7!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe41583fc-a320-4da1-9d3c-d017b89bd9e2_757x575.png)

*Storage node contact (denoted BC for buried contact), bitline cut (the narrow gap between bitline ends), and bitline contact (denoted DC here) are the first layers where EUV is adopted. Source: Samsung*

DRAM EUV intensity will increase substantially in the short term, as chipmakers are rushing to convert as much capacity as they can to the latest, EUV-heavy, processes. Longer term, they are taking steps to rein in cost. SK Hynix will continue to increase EUV layer count in the upcoming 1γ process, but predicts EUV spend will begin to level off. This is due to likely MOR adoption, which effectively increases throughput per tool without paying ASML for an upgrade, and possibly other improvements. Still, a *slower* increase in EUV spend is still an increase and great for ASML.

*Want complete details on the WFE supercycle? Model subscribers had them long before this report: [https://semianalysis.com/wafer-fab-model/](https://semianalysis.com/wafer-fab-model/)*

![](https://substackcdn.com/image/fetch/$s_!78Ir!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F24839116-a43e-40fe-9a59-2d9c470627f5_889x508.png)

Source: [SemiAnalysis WFE Model](https://semianalysis.com/wafer-fab-model/) - [Sales@SemiAnalysis.com](http://Sales@SemiAnalysis.com)

DRAM WFE capex will increase by roughly 26%, 34%, and 20% for Samsung, SK hynix, and Micron, respectively, in 2026. These increases are driven by aggressive HBM capacity expansion, rapid migration to 1b and 1c nodes with higher EUV layer intensity, and fab build-outs slated to come online in 2027, alongside accelerating node migration across the industry. We expect this view to be validated as the upcoming earnings season reflects semiconductor management commentary, alongside capital expenditure guidance from the memory companies.
