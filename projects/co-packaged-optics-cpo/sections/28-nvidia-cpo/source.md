At GTC 2025, Nvidia debuted their first CPO-based switches for scale-out networks. Three different CPO-based switches were announced. We will walk through each of them in turn, but we first present a neat table aggregating all the important specifications:

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_045.png)

Source: SemiAnalysis

### Quantum-X Photonics

The first CPO switch to come to market by 2H 2025 will be the Quantum X800-Q3450. It features 144 Physical MPO ports which enables 144 logical ports of 800G or 72 logical ports of 1.6T, for aggregate bandwidth of 115.2T. Its resemblance to a spaghetti monster has the authors’ stomachs rumbling.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_046.png)

Source: Nvidia

The Quantum X800-Q3450 achieves this high radix and high aggregate bandwidth by using four Quantum-X800 ASIC chips with 28.8 Tbit/s bandwidth each in a multi-plane configuration. In this multi-plane configuration, each physical port is connected to each of the four switch ASICs, allowing any physical port to talk to another one by spraying the data across all four 200G lanes via the four different switch ASICs.

When it comes to the maximum cluster size for a three-layer network, this delivers the same end result as theoretically using four times as many 28.8T switch boxes but with 200G logical port sizes – both allow a maximum cluster size of 746,496 GPUs. This difference is that when using the X800-Q3400 switch, the shuffle happens neatly inside the switch box, while setting up the same network with discrete 28.8T switch boxes will require far more individual fiber cables going to a greater number of destinations.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_047.png)

Source: SemiAnalysis

Each ASIC in the Quantum-X800-Q3450 is surrounded by six detachable optical sub-assemblies, with each sub-assembly housing three optical engines. Each optical engine delivers 1.6 Tbit/s of bandwidth, resulting in a total of 18 optical engines per ASIC and an aggregate optical bandwidth of 28.8 Tbit/s per ASIC. Note that these sub-assemblies are detachable, so purists may consider this to be technically “NPO” not strictly “CPO.” While there is a bit of extra signal loss associated with the detachable OE, in effect we believe this will not considerably impact performance.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_048.png)

Source: Nvidia

Each engine operates with 8 electrical and optical channels, driven by 200G PAM4 SerDes on the electrical side and on the optical side, 8 Micro-Ring Modulators (MRMs) use PAM4 modulation to achieve 200G per modulator. This design choice was one of the big takeaways of the announcement: that Nvidia and TSMC can ship 200G MRMs in production. This matches the fastest MZMs today and disproves the industry notion that MRMs are limited to NRZ modulation. It’s quite an impressive engineering achievement by Nvidia to reach this milestone.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_049.png)

Source: Nvidia

Each optical engine integrates a Photonic Integrated Circuit (PIC) built on a mature N65 process node, and an Electronic Integrated Circuit (EIC) fabricated on an advanced N6 node. The PIC leverages the older node because it contains optical components such as modulators, waveguides, and detectors—devices that do not benefit from scaling, and often perform better at larger geometries. In contrast, the EIC includes drivers, TIAs, and control logic, which benefit significantly from higher transistor density and improved power efficiency enabled by advanced nodes. These two dies are then hybrid bonded using TSMC’s COUPE platform, enabling ultra-short, high-bandwidth interconnects between the photonic and electronic domains.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_050.png)

Source: Nvidia

Two copper cold plates sit atop the ASICs in the Quantum-X800-Q3450 as part of a closed-loop liquid cooling system that efficiently dissipates heat from each of the switch ASICs. The black tubing connected to the cold plates circulates coolant fluid, helping to maintain thermal stability. This cooling system is essential in maintaining thermal stability not only for the ASICs but also for the adjacent, temperature-sensitive co-packaged optics.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_051.png)

Source: Nvidia

### Spectrum-X Photonics

Spectrum-X Photonics is set for release in the 2nd half of 2026, with two separate switch configurations products to be released, an Ethernet Spectrum-X variant of the X800-Q3450 CPO switch with 102.4T aggregate bandwidth, the Spectrum 6810 offering 102.4T aggregate bandwidth, and its larger cousin the Spectrum 6800 offering 409.6T aggregate bandwidth by using four discrete Spectrum-6 multi-chip modules (MCMs).

The Quantum X800-Q3450 CPO switch utilizes four discrete switch packages connected to the physical in a multi-plane configuration, and each switch package is a monolithic die containing the 28.8T switch ASIC together with required SerDes and other electrical components. In contrast, Spectrum-X Photonics switch silicon is a multi-chip module (MCM) with a much larger reticle size 102.4T switch ASICs at the center, surrounded by eight 224G SerDes I/O chiplets – two on each side.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_052.png)

Source: Nvidia

Each Spectrum-X photonics multi-chip module switch package will have 36 optical engines in a single 102.4T switch package. This package will use Nvidia’s second generation optical engine with 3.2T bandwidth, with each optical engine having 16 optical lanes of 200G each. Note that only 32 optical engines are active, with the additional 4 being there for redundancy purposes in case an OE fails. This is due to the OEs being soldered on the substrate, so they are not easily replaceable.

Each I/O chiplet delivers 12.8T of total unidirectional bandwidth, comprising of 64 SerDes lanes, and interfaces with 4 OEs each. This is what allows the Spectrum-X to deliver far more aggregate bandwidth than Quantum-X Photonics, with much more shoreline and area for the SerDes.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_053.png)

Source: SemiAnalysis

The Spectrum-X 6810 Switch Box uses one unit of the above switch package to deliver 102.4T of aggregate bandwidth. The larger Spectrum-X 6800 Switch Box SKU is a high-density chassis with an aggregate bandwidth of 409.6T achieved by utilizing four of the above Spectrum-X switch packages which are also connected to the external physical ports in a multi-plane configuration.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_054.png)

Source: Nvidia

Much like the four ASIC 115.2T Quantum X800-Q3450, the Spectrum-X 6800 uses an internal breakout to physically connect each port to all four ASICs.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_055.png)

Source: SemiAnalysis
