The core issue with the capacity market design is that it is directly impacted by the supply & demand forecast of a central planner, PJM. Any forecasting error can lead to billions of dollars of unwarranted spending. In the 2025-26 auction, that spending sums up to $16 billion, spread across every single resident and business in the PJM area.

### How the Base Residual Auction Works

PJM pays for system capacity with the aforementioned forward capacity market, called the [Base Residual Auction (BRA](https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2025-2026/2025-2026-base-residual-auction-report.pdf)). This is a yearly auction ran two years ahead of time: for example, PJM’s 2027/28 capacity needs were auctioned at the end of 2025.

Unlike wholesale energy markets that trade in $/MWh (i.e. electrons consumed in a given hour), the BRA trades in $/MW-day (i.e. peak power provisioned in a given day). PJM’s demand forecast determines how many megawatts of generators, batteries, and other resources it needs to meet its maximum projected electric load (plus a reserve margin), then runs the auction to discover how much that capacity will cost. Customers ultimately pay for everything on the grid, so when prices in this capacity auction spike, that spike reaches household electric bills.

Until recently, the BRA delivered on its promise. Summer 2025 was brutally hot in PJM, with June 23 and 24 setting records as the 3rd- and 4th-highest peak days in PJM history. The lights did not go out, because there was enough generation capacity to meet the load.

But that reliability now comes at an extraordinary price. Between June 2024 and May 2025 (the 2024/25 service period), capacity cost $29/MW-day. For the current 2025/26 service period, capacity jumped 9.3x to $270/MW-day, with select locations seeing prices closer to $450/MW-day. The subsequent 2026/27 and 2027/28 auctions continued clearing at record prices. It was widely believed that the price would be even higher, but the federal regulator imposed a price cap of $329/MW-day. The most recent auction, December 17th, 2025, hit the price cap for the second straight year.

