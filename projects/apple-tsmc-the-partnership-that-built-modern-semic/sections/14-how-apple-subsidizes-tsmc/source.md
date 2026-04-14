One of the most misunderstood aspects of the Apple-TSMC relationship is the pricing model. Surface-level analysis assumes a fixed wafer price. The reality is a dynamic risk-sharing agreement that evolves over the lifecycle of a process node.

### The Known Good Die (KGD) Model

When TSMC launches a bleeding-edge node (e.g., N3 for the A17 Pro), yields can be as low as 55% during the initial ramp. A standard wafer pricing model ($20,000/wafer) would be ruinous for Apple if nearly half the chips on each wafer are defective.

The Deal: Apple negotiates to pay only for Known Good Dies (KGD) during the initial ramp. TSMC absorbs the cost of the defects. This effectively aligns incentives: TSMC must improve yield to make money, and Apple is protected from the immaturity of the node.

The Trade-off: Apple commits to enormous volumes (often buying 50-100% of initial capacity) that no other customer can match, effectively funding the R&D and depreciation of the fab.

The Transition: Once yields hit a mature threshold, the contract reverts to standard per-wafer pricing. This incentivizes TSMC to fix yields quickly.

### Binning as Yield Optimization

Apple utilizes its M-series product stack to maximize yield. A defective M3 Max die with a broken GPU core doesn’t go in the trash; it becomes a binned M3 Pro or a lower-tier Max.

A-Series: Less binning flexibility (iPhone volumes require uniformity), though the A18 vs A18 Pro distinction (5-core vs 6-core GPU) suggests aggressive binning is now entering the iPhone lineup to combat N3E yield costs. This allows Apple to use dies with a single GPU defect in the standard iPhone 16.

M-Series: Extreme binning. M3 Max exists in 30-core and 40-core GPU variants. This allows Apple to harvest dies that would otherwise yield losses. This strategy is crucial for maintaining margins on large, expensive dies like the M-series Max and Ultra.

In 2020, shortly after Apple commenced 5nm volume production for the iPhone 12 (A14 chip), Fab 18 reported having just 4 customers. This exclusivity explains how Apple could secure 100% of the initial capacity.

By 2024, as the node matured and yield rates stabilized, the number of customers at Fab 18 exploded to 45.

