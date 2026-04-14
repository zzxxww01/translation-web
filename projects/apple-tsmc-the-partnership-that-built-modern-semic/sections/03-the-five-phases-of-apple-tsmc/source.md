![](https://substackcdn.com/image/fetch/$s_!0uZo!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F69fbfcbe-e7c8-4de6-899d-8cd0d36222ea_2058x769.png)

### Phase 1: Why Apple started making its own chips and Apple’s courtship

The original iPhone launched in 2007 relied heavily on Samsung components. Samsung supplied the application processor, display, and flash memory. While making its chips an inevitable destiny for Apple, a few things accelerated the journey.

**First**, Apple’s key supplier Samsung entered smartphones 18 months after iPhone launched, ending up in a legal battle with Apple as early Galaxy S designs resembled iPhones. The unease grew with each Samsung’s release and its growing competitive position smartphones, pushing Apple to look for alternatives.

**Second**, the rise of the Wintel model (Android plus Qualcomm) in smartphones in the 2010s worried Apple that commodity chips could erode its differentiation in software and affect its premium status. Jobs made the call in 2008: Apple would design its own chips. But manufacturing requires 10s of billions in fabs. So Apple adopted a fabless systems company approach.

**Third**, workload optimization: designing for iOS specifically, rather than generic benchmarks, enabled meaningful performance-per-watt advantages.

**Fourth**, power efficiency: iPhone’s thin form factor demanded performance-per-watt leadership that merchant silicon couldn’t deliver.

**Fifth**, margins: eliminating supplier markups over time would capture billions in additional profit.

Apple wanted to control the primary technologies used in its devices. The $278M P.A. Semi acquisition in April 2008 served as a stepping stone. Dan Dobberpuhl, creator of Alpha and StrongARM, had assembled 150 of the best low-power chip engineers in the world. Among them was Johny Srouji, an Israeli engineer from Intel and IBM. He now runs Apple Silicon as SVP of Hardware Technologies.

> *First and foremost, if we do this, can we deliver better products? That’s the No. 1 question. It’s not about the chip. Apple is not a chip company.*
>
> *- Johny Srouji, Apple SVP of Hardware Technologies*

Following P.A. Semi, Apple acquired ultra-low-power chip design company Intrinsity for $121M in 2010 Apple fielded its first custom smartphone applications processor (AP), the A4, in iPhone 4 in September 2010. While it was still manufactured by Samsung, Apple intensified its search for a manufacturing partner who wasn’t also their competitor.

#### The Decision That Changed Computing History: TSMC vs Samsung vs Intel Decision

Between 2010 and 2014, the “courtship” phase, Apple explored alternatives to Samsung via “Project Azalea,” considering GlobalFoundries and even building its own fabs.

Enter Intel and TSMC, two of the leading fab options for Apple. Discussions with Intel were unsuccessful as then CEO Paul Otellini declined, believing the volume wouldn’t justify the low margin and rigorous demands Apple placed on suppliers. At TSMC, Morris Chang accepted the challenge, viewing it as a growth opportunity rather than a margin drag.

Apple COO Jeff Williams met with Chang over dinner and pitched TSMC to build 20nm capacity. At that time, TSMC was shifting focus and investment to 16nm. The capital and capacity numbers Apple asked were unheard of; they went so far as suggesting TSMC cut its dividend to fund the fab buildout. TSMC made the bet. They were able to fund the fabs with debt. At the time of the initial decision, success was far from a sure thing for either side.

### Phase 2: Apple Made TSMC (2014-2020)

Apple’s A8 chip launched in 2014, and TSMC never looked back. Over the next six years, Apple drove TSMC to invest $60-80 billion in leading-edge capacity. Apple’s volume justified every major node transition: N16, N7, N5. Without the iPhone’s annual 200M unit baseline, TSMC could not have afforded the R&D velocity that left Intel and Samsung behind.

![](https://substackcdn.com/image/fetch/$s_!nT85!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F47553882-9fa3-4886-aa11-d4452f22c7b0_2052x1518.png)

![](https://substackcdn.com/image/fetch/$s_!Yiqb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd291825b-404c-4788-aab4-e2c4d580bfb6_2029x1529.png)

![](https://substackcdn.com/image/fetch/$s_!VYK-!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fef47eb93-cb92-4fc3-8c57-06eae322a16f_2184x1599.png)

In 2016, Apple funded the development of InFO (Integrated Fan-Out) packaging. This allowed for thinner phones with better thermals and created the advanced packaging ecosystem that now powers AI accelerators.

[In a candid interview](https://www.acquired.fm/episodes/tsmc-founder-morris-chang), Morris Chang revealed that Tim Cook later told him:

> *Intel just does not know how to be a foundry.*

At the core there are cultural differences: Intel, trapped in its product success, couldn’t foresee the massive Arm-based foundry market; TSMC offered servitude, flexibility, and a willingness to ‘bet the company’ on Apple’s success. TSMC built dedicated capacity, accepted Apple’s engineers into their labs, and aligned their roadmap with the iPhone’s annual cycle. This cultural alignment, TSMC’s willingness to customize versus Intel’s standardized product approach, remains Intel’s biggest hurdle in its IDM 2.0 pivot today.

[Apple initially said to have offered 40% gross margin to TSMC](https://www.acquired.fm/episodes/tsmc-founder-morris-chang), which was in line with TSMC’s margin then. Current gross margin from Apple business is significantly higher than the initial 40%.

Despite investing in dedicated 20nm capacity for Apple, TSMC did not even receive a majority share of Apple’s foundry business at first. It had to share a 14nm slot with Samsung in 2015 with the latter getting >60% share. TSMC management was shocked, but responded by accelerating their next-gen 10nm process.

Ultimately, TSMC won because it demonstrated the ability to scale 20nm ahead of the competition, proving it could handle the iPhone’s massive volume spikes. The “Night Hawk” team at TSMC worked 24/7 to solve yield issues, establishing the operational trust that persists today.

What if Apple chose Intel in 2014? Intel would have $15B+/year guaranteed foundry revenue. TSMC, without that revenue, would probably not have achieved dominance anywhere near what it has today. Intel Foundry would be 10 years more mature. It’s the biggest misstep in the history of chip foundries.

### Phase 3: Mutual Lock-In (2020-2023)

By 2020, the partnership had evolved from mutually beneficial to co-dependence. Apple could no longer leave. No other foundry on earth could produce M-series and A-series chips at the required volume and yield. Samsung’s 3nm yields were 30-40% versus TSMC’s 80%+. The switching cost was estimated at $2-5 billion in redesign and requalification alone.

TSMC could not lose Apple. The iPhone brought 22-25% of total revenue and filled 70%+ of 3nm capacity. Apple orders were known three years in advance, allowing TSMC to plan capex with the confidence of a utility company.

![](https://substackcdn.com/image/fetch/$s_!HMKq!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd65f4565-f831-4d47-9b4c-694760524e65_2106x757.png)

![](https://substackcdn.com/image/fetch/$s_!uSih!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8d2fb8af-38d8-4f06-b8b8-cb361db6f7c0_2109x754.png)

![](https://substackcdn.com/image/fetch/$s_!_7t3!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0f07975e-d2f2-4742-9214-0a645bef2ecd_1999x938.png)

A more serious risk is timing. Apple’s product cadence is synchronized to TSMC’s node roadmap. Moving to Intel or Samsung would mean 2-3 years of inferior products while yield learning catches up. Product upgrade cycles, most importantly the annual iPhone refresh synced with holidays, would also be at risk.

### Phase 4: Diversified Dependence (2023-Present): The Changing Power Dynamic: Is Apple Still the Kingmaker?

For years, Hsinchu and Cupertino worked as a single team to relentlessly advance Moore’s Law. Apple’s One Team approach embedded hundreds of engineers at TSMC’s headquarters, effectively treating the foundry as an extension of Cupertino. This team co-developed Process Design Kits (PDKs), ensuring that when a new node like 5nm launched, Apple’s designs were perfectly synthesized to the transistor characteristics.

However, the rise of generative AI is shifting TSMC’s customer mix. While Apple remains the largest single customer by revenue, its relative influence is diluting as the High-Performance Computing (HPC) segment, driven by NVIDIA, AMD, and hyperscalers, outgrows. In Q1 2020, smartphones accounted for 49% of TSMC’s revenue, while HPC was 30%. By Q3 2025, HPC had skyrocketed to 57%, relegating smartphones to a secondary growth driver.

While Apple also contributes to TSMC’s HPC segment through its tablet/PC chips, the uptake of AI offered TSMC a new stream of customers who are voracious for advanced node capacity. While AI accelerators moved 1 year cadence, they are still on n-1 node largely. Apple will still be the anchor customer on N2 (2nm) but it will see stiff competition from others competing for capacity. On A16 (1.6nm), HPC players are likely to beat Apple as it is a more HPC centric node.

Apple acts as the predictable baseline that justifies the massive, fixed costs of new fabs. NVIDIA provides the high-margin upside that drives profitability growth. TSMC now has two anchor tenants instead of one.

![](https://substackcdn.com/image/fetch/$s_!CVJM!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff3b95f45-de84-447b-90af-77247fc8c80f_2077x1421.png)

#### The AI Divergence: Wafers vs. Packaging

The distinction lies in what these customers are buying. Apple buys leading-edge logic wafers (N3, N3E) and InFO (Integrated Fan-Out) packaging. NVIDIA buys logic wafers (N4, N5) on a custom process a node or 2 behind leading edge but is critically dependent on CoWoS (Chip-on-Wafer-on-Substrate) packaging.

Apple was TSMC’s first advanced packaging customer at scale. InFO revenue grew from $1.8B in 2018 to >$3.5B in 2024, driven entirely by A-series and M-series chips. But CoWoS, TSMC’s AI packaging platform, has surpassed it. CoWoS revenue hit $9.6B in 2025, 2.5x InFO, fueled by Nvidia and AMD demand.

![](https://substackcdn.com/image/fetch/$s_!3bJr!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb421a17a-6967-40f7-b81d-01cb526a084f_2074x1421.png)

![](https://substackcdn.com/image/fetch/$s_!Vy_p!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb53c83b2-99cc-439f-ac68-2db99feae73b_2211x1456.png)

This creates a bifurcation in TSMC’s capacity planning. Apple is no longer the sole driver of capex. TSMC’s capital expenditure is now split between chasing Moore’s Law (2nm for Apple) and chasing packaging density (CoWoS-L for NVIDIA). Apple acts as the predictable baseline that justifies the massive fixed costs of new fabs, while NVIDIA provides the high-margin upside that drives profitability growth. The power dynamic has shifted from a unipolar world (Apple) to a bipolar world (Apple + AI), where TSMC can now arbitrage demand between the two sectors to maintain pricing power.

### Phase 5: Beyond TSMC (2027+)

Apple is actively exploring alternatives.

Intel’s 18A-P process (shipping late 2026) represents the first theoretically viable alternative since Apple left Samsung in 2016. Apple could qualify Intel, initially for lower-risk silicon such as base M-series, and yield well. That would give Intel reference design wins and Apple supply chain diversification without risking core products.

Intel missed Apple once before in 2014. The door hasn’t fully closed. The key question is: would Apple actually use it?

![](https://substackcdn.com/image/fetch/$s_!Mkbg!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fad4827a2-9eae-4c49-a03d-f03042610f99_1878x915.png)

![](https://substackcdn.com/image/fetch/$s_!3RG5!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F784cd775-1a9c-48be-9969-5bd5e6bcbad3_2328x633.png)

But, 18A-P on base M-series chips makes sense. If Apple were to shift 20% of base M-series wafers to Intel 18A-P, it would imply $630M in foundry revenue for Intel at an $18k ASP.

Base M-series die sizes tend to be in the range of 150-170mm² and could yield 70%+ on 18A-P (based on current Panther Lake, which has a similar die size).

While Intel’s current 18A yields are lower than TSMC’s N3 for a 150mm² die (>80%), Intel offers pricing leverage, potential 14A optionality, and US-based wafer/packaging capabilities for Apple.

Intel 18A-P offers 8% higher performance/watt and similar density to 18A with backside power delivery (PowerVia).

There are a few lower impact possibilities too: while the Intel16 mature node in its Ireland fab could address DTV and connectivity apps, we doubt the capacity is enough to serve Apple. Apple could qualify Intel for lower-risk silicon: WiFi/Bluetooth, display drivers, or power management. That would give Intel reference design wins and Apple supply chain diversification without risking core products.

#### Apple’s Real Diversification Strategy

Apple’s actual foundry diversification isn’t about moving leading-edge A-series/M-series away from TSMC. Non-Pro versions, Peripheral chips and packaging are all candidates for foundry diversification.

![](https://substackcdn.com/image/fetch/$s_!g79U!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1a3272c5-453b-4dae-9970-bee96c35b5f9_2316x1026.png)

**Where diversification makes sense: PMICs, Display Drivers**, **Audio/Connectivity**

**Where diversification is Challenge: leading-edge A-series and M-series**

#### Apple’s Reengagement with Samsung LSI/Foundry

After leaving Samsung in 2016, Apple went exclusive with TSMC. Apple’s diversification strategy is about **reducing supply chain risk for non-critical chips**.

Apple has signed a strategic deal with Samsung Foundry to manufacture advanced CMOS Image Sensors (CIS) at Samsung’s Austin, Texas facilities, breaking Sony’s decade-long exclusivity on iPhone image sensors. Leveraging Samsung’s US fabs helps Apple meet internal “American Manufacturing” targets without relying solely on TSMC Arizona, which is focused on leading-edge.

We estimate Samsung could capture 20-30% of Apple’s CIS volume by 2027 (150M-200M sensors annually), offering $1-$1.5B foundry revenue to Samsung.

![](https://substackcdn.com/image/fetch/$s_!zvqD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffa633537-4571-40e0-88ac-6a5e45b9625e_1770x1211.png)
