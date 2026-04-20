Celestial AI is an IP, products, and systems company specializing in optical interconnect solutions for AI scale-up networks. The main goal of the company’s technology is to build photonic devices (modulators, PDs, waveguides, etc.) into interposers coupled with an interface with the outside world (GC with an FAU). The diagram below is a good representation of Celestial AI’s suite of photonics-based interconnect solutions which Celestial AI calls their “Photonic FabricTM” (PF).

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_072.png)

Source: Celestial AI

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_073.png)

Source: Celestial AI

Photonic FabricTM (PF) Chiplets are TSMC 5nm chiplets incorporating die-to-die interfaces like UCIe and MAX PHY, enabling XPU-to-XPU, XPU-to-Switch, and XPU-to-Memory connectivity. They can be co-packaged by customers alongside their XPUs, delivering higher bandwidth density and lower power consumption than CPO products based on electrical SerDes interfaces. Celestial AI develops these chiplets on a per-customer basis to accommodate specific D2D interfaces and protocols. The first generation of PF Chiplet supports a bandwidth of 16 Tbit/s, while the second generation will deliver 64 Tbit/s.

Optical chiplets offer a strong power advantage compared to traditional copper traces. Traditional copper cables with linear SerDes at 224G require ~5 pJ/bit. With two ends required, the total power consumption is ~10 pJ/bit. Celestial AI’s solution requires just ~2.5 pj/bit for the entire electrical-optical-electrical link (plus ~0.7 pJ/bit for the external laser).

Next, the Photonic FabricTM Optical Multichip Interconnect BridgeTM (OMIBTM) is essentially a CoWoS-L style or EMIB style packaging solution. It adds photonics directly onto the embedded bridge in the interposer so that the bridge can move data directly to point of consumption. It offers higher overall chip bandwidth than PF Chiplets, as it is not limited by beachfront constraints.

In traditional interposers or substrates with metal interconnects, placing I/O at the center of the chip is impractical because it would create excessive routing complexity and severe crosstalk issues due to high-density signal congestion. However, with the OMIB optical interposer, Celestial AI is able to place the interposer right beneath the ASIC, bypassing shoreline limitations and enabling faster, more efficient data movement with minimal crosstalk.

Optical interposers allow I/O to be placed anywhere on the chip, as **optical** waveguides experience negligible signal degradation over distance, removing the traditional constraint of shoreline as we know it. They also eliminate crosstalk since light signals in different waveguides do not interfere like electrical signals in densely packed copper traces as they are highly confined within the waveguide core with only a small evanescent field outside in the cladding. This ground-up rearchitecting of I/O design and placement fully takes advantage of the potential that optics provides.

![A screen shot of a computer](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_074.png)

Source: Celestial AI

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_075.png)

Source: Celestial AI, Marvell

The idea of an optical interposer or channeling optical signals through an advanced package has a few similarities to Lightmatter’s solution in that they both route optical signals below the logic chips thereby avoiding shoreline constraints, but there are a few key differences. Celestial AI adopts a photonic bridge that is akin to a silicon bridge (think like the CoWoS-L silicon bridge) whereas Lightmatter uses a large multi-reticle photonic interposer that sits below a number of individual chips. Lightmatter’s concept is more ambitious in scope – aiming for 4,000 mm2 interposer sizes in its M1000 3D Photonic Superchip while also aiming to support optical circuit switching within the interposer and a very high 114 Tbit/s of total aggregate bandwidth.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_076.png)

Source: Celestial AI, Marvell

Lastly, Celestial AI offers the Photonic FabricTM Memory Appliance (PFMA), a high-bandwidth, low-latency scale-up fabric with in-network memory built on TSMC 5nm with 115.2T total bandwidth that can connect 16 ASICs at 7.2T scale-up bandwidth per each ASIC. Notably, PFMA is the world’s first silicon device with on-die optical I/O located in the center of the chip, leaving scarce perimeter physical I/O’s for memory controllers. This positions the PFMA as a “warm” memory tier between host CPU memory and storage for KVCache offloading.