![](https://substackcdn.com/image/fetch/$s_!vdcu!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F42eb5fd1-d5ca-40e5-bd6d-2653f836848e_2023x1476.png)

![](https://substackcdn.com/image/fetch/$s_!2aUo!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F91b4629f-760f-4e1a-98cc-1c94f1b71680_2218x1488.png)

This trajectory (4 to 14 to 21 to 45) shows the ‘Apple Wave’ thesis:

* Phase 1 (Anchor): A new fab open with very few customers (Apple exclusive).

* Phase 2 (Democratization): After Apple matures the node and captures the “Early Adopter Surplus,” the node opens to AMD, NVIDIA, and Qualcomm.

* Phase 3 (“Platformization”): Apple effectively pays for the R&D of the industry’s leading edge while securing the first 12-18 months of exclusivity.

### TSMC Capex Explosion (Driven by Apple)

TSMC’s capex trajectory reveals three distinct eras. Pre-Apple (2005-2009), annual spending averaged $2.4B. The foundry had no anchor tenant and limited visibility into future demand. Post-Apple (2010-2018), capex climbed to $8B annually as A-series volumes justified larger bets. The EUV era (2019-2022) broke the model entirely. TSMC deployed $98B in four years, exceeding the cumulative $92B spent over the prior 14 years. This acceleration required certainty. Apple’s volume commitments and manufacturing purchase obligations gave TSMC the confidence to make these bets. Without a guaranteed buyer for bleeding-edge nodes, no foundry can justify $30B+ annual capex.

![](https://substackcdn.com/image/fetch/$s_!rHve!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F56125581-9776-4e1f-a532-54afff4fdb76_2224x1113.png)

![](https://substackcdn.com/image/fetch/$s_!TC7Y!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F20b8ef63-eb59-4a38-be6c-8a1f1519d040_2410x591.png)

Apple has effectively financed $73B of TSMC’s leading-edge capacity since the A8 launched on 20nm in 2014, representing 47% of all advanced node capex over that period. This is 1.7x the $43B implied by Apple’s 22-25% revenue share. The premium stems from Apple’s role as sole anchor tenant at node launch: near 100% of 20nm in 2014 and 10nm in 2017, and over 90% of N3 in 2023.

These figures use lifetime utilization weighting, crediting Apple only for its share of each node’s output over a 5-year depreciation cycle rather than assigning full launch-year capex. Even under this conservative methodology, Apple’s contribution dwarfs all other customers combined. TSMC’s cumulative $259B capex through 2025 translates to $83B in Apple-attributed infrastructure, exceeding Apple’s own semiconductor R&D spend over the same period.

Qualcomm, AMD, NVIDIA, and MediaTek collectively account for 25% of TSMC revenue but bear roughly 30% of leading-edge capex burden because they backfill capacity 12-18 months after Apple has absorbed yield risk and funded the initial ramp. The dynamic creates mutual lock-in: Apple gets first access to density and efficiency gains, TSMC gets a guaranteed anchor tenant to de-risk $25-30B annual node transitions.

### TSMC R&D Funding: Apple Role

TSMC’s R&D spending has grown 8x since 2010, from under $1B to $8B in 2025. But R&D intensity tells a different story. In the 2015-2019 period when Apple was the primary driver of leading-edge scaling, TSMC consistently spent 8%+ of revenue on R&D. That ratio has since dropped to under 7%, not because TSMC is investing less, but because AI-driven revenue is scaling faster than the R&D required to support it. Apple funded the hard yards of EUV transition and sub-7nm development; AI customers are now harvesting the returns on that investment at scale.

![](https://substackcdn.com/image/fetch/$s_!TYZW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fee6cebd1-fd21-463d-8ea3-bc1c483eb2ab_2184x1599.png)

### Apple’s Position Among TSMC’s Top Customers

TSMC’s customer concentration has steadily increased over the past two decades, with the top-10 customers growing from 44% of revenue in 2000 to 78% by 2025. Apple has been a primary driver of this concentration. Before 2014, Apple was a negligible contributor to TSMC’s revenue; by 2025, Apple alone represents roughly a quarter of top-10 customer revenue. For most of the 2014-2022 period, Apple grew faster than the average of the other nine top-10 customers, pulling TSMC’s customer mix increasingly toward Cupertino.

That dynamic has now reversed. In 2024 and 2025, non-Apple revenue at TSMC grew at nearly double Apple’s rate, driven by AI accelerator demand from NVIDIA, Broadcom, AMD, and hyperscaler custom silicon. The ex-Apple top-10 cohort, which grew at single-digit rates for much of the 2010s, is now expanding at 40%+ annually. Apple remains TSMC’s largest single customer, but its growth is being outpaced by a coalition of AI-focused buyers who are collectively reshaping the foundry’s revenue base. The customer concentration continues to rise, but the center of gravity is shifting away from smartphones and toward data center silicon.

Apple’s lead is shrinking. In 2020, Apple’s revenue was 4.6x the average of the other top-9 customers. By 2025, that ratio has compressed to 2.9x. Apple is still the largest customer by far, but the gap is closing as AI customers scale.

The 2022 dip is notable. Top-10 concentration actually fell from 74% in 2020 to 68% in 2022 before rebounding. This coincided with the crypto winter and memory correction, which hit several top-10 customers hard. The rebound to 78% by 2025 is AI-driven.

![](https://substackcdn.com/image/fetch/$s_!ruoA!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fde1a3584-a724-4132-8aa5-2431e21ca7a1_2076x1421.png)

![](https://substackcdn.com/image/fetch/$s_!TOEI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2a6ec45b-54c0-4f80-aa71-b199438d84c6_1999x1419.png)

![](https://substackcdn.com/image/fetch/$s_!iCdz!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F43f2a692-06d7-4101-96e4-9ac3cba91af8_1946x1419.png)

Ex-Apple top-10 growth inflected. From 2014-2021, the ex-Apple top-10 cohort grew at single-digit rates most years. In 2023, that flipped to +37%. In 2024, +40%. The acceleration is almost entirely NVIDIA and hyperscaler ASICs.

Concentration is a double-edged sword. With 78% of revenue coming from 10 customers, TSMC is increasingly dependent on a small number of buyers. Apple and NVIDIA alone likely represent 40%+ of total revenue by 2025. Any demand shock from either would be material.