![](https://substackcdn.com/image/fetch/$s_!48ZG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdf36a940-6317-428c-9e9e-f171b1d7c3f2_3179x1543.png)

Source: PJM BRA Report

[PJM blamed “runaway” power costs on both extreme weather and hyperscaler datacenter & AI power demand, and that narrative trickled into mainstream news.](https://insidelines.pjm.com/maintaining-grid-reliability-through-highest-peaks-in-a-decade/) But that explanation obscures PJM’s own responsibility, because capacity prices are set more than a year ahead of time, based on a simulated model designed by PJM.

### The Simulation Under the Hood

Capacity prices are based on an artificial supply-demand curve known internally as the [Variable Resource Requirement (VRR) curve.](https://www.pjm.com/-/media/DotCom/markets-ops/rpm/rpm-auction-info/2026-2027/2026-2027-bra-report.pdf) The VRR curve is built on PJM’s internal forecast model, not on what the market thinks will happen. The projected increase in datacenter load shifted the clearing price on this curve, driving up prices independent of any public bid process.

![](https://substackcdn.com/image/fetch/$s_!H6mE!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc7cfa0ed-0954-4a3a-9ebf-dd7c2609aaa2_1814x1230.png)

However, the VRR curve is constructed from a web of assumptions, many of which depend on non-public models and proprietary data. Even modest changes in forecasted load can trigger large swings in clearing prices. The capacity market’s extreme sensitivity to forecast inputs means that getting the datacenter load number wrong by even a few gigawatts produces a catastrophic result: changing the curve’s shape near the clearing point, and ramping prices.

### Datacenters blamed as the culprit for surging capacity prices

[PJM’s Internal Market Monitor (IMM](https://www.monitoringanalytics.com/reports/reports/2025/IMM_Analysis_of_the_20252026_RPM_Base_Residual_Auction_Part_G_20250603_Revised.pdf)) -- an independent monitoring entity required by the Federal Energy Regulatory Commission (FERC) -- ran alternate simulations of the 2025/26 market, offering rare visibility into PJM’s otherwise-opaque methodology. According to the market monitor, datacenters should be blamed:

* **Removing all datacenters** from the forecast reduced PJM peak load by 7,927 MW, resulting in a **$9.33 billion reduction** of total capacity payments -- a 64% reduction versus the actual price.

* **Keeping only already-energized datacenters** reduced peak load by 4,654 MW, resulting in a **$7.74 billion reduction** -- a 53% cut from the actual price. For the **2026/27** auction parameters with an unrestricted VRR curve, the IMM estimated ~11,993 MW of combined datacenter load.

According to the IMM’s analysis, incremental datacenter load growth alone explains roughly a doubling in capacity costs versus a hypothetical grid without that load. [The IMM attributes ~7.9 GW of additional datacenter demand in 2025/26 and ~12 GW in 2026/27.](https://www.monitoringanalytics.com/reports/reports/2025/IMM_Analysis_of_the_20252026_RPM_Base_Residual_Auction_Part_G_20250603_Revised.pdf) No other factor came close.

But all of these simulations obscure a deeper issue: the main auction that drives electric rates is **also based on a simulation**. The VRR curve is an artificial supply-demand curve based on a forecast that PJM made for themselves. If that forecast is inaccurate, those inaccuracies skew the entire capacity market.

And we believe the forecast **is** inaccurate. Our methodology [tracks precise construction timelines of every single datacenter](https://semianalysis.com/datacenter-industry-model/) in the PJM area and shows PJM’s forecast is likely too optimistic. This is not due to a lack of demand, rather it’s due to datacenter construction delays (as highlighted in our [Industrials Model](https://semianalysis.com/industrials-model/)), to GPU production and assembly delays (as explained in our [Accelerator Model](https://semianalysis.com/accelerator-hbm-model/)), and other supply chain issues. New hardware platforms are often buggy at first and longer-than-usual to turn on at full capacity.

![](https://substackcdn.com/image/fetch/$s_!prZB!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff6daac55-f442-4fb9-a3bc-5ecc70c7a318_3180x1716.png)

Source: SemiAnalysis Datacenter Model, PJM

We show below a great example of this. PJM’s own data shows an inability to forecast even one year out. In 2024, the datacenter load forecast was cut by 800MW versus the 2023 load forecast. In 2025, it happened again: the datacenter load forecast was cut by 1.1GW versus what had been forecasted just a year ago, in 2024 !

![](https://substackcdn.com/image/fetch/$s_!U3MK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F482f7f80-0d44-44d8-877b-c9e4be675c83_2222x708.png)

Source: PJM, Monitoring Analytics

### Forward Energy Prices Tell a Different Story

The energy market in PJM remains closer to a real market, with supply and demand balances that return a moving price per MWh of electricity. These prices spike during heat waves, fall during mild weather, and use distributed market actors to track gas prices, transmission congestion, and renewable output -- like a market should.

PJM Western Hub forward prices -- the most liquid benchmark for energy traders’ view of the future -- have increased 12-20% in the 2028 and 2030 windows, with the 2026 window jumping somewhat higher. These are meaningful increases, but nothing resembling the 9.3x explosion in the capacity market. PJM’s simulation-heavy capacity construct is producing a price shock that the forward energy market does not validate. Traders, using real money and real risk, are not pricing in the same panic that PJM’s simulated VRR curve produced.

![](https://substackcdn.com/image/fetch/$s_!aZkY!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F72c39ddb-b566-436e-8655-7e8517b918ed_1808x1110.png)

Source: Bloomberg

### PJM’s supply-side forecast is also simulated

PJM’s forecast and methodology are also impacting the supply side of the forecast. A year before the AI Datacenter boom, issues had already begun to rise. As shown below, total offered capacity has been reduced by ~35GW in just four years. Where did that supply go?

![](https://substackcdn.com/image/fetch/$s_!0RvI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6ea967ff-1bf5-4d18-8612-fc7098521e9d_3179x1742.png)

Source: PJM

As shown below, while coal retirements were the biggest drivers, PJM also introduced major methodology changes that caused close to 20GW of supply to disappear. A methodology change on how PJM accounts for natural gas power plants made 14GW disappear overnight.

![](https://substackcdn.com/image/fetch/$s_!lio-!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6f936070-e91d-4ce3-9b91-f9f59e93c834_3979x1919.png)

Source: PJM

### How Capacity Prices Hit Household Bills

The 2026/27 Base Residual Auction (BRA) clearing price of $329/MW-day represents a tangible cost increase for every load in PJM. These costs are ultimately recovered through retail rates, appearing as higher capacity charges for utilities, suppliers, and large customers. In total, the auction translates to approximately **$16 billion in total capacity payments, or roughly $120,000 per MW.**

To estimate the impact on retail bills, we need the following datapoints:

· Average power consumption per household: in PJM, that’s 880 kWh per month.

· “Load factor”, i.e. average usage to peak usage. Empirical data shows 40% as a common value.

· Capacity prices: at $329/MW-day, we can divide this by the number of hours per day, and apply the 0.4 load factor, to get $34/MWh (or 3.4c/kWh).

Multiplying 3.4 by the monthly consumption (880 kWh) gets us a $29.9 monthly payment. Given the auction has already been cleared, we have near-certainty that households will pay $25-30 more per month than two years ago!

![](https://substackcdn.com/image/fetch/$s_!YaBK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff4cbff97-5557-4b44-aaa1-539add752ebc_2400x1125.png)

Source: [SemiAnalysis Energy Model](https://semianalysis.com/energy-model/), PJM, Monitoring Analytics

Let’s now turn our attention to Texas, to see how power prices have responded to the massive AI Datacenter surge.