A key differentiator of Celestial AI’s technology is its use of an Electro Absorption Modulator (EAM). Part 3 of this article described in more detail how EAMs work and discusses the advantages and trade-offs when it comes to EAM. We repeat the bulk of this discussion here as understanding the pros and cons of EAMs is key to understanding Celestial’s go to market.

EAMs have several advantages compared to MRMs and MZIs:

* Clearly – both EAMs and MRMs have control logic and heaters that act to stabilize both against variations in temperatures, but EAMs have fundamentally less sensitivity to temperature. Compared to MRMs, EAMs have much better thermal stability above 50° C while MRMs are very sensitive to temperature. A typical stability of 70-90 pm/C for MRMs mean that a 2° C variation shifts resonance by 0.14nm, well beyond the 0.1nm resonance shift at which MRM performance collapses. In contrast, EAMs can tolerate an instantaneous temperature shift of up to 35° C. This tolerance is important in particular for Celestial AI’s approach as their EAM modulator resides within an interposer beneath a high-XPU power compute engine that dissipates hundreds of watts of power. EAMs can also tolerate high ambient temperature ranges of around 80° C which may be applicable for chiplet applications which sit next to the XPU and not beneath it.

* Compared to MZIs, EAMs are much smaller in size and consume less power as the relatively large size of MZIs requires a high voltage swing, amplifying the SerDes to achieve a swing of 0-5V. Mach Zender Modulators (MZMs) are on the order of ~12,000µm2, GeSi EAMs at around 250µm2 (5x50µm) with MRMs at between 25µm2 and 225µm2 (5-15µm2 in diameter). MZIs also require more power usage for the heaters needed to keep such a large device at the desired bias.

On the other hand, there are a few drawbacks in using GeSi EAMs for CPO:

* Physical modulator structures built on Silicon or Silicon Nitride such as MRMs and MZIs have been perceived to have far greater endurance and reliability than GeSi based devices. Indeed, many worry about the reliability of GeSi based devices given the difficulty of working with and integrating Germanium-based devices, but Celestial argues that GeSi based EAMs, which are essentially the reverse of a Photodetector, are a known quantity when it comes to reliability given the ubiquity of photodetectors in transceivers today.

* GeSi modulators’ band edge is naturally in the C-band (i.e. 1530nm-1565nm). Designing quantum wells to shift this to the O-band (i.e. 1260-1360nm) is a very difficult engineering problem. This means that GeSi based EAMs will likely form part of a book-ended CPO system and cannot easily be used to participate in an open chiplet-based ecosystem.

* Building out a laser ecosystem around C-band laser sources could have diseconomies of scale when compared to using the well-developed ecosystem around O-band CW laser sources. Most datacom lasers are built for the O-band but Celestial points out that there are considerable volumes of 1577nm XGS-PON lasers manufactured. These are typically used for consumer fiber to the home and business connectivity applications.

* A SiGe EAM has an insertion loss of around 4-5dB vs 3-5 dB for both MRMs and MZIs. While MRMs can be used to directly multiplex different wavelengths, EAMs require a separate multiplexer to implement CWDM or DWDM, adding slightly to the potential loss budget.

Overall, Celestial AI has been working to innovate its custom links – they don’t rely on any gearbox components, offering better latency and power efficiency, and are adaptive to different types of protocols. As mentioned earlier, Celestial AI is the only major player that is mainly using EAMs for modulation. One key implication is that they will also have some work ahead of them integrating their EAM design into a foundry whereas other CPO companies can lean on TSMC COUPE where MRMs and related heaters are already part of the PDK.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_077.png)

Source: Celestial AI

In the immediate term, Celestial AI is committing to an ambitious timeline for the release of the chiplet. Marvell announced in the transaction summary that their estimated revenue run rate from Celestial at the end of January 2028 (the end of Marvell’s Fiscal Year 2028 – i.e. F1/28) is expected to reach $500 million. At the Barclay’s Global Technology Conference, they further added that this run rate is expected to double to $1B by the end of Calendar Year 2028 (with most of CY28 falling into Marvell’s FY ending Jan 2029 – i.e. F1/29), implying a 2-year period from now to the end of 2027 for the product to achieve commercial viability.

