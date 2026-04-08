The Electric Reliability Council of Texas (ERCOT) is a much simpler market to understand. It runs a unified market mechanism balancing supply and demand based on real-time prices. ERCOT does not have two separate markets, and does not make forecasts that impacts directly market needs.

### Scarcity Pricing Instead of a Capacity Auction

Instead of a capacity market driven by a once-a-year auction, ERCOT uses a real-time scarcity price adder based on an Operating Reserve Demand Curve (ORDC). When the balance between electric supply and demand gets too tight -- when everyone’s air conditioner runs at the same time -- the real-time energy price spikes, from normal prices of $10-50/MWh to a cap of $5,000/MWh, with additional adders in transmission-constrained areas.

![](https://substackcdn.com/image/fetch/$s_!pKKs!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7c2ea8ff-d1ba-4c7b-b934-26a53ba74b88_1799x1114.png)

This scarcity-price structure allows capacity resources that run fewer than 100 hours per year (gas peaker plants, batteries, etc) to pay for themselves, because that handful of run-hours can still be worth millions of dollars in annual revenue to a 50 MW power plant or battery system.

Said differently: in PJM, the central operator has the responsibility to analyze the system, determine capacity needs, and guarantees payment to power plant owners to provide capacity. In ERCOT, there’s no guarantee and it falls on the asset owners to make analysis and use their judgement on whether the market has enough capacity or not. Real-time pricing signals are a proof of market constraints.

### ERCOT’s Demand Forecast: Extraordinary -- and Largely Ignored

This difference is particularly interesting as ERCOT also provides demand forecasts. And the outlook is staggering. The [2025 Long-Term Load Forecast](https://www.ercot.com/files/docs/2025/04/29/Long-term-Load-Forecast-RPG.pdf), released April 2025, identified datacenters as the single largest driver of incremental peak growth. Based partly on attestation from Texas transmission service providers, ERCOT projected 77.9 GW of potential datacenter load by 2030 -- more than double the 29.6 GW in the prior year’s outlook, an unprecedented one-year revision.

![](https://substackcdn.com/image/fetch/$s_!Dqhd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F11a823b3-3e3f-4f95-9b4c-6a9ce585f4a9_1800x961.png)

Source: ERCOT

Taken at face value, that forecast implies a structural demand shock on the order of an entire new ERCOT system layered on top of today’s load curve. In reality, no one believed in these numbers, and the market largely ignored them.

Even ERCOT recognized that their forecast was not realized and changed course. In the May 2025 Capacity, Demand and Reserves report, they applied a deliberate haircut: generic requests were discounted to 49.8%, officer-attested requests to 55.4%, and all in-service dates pushed back by 180 days. ERCOT’s internal grid analysts effectively said they would not plan for 100% of what developers claim until shovels actually move.

![](https://substackcdn.com/image/fetch/$s_!sY9J!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1e31a199-bfe3-45c6-9d33-2a6a48cc4fcb_1800x961.png)

Source: ERCOT

But the difference here is that ERCOT’s load forecasts and interconnection queue constraints do not directly drive electricity prices. PJM’s forecasts drive a simulated supply-demand curve, which in turn directly determines the bounds of what system capacity can cost. ERCOT uses its demand forecasts to guide system planning, transmission expansion, and resource adequacy studies -- not as a direct pricing input. ERCOT’s approach embeds skepticism that filters speculative demand before it can influence market outcomes.

### More Datacenter Load, Less Scarcity

The physical system confirms ERCOT’s approach is working. The grid has already experienced record-breaking peaks of over 90 GW in summer 2024 and a spring record of 78.4 GW in May 2025. Hyperscaler demand growth in Texas is already enormous, and there have been no brownouts since.

The prices that energy traders see have not gone to the moon either. Forward prices -- particularly 2026, 2028, and 2030 contracts -- have increased 11-17% in the past year, a notable increase and roughly similar to that of PJM, but no 9x surge in capacity prices.

![](https://substackcdn.com/image/fetch/$s_!bTKf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F30a916ae-8f6f-462a-a184-7622bd295775_1808x1110.png)

Source: Bloomberg

The [2024 Biennial ORDC Report](https://www.ercot.com/files/docs/2024/10/31/2024-biennial-ercot-report-on-the-ordc-20241031.pdf) explains that more online reserves were available than in prior cycles, allowing for steady, calm growth. Solar, wind, batteries, and fossil fuel peakers all came online in sufficient volume to cushion the system. The measurable effect was that the number of hours with scarcity pricing and the total spend on scarcity pricing fell relative to previous years. Energy is now less scarce in ERCOT territory despite the increase in electric demand. It takes more incremental gigawatts of demand to push the system into true scarcity conditions than it did even two years ago. In their public messaging, ERCOT’s concerns about datacenter growth leave out resource scarcity worries.

![](https://substackcdn.com/image/fetch/$s_!bbjn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faeb83ece-fc7c-4534-b358-0b494e4cacef_1740x1100.png)

Source: ERCOT, SemiAnalysis annotation

The forward wholesale price curve tells us that traders believe ERCOT can absorb the growth. They are betting on supply expansion, improved reserves, and [SB 6 curtailment](https://www.bakerbotts.com/thought-leadership/publications/2025/july/texas-senate-bill-6-understanding-the-impacts-to-large-loads-and-co-located-generation) authority to mitigate scarcity in the long term. That skepticism mirrors ERCOT’s own haircutting of developer submissions. The system operator discounts the raw datacenter claims in its forecast; the market discounts them in its forward prices.

ERCOT also moves much faster: one of its key advantages over PJM is that it only covers one state and is not subject to FERC jurisdiction. On the other hand, PJM has to deal with FERC and with 13 states.
