Nvidia provided a long-awaited update on its Kyber rack form factor, the latest addition to the lineup after Oberon having first been previewed as a prototype at GTC 2025. As a prototype, the rack architecture has continued to evolve, and we notice some changes. First, each compute blade has densified, with 4x Rubin Ultra GPU and 2x Vera each. There are a total of 2 canisters of 18 compute blades which amounts to 36 compute blades total for 144 GPUs in a rack. The initial Kyber design featured 2 GPUs and 2 Vera CPUs in one compute blade, with a total of 4 canisters of 18 compute blades each.

The details below are based on the Rubin Kyber prototypes, but Rubin Ultra will be redone.

![](https://substackcdn.com/image/fetch/$s_!57WO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6e91ff96-9d44-4d04-8a1f-eeb1575b235d_3000x4000.jpeg)

Source: SemiAnalysis

Each switch blade is also double in height vs the GTC 2025 prototype, with 6 NVLink 7 switches per switch blade, and 12 switch blades per rack, amounting to a total of 72 NVLink 7 switches per Kyber rack. The GPUs are connected all-to-all to the switch blades via 2 PCB midplanes or 1 midplane per canister.

![](https://substackcdn.com/image/fetch/$s_!lj22!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4c5a1ad2-cfca-47a0-be02-f39b150e8df4_3000x4000.jpeg)

*Kyber midplane PCB (GPU side). Source: Nvidia, SemiAnalysis*

For Rubin Ultra NVL144 Kyber, [there will be no CPO used for scale up as we have told clients multiple times](https://semianalysis.com/institutional/multi-vertical-note-kyber-cpo-sku-will-be-a-low-volume-test-rack/), despite rumors from other analysts suggesting scale-up CPO introduction for Kyber. However, optics for NVLink are coming and will be progressively phased in. Scale-up CPO will first be used for the Rubin Ultra NVL 576 system to connect between 8 Oberon form factor racks, forming a two-layer all-to-all network. A copper backplane will still be used for scale-up networking within the racks however. This is still for low volume / testing purposes.

Moving back to the Kyber Rack, each Rubin Ultra logical GPU offers 14.4Tbit/s uni-di of scale-up bandwidth, using an 80DP connector (72 DPs used x 200Gbit/s bi-di channel = 14.4Tbit/s) per GPU for connectivity to the midplane board. Connecting all 144 GPUs in an all-to-all network will require 72 NVLink 7.0 Switch Chips running at 28.8Tbit/s uni-di of aggregate bandwidth each.

![](https://substackcdn.com/image/fetch/$s_!028i!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa6507cbc-367c-4f8e-9f8a-6fcbccf61aa3_1513x655.png)

Source: SemiAnalysis

In the Kyber Switch Blade picture below, we can see that there are 2 separate PCBs carrying 3 Switches each. The switch blade should have 6 152DP connectors, 3 connectors serving each midplane board. The picture is a prototype blade using less dense connectors, which is why there are 12 connectors instead of the 6 that we expect in the production version.

![](https://substackcdn.com/image/fetch/$s_!ET6V!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1bef24fc-b8ed-4652-a928-7abd4cf2d496_4000x3000.jpeg)

Source: Nvidia, SemiAnalysis

Each 28.8T NVLink Switch has 144 lanes of 200G (simultaneous bi-directional) which means each Switch has 24 lanes of 200G going to each connector. Copper flyover cables are used to connect each switch to the midplane, as the distances involved are too long for PCB traces. This is also why the switches are further away from the midplane, to provide space for the routing of the flyover cables.

![](https://substackcdn.com/image/fetch/$s_!-biX!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F376fc839-5860-4555-a18c-3b591ec13156_1582x1372.png)

Source: SemiAnalysis [Networking Model](https://semianalysis.com/ai-networking-model/)

Each NVLink Switch Chip connects via flyover cables to the connector (144 DPs used x 200 Gbit/s bi-di channel = 28.8Tbit/s) connectors at the edge of the switch blade, and these connectors plug into the midplane board. Nvidia is looking into using co-packaged Copper to reduce loss further, in case NPC doesn’t work. As far as we know the Nvidia is telling supply chain to go for fully co-packaged copper.

#### Rubin Ultra NVL288

Though not officially discussed by Nvidia at GTC 2026, an NVL288 concept has been explored within the supply chain. This would entail two NVL144 Kyber racks placed adjacent to each other, with a rack-to-rack copper backplane used to connect the two racks. One possibility is that all 288 GPUs are connected all to all, but this would require higher radix switches than the current NVLink 7 switches which only offer a maximum radix of 144 ports of 200G.

If Rubin Ultra NVL288 is deployed, each Rubin Ultra GPU will have a scale-up bandwidth of 14.4Tbit/s uni-di, requiring 144 DPs of cables to connect the NVLink 7 switches. 72 DPs per GPU times 288 GPUs means a total of 20,736 additional DPs required to connect this larger world size domain. This entails a lot of cables, so it is an upper bound of how much cable content could be used.

The radix of the 28.8T NVLink Switch limits the number of GPUs that each switch can connect while still providing for cross-rack connectivity. Either a higher radix switch will have to be used - or there will have to be a degree of oversubscription in this architecture while potentially adopting a dragonfly-like network topology. This would also require fewer DPs worth of copper cables.

![](https://substackcdn.com/image/fetch/$s_!YbDc!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faddf00bd-ed41-47b8-864e-35e96b6768c1_1613x1158.png)

Source: SemiAnalysis

All current evidence in the supply chain points to NVSwitch 7 being the same bandwidth as NVSwitch 6, but that is seems a bit illogical to be frank. Our belief is that NVSwitch 7 is actually 2x the bandwidth and radix of NVSwitch 6, so all-to-all can be done, and architecturally that makes the most sense from a systems perspective.

#### Rubin Ultra NVL576

To push the scale up world size beyond 144 GPUs and across multiple racks, optics are needed as we are approaching the maximum compute density that is within the reach of copper. Rubin Ultra NVL576 is now on the roadmap with 8 racks of lower density Oberon.

![](https://substackcdn.com/image/fetch/$s_!kVKx!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fee215fef-65ff-41ce-be3d-1a54c3af2334_2449x1037.png)

Source: SemiAnalysis

Optics will be required for the inter-rack connections, though strictly speaking it isn’t confirmed whether this will be with pluggable optics or with CPO, though CPO seems much more likely. The current Blackwell NVL576 prototype “Polyphe” uses pluggable optics.

We have [shown a concept of NVL576 for GB200 previously](https://newsletter.semianalysis.com/i/175661160/gb200-nvl576) with pluggable optics to interconnect the second layer of NVLink switches. The use of pluggables contributed to an enormous increase in BOM cost that made the system untenable from a TCO perspective for a switched all-to-all. However, it is plausible that Rubin Ultra NVL576 will be rolled out in test volumes before Feynman NVL 1,152, where we will see actual volume ramp of scale-up CPO.

The downstream implications of this are exposed in our institutional research, trusted by all major hyperscalers, semiconductor companies, and AI Labs, at sales@semianalysis.com

#### Feynman

While not much is known about Feynman, the Keynote sneak peek was enough to tell us Feynman will be exciting, with three major technical innovations all being pushed in a single platform: [Hybrid bonding/SoIC](https://newsletter.semianalysis.com/p/hybrid-bonding-process-flow-advanced?utm_source=publication-search), A16, [CPO](https://newsletter.semianalysis.com/p/co-packaged-optics-cpo-book-scaling?utm_source=publication-search), and [custom HBM](https://newsletter.semianalysis.com/i/174558655/custom-base-die).

While Feynman adopting CPO is on the roadmap, the question is to what extent? Will in-rack interconnectivity be copper based or optical? We will show possible configurations behind the Paywall. **Vera ETL256**

CPU demand is rising as AI workloads require more data handling, preprocessing, and orchestration beyond GPU compute. Reinforcement learning further increases demand, with CPUs running simulations, executing code, and verifying outputs in parallel. As GPUs scale faster than CPUs, larger CPU clusters are needed to keep them fully utilized, making CPUs a growing bottleneck.

The Vera standalone rack addresses this directly, achieving unprecedented density by fitting 256 CPUs into a single rack — a feat that necessitates liquid cooling. The underlying rationale mirrors the NVL rack design philosophy: pack compute tightly enough that copper interconnects can reach everything within the rack, eliminating the need for optical transceivers on the spine. The cost savings from copper more than offset the additional cooling overhead.

![](https://substackcdn.com/image/fetch/$s_!KfPw!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc9e8a2b9-8417-41bc-aa32-1072b2e68fc0_3000x4000.jpeg)

Source: SemiAnalysis

Each Vera ETL rack consists of 32 compute trays, 16 above and 16 below, arranged symmetrically around four 1U MGX ETL switch trays (based on Spectrum-6) in the middle. The symmetric split is deliberate: it minimizes cable length variance between compute trays and the spine, keeping all connections within copper reach. From each switch tray, rear-facing ports connect to that copper spine for intra-rack communication, while 32 front-facing OSFP cages provide optical connectivity to the rest of the POD.

Networking within the rack uses a Spectrum-X multiplane topology, distributing 200 Gb/s lanes across the four switches to achieve full all-to-all connectivity while maintaining a single network tier. With each compute tray housing 8 Vera CPUs, the result is 256 CPUs per rack, all interconnected over Ethernet through a single, flat network.

![](https://substackcdn.com/image/fetch/$s_!UMo8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F31febbf5-a0ec-4218-b2d0-e95e40704213_4000x3000.jpeg)

Source: SemiAnalysis

![](https://substackcdn.com/image/fetch/$s_!At98!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F91ab19c1-1ceb-4b0b-a13e-6de00121eebd_1427x199.webp)

Source: [Nvidia](https://developer.nvidia.com/blog/nvidia-vera-rubin-pod-seven-chips-five-rack-scale-systems-one-ai-supercomputer/)