As part of the deal terms, an additional $2.25B of payout to Celestial AI’s equity holders is contingent upon the company achieving a cumulative revenue of at least $2.0 billion by January 2029 (the end of Marvell’s Fiscal Year 2029 – i.e. F1/29). This first milestone towards that full payout is achieving $500M of cumulative revenue by January 2029 for one third of the payout. The $1B revenue run rate expected exiting F1/29 is half of the earn-out amount – implying that Celestial will need to add additional customers to the order book to achieve the $2B earn-out target.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_078.png)

Source: Celestial AI, Marvell

In connection with the Celestial AI acquisition, Marvell filed an [8-K report](https://www.sec.gov/Archives/edgar/data/1835632/000119312525305271/d81371d8k.htm) on December 2, 2025 issuing Amazon warrants with an exercise price of $87.0029 through December 31, 2030. These warrants vest “based on Amazon’s purchases of Photonic Fabric products, indirectly or directly, through December 31, 2030”, strongly suggesting that AWS’s Trainium will be the target product as this starts to ramp in late 2027. At Marvell’s Industry Analyst Day, Celestial AI discussed how a major hyperscaler selected them for optical interconnectivity for advanced AI systems that will move into volume production in that hyperscaler’s next generation processor. This, together with the earn-out timing and product revenue guidance in the transaction summary suggests that Celestial AI is targeting to deploy its solution within Trainium 4.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_079.png)

Source: Marvell SEC Filings

Let’s conclude our discussion on Celestial AI by elaborating further on its first scale-up solutions to come to market which will be oriented around its 16Tbit/s Photonics Link that will be connected to a chiplet. An FAU is connected to the channel waveguides via the grating coupler. A Scale-up switch ASIC – possibly Marvell’s 115.2T scale-up ASIC – will be optically connected to an XPU via the Photonics link and the PF chiplet. Though Celestial expects most of its initial go-to-market revenue to be contributed by its chiplet, it positions itself as a systems company and has pitched several optical-based memory expansion solutions that can come to market after this first scale-up networking solution.

Using optics to increase the scale-up world size through multiple switch layers is not a new concept, though of course it has yet to come close to being productized. Such a concept could have topologies that mirror the NVL576 concept of the GB200, where there are two switch layers and each switch layer is connected to the other via OSFP transceiver modules and optical fiber. Celestial AI’s approach of using multiple switch layers is similar but skips the use of actual transceivers.

The biggest difference from the NVL576 concept, however, is that the scale-up ASIC can double as both a router and a memory endpoint, whereas an NVSwitch only routes high-bandwidth links between GPUs. This is an important distinction because Celestial AI’s pitch is that its scale-up solution is able to sidestep the silicon beachfront constraint that limits the number of HBM stacks one can attach to the XPU.

To achieve this, the HBM stack attached to the XPU is replaced with a chiplet that connects to the Photonic Fabric, which is a shared HBM pool. The shared HBM pool is a Photonic Fabric Appliance (PFA) a 2U-rack-mountable system made up of 16 Photonic Fabric ASICs consisting of one port each.

Each ASIC is a 2.5 layer package integrated with two 36GB HBM3E memory and eight external DDR5.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_080.png)

Source: [Celestial AI](https://arxiv.org/pdf/2507.14000)

The optical I/O (Photonic Fabric IP) is mounted in the middle of the ASIC, rather than at the beachfront, which frees up the shoreline for other use cases.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_081.png)

Source: [Celestial AI](https://www.youtube.com/watch?v=Rchp-QjdCgE)

Zooming out, each PFA module is a 16-radix switch that can support up to 16 XPUs. Rather than have each XPU fan-out to all 16 ports, all-to-all connectivity occurs inside the switch box, where the Fiber Attach Unit (FAU) connected to each Switch ASIC fans out to each of the 16 switch I/Os. As such, every XPU only has one Fiber link to one switch port outside of the box.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_082.png)

Source: [Celestial AI](https://arxiv.org/pdf/2507.14000)

By placing memory external to the XPU and within a shared switching interface, data is aggregated and subsequently accessed from the shared memory pool by every XPU in an all-reduce communication collective.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_083.png)

Source: [Celestial AI](https://arxiv.org/pdf/2507.14000)
