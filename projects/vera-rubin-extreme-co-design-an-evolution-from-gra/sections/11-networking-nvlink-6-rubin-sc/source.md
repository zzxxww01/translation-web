NVIDIA’s gen-on-gen innovations are evolutionary and not revolutionary. With GPU scale-up and scale-out bandwidth doubling approximately every 18 months, the copper infrastructure in NVIDIA racks are being innovated to accommodate higher bandwidth workloads. Scale-up network infrastructure will eventually involve optics to build larger world sizes, but that is the topic of a separate article.

The below table shows the evolution of scale-up and scale-out networking speeds. NVLink 6 used in Vera Rubin doubles NVLink bandwidth by implementing bi-directional signaling over the same number of copper cables - effectively delivering 4 Lanes of 200G per NVLink. Much more on this in the following sections.

![](https://substackcdn.com/image/fetch/$s_!YQB9!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4e17ee04-dce9-4fde-b4fc-6b3f5dff2849_2233x1207.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

Let’s step through key features of Rubin’s networking and the architectures that are likely to be built around Rubin scale-up and scale-out networks.

### Bi-directional SerDes for Scale-Up

The doubling of bandwidth per logical GPU from NVLink 5 in GB300 NVL72 to NVLink 6 in Vera Rubin NVL72 are made possible by using a simultaneous bi-directional SerDes for the copper backplane instead of increasing the modulation or baud rate. Whereas NVLink 5 delivers 224G per electrical lane, NVLink 6.0 delivers 448G per electrical lane. Each electrical lane is one differential pair (DP) consisting of two conductors that carry equal magnitude, and opposite polarity signals.

![](https://substackcdn.com/image/fetch/$s_!I5lb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa92bb668-9e15-45d7-91a5-ed8bba8f3e2a_1946x1300.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

This gives rise to the engineering problem of ensuring that a clean signal can be received at either end of the wire because two signals sent in opposite directions over the same copper wire will superpose to form a composite signal that is different from the intended transmitting signal.

In optics, bidirectional interconnect can be achieved by integrating an optical circulator to a transceiver as discussed in our [TPUv7 article](https://newsletter.semianalysis.com/p/tpuv7-google-takes-a-swing-at-the) published late last year. The circulator works by routing the [inbound and outbound signal onto separate paths](https://newsletter.semianalysis.com/p/google-apollo-the-3-billion-game), ensuring no overlaps between both at the photodiode receiver. Bidirectional interconnect is, however, much trickier in the copper domain. A circulator cannot be used as copper cables are linear transmission lines, which means that the inbound and outbound signals will be summed at the receiver through superposition. The receiver at each end of the copper wire therefore needs a mechanism to separate the local TX from the local RX.

The solution to this problem is the use of a hybrid at each end of the wire. Without a hybrid, there will be self-interference at the local RX because both the local TX and local RX are being transmitted along the same wire:

\(B0 + A0 = BA0 \)

An inverted copy of the local TX must therefore be generated at the local RX for proper echo cancellation:

\(B0 + A0 = BA0 + (-A0) = B0\)

The diagram below illustrates this dynamic:

![](https://substackcdn.com/image/fetch/$s_!KYxc!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbefba865-35dc-46a0-b593-48fa65baa8ae_4380x2667.png)

Source: [IEE Explore](https://ieeexplore.ieee.org/stamp/stamp.jsp?tp=&arnumber=10011563)

While bidirectional signaling is being used for short-reach (less than 5mm) die-to-die interconnect, what stands out is that NVIDIA has extended this technology to longer reach transmission over copper backplane with a reach of at least 1m.

The challenge with bidirectional signaling is that echo cancellation must be precisely calibrated or slight delays in the generation of the local TX copy can cause link failure. However, if NVIDIA were to continue using the 200G SerDes, doubling the bandwidth would mean doubling the number of copper cables at the backplane, which is a tall order for several reasons.

Cramming in approximately five thousand copper cables on the backplane at the Blackwell generation has introduced non-trivial reliability failure modes at scale. To double scale-up bandwidth while staying on regular 200G SerDes would require the backplane to double to ten thousand copper cables: only further increasing the manufacturing complexity and likelihood of failure of the system.

![](https://substackcdn.com/image/fetch/$s_!RWpE!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff79a0f25-17d9-4603-93ae-44a793db3705_4380x2490.png)

*[Blackwell Copper Backplane](https://developer.nvidia.com/blog/nvidia-gb200-nvl72-delivers-trillion-parameter-llm-training-and-real-time-inference/), Source: Nvidia*

NVIDIA could also opt to deploy wider racks instead as is the case of [AMD’s Helios rack](https://newsletter.semianalysis.com/p/amd-advancing-ai-mi350x-and-mi400-ualoe72-mi500-ual256), but this could affect the signal integrity on the PCB as electrical signals will have to traverse a longer path.

### Scale-Up Network – NVLink 6

The bidirectional SerDes technology employed on the copper backplane is used for NVIDIA’s scale-up network. For Vera Rubin NVL72, the scale-up network continues to be rail-optimized with all-to-all connectivity between each GPU and switch ASIC in the scale-up domain.

Last year, we discussed NVIDIA’s GB200 scale-up architecture, which consists of 18 NVLink 5 Switch chips in a single rack for the NVL72 system.

* [GB200 Hardware Architecture - Component Supply Chain & BOM](https://newsletter.semianalysis.com/p/gb200-hardware-architecture-and-component) - Dylan Patel, Wega Chu, and 4 others · July 17, 2024

Although the NVLink 6 Switch used in the VR NVL72 system delivers the same per switch 28.8T aggregate bandwidth as NVLink 5 Switch, the SerDes speed on the NVLink 6 Switch is double the SerDes speed of NVLink 5 Switch but with the same number of DPs. As such, in order to deliver double the aggregate scale-up bandwidth required for NVLink 6, Vera Rubin NVL72 racks will contain double the number of NVLink Switches as compared to GB200 racks. This translates to four NVLink Switch chips per tray on 9 switch trays, or 36 NVLink Switch chips in each rack.

Each VR NVL72 Switch tray contains four NVLink 6 Switch ASICs and one system management module. The design of the Rubin NVLink 6 Switch tray is also simpler and relatively seamless compared to the first Oberon NVLink 5 Switch released for GB200 because Rubin NVLink 6 Switch trays will not use flyover cables. As such, all NVLink signals will run over the PCB.

The NVLink 6 Switch board is liquid cooled and will be covered with a cold plate, which is a single module. Connected to the NVSwitch tray is the system management module (SMM) that comes with a CPU and acts as a host to the switch tray. The switch tray to SMM connection uses flyover cables, but this is the only flyover cable connection required in the entire Vera Rubin NVL72 system. Given that the PCIe connection is lower speed and the NVLink Switch tray contains relatively few modules, assembly of the switch tray is unlikely to be challenging.

![](https://substackcdn.com/image/fetch/$s_!AUbf!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9a0db27b-2364-4f3e-8e5b-14a31327c898_919x1501.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

The diagram below shows how the NVLink 6 signal traverses through the tray. Each of the green lines represents nine 400G logical ports of NVLink 6, or 18 TX/RX lanes of 200G. Because there is only 1 DP per lane using bidirectional SerDes, there are a total of 18 DPs between any connector and any switch for a total of 72 DPs per connector, which is the same as prior generation of NVLink 5 Switch Tray.

![](https://substackcdn.com/image/fetch/$s_!aeWB!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fccd14529-356f-493a-ad9a-4fe57d339d9d_883x1485.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

As previously explained, high speed signals require better PCB materials, especially for NVLink 6 which has much lower tolerance for insertion loss given the use of bidirectional signaling. The number of lanes between the PaladinHD2 connectors and the NVLink Switch also creates complexity for PCB design. Hence, the NVLink 6 Switch board PCB is upgraded to 32 layers with M8+ graded CCL - minimally LDK2 glass fiber cloth or potentially Quartz fiber cloth.

We have more details on the switch tray and various components in the [VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/).

Zooming out, backplane copper cables are used to connect NVLink Switch trays to the GPU trays for the VR NVL72 system. Although the bandwidth doubles, with bi-directional SerDes, the number of cables required does not change from the GB300 backplane generation to the Vera Rubin NVL72 backplane generation. The number of connectors and the number of DPs per connector also does not change from Grace Blackwell NVL72 to VR NVL72.

![](https://substackcdn.com/image/fetch/$s_!kVSj!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe18bd90a-d96f-4237-bb8a-bb5b0f0e0582_3193x1126.png)

*Grace Blackwell NVL72 Scale-up Topology. Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)*

![](https://substackcdn.com/image/fetch/$s_!R5Gn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa4533a61-ae9d-45a4-a80b-c5d76f70bd6d_3150x1090.png)

*Vera Rubin NVL72 Scale-up Topology. Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)*

While the VR NVL72 system features GPUs and scale-up switches that are connected by copper cables, the VR HGX system features servers consisting of eight Rubin GPUs and four NVLink Switch chips. The second meaningful difference between the NVL72 and HGX deployments is that the former has a scale-out bandwidth of 1.6T per GPU while the latter only has a scale-out bandwidth of 800G per GPU. How is it that all Rubin 200 deployments use CX-9 NICs even though some deployments have half the per GPU scale-out bandwidth?

The HGX Rubin NVL8 server consists of eight 800G CX-9 NIC packages – one NIC per GPU – which means that the scale-out bandwidth does not increase from its predecessor, the HGX B300 server. The Vera Rubin NVL72 deployment on the other hand doubles the per GPU scale-out bandwidth to 1.6T, but not by doubling the bandwidth per NIC. Rather, the “1.6T NIC” attached to each Rubin chip is comprised of two 800G CX-9 packages that is connected to the Vera CPU by PCIe Gen 6.0 lanes.

Each compute tray on the VR NVL72 has eight 800G CX-9 NICs, but there are two possibilities for the number of OSFP cages - either one 1.6T OSFP cage per GPU for a total of 4 per compute tray, or two 800G OSFP cages per GPU for a total of 8 cages per compute tray. We think that the latter would be the more popular deployment assumption, and will be the base case for our discussion of scale-out networking architectures in later sections of the article.

![](https://substackcdn.com/image/fetch/$s_!ELO8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdb518988-d9be-433e-a5cd-f8d834c7daa3_2631x826.png)

Source: Nvidia VR NVL72 Component BoM and Power Budget Model

### Connecting GPUs in the Scale-Out InfiniBand Network

Broadly, there are three flavors of scale-out deployments for Vera Rubin NVL72. We have InfiniBand-based clusters which employ the NVIDIA Quantum series of switches, NVIDIA Ethernet-based clusters employing Spectrum series switches and lastly, non-Nvidia Ethernet such as Tomahawk-based, Cisco Silicon One or Teralynx-based Ethernet switches. Some Ethernet-based clusters deployed by hyperscalers will use AECs for NIC-to-TOR and switch-to-switch connections, while other Ethernet-based clusters using only optical interconnects will usually adopt a multi-plane and multi-rail networking architecture. What is particularly noteworthy about Vera Rubin NVL72 deployments, however, is that it is the first Nvidia GPU generation where we will be seeing some Co-Packaged-Optics (CPO) deployments in the scale-out backend network.

While there are both InfiniBand and Spectrum-X based clusters, the InfiniBand-based Quantum X800-34XX series of switches is more popular with Neoclouds than with hyperscalers. For InfiniBand, there are two deployment types – the first is the Quantum X800-Q3400 with pluggable optics and the second is the Quantum X800-Q3450 CPO-based switch that use co-packaged Optical Engines (OE) instead of pluggable transceivers.

The Quantum X800-Q3400 is logically a multi-plane switch combining 4 Quantum-3 ASICs into a single switch box, though we will dive into this equivalence later in the article. This multi-plane “topology” is abstracted away and as far as network engineers are concerned, the Q3400 is a single switch with 144 ports – or a “little boy” switch.

![](https://substackcdn.com/image/fetch/$s_!iXPd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc3908b30-94ca-4a19-a964-75806231894a_2695x1059.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

The InfiniBand architecture for the HGX Rubin NVL8 server is therefore effectively a single-plane, 8-rail network consisting of one 800G uplink from each HGX Rubin NVL8 GPU to a leaf switch.

![](https://substackcdn.com/image/fetch/$s_!xxpO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Feacb373c-b4b3-4125-b335-d90e8d4caf2e_2538x1267.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

For the Vera Rubin NVL72 deployment however, there are two 800G OSFP cages per GPU for a total of 1.6T per GPU bandwidth. Having two 800G logical ports per GPU is advantageous because it allows multi-plane network deployments without complex fiber management – by splitting one logical GPU two ways to two different leaf switches. As such, larger network clusters can be built with two 800G logical ports than if only one 1.6T logical port were used. In fact, as we have explained in multiple prior articles such as the networking sections of [NVIDIA’s Optical Boogeyman](https://newsletter.semianalysis.com/p/nvidias-optical-boogeyman-nvl72-infiniband#the-clos-non-blocking-fat-tree-network) and [Microsoft’s AI Strategy Deconstructed](https://newsletter.semianalysis.com/p/microsofts-ai-strategy-deconstructed), this relationship is dictated by a simple formula for the maximum number of hosts that can be supported using a switch of k ports on an L-layer:

\(2\left(\frac{k}{2}\right)^L \)

Illustratively, consider two hypothetical VR NVL deployments with 1.6T and 800G logical ports respectively. A 1-plane, 3-layer network with one 1.6T logical ports achieves only a maximum cluster size of 93,312 GPUs, or:

\( 2\left(\frac{\frac{115{,}200}{1{,}600}}{2}\right)^3 = 2\left(\frac{72}{2}\right)^3 = 93,312\)

By one 1.6T logical port, we mean that the two 800G OSFP cages connected to each GPU are connected to a single, dual-port 1.6T transceiver at the leaf layer because the two 800G ports are effectively performing the function of one 1.6T port – and hence the term “logical”.

![](https://substackcdn.com/image/fetch/$s_!9P5d!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fec57efde-b531-4f61-9d11-8703e99c5e20_3145x1357.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

To scale beyond the maximum cluster size of 93,312 GPUs, a 2-plane network can be deployed in which each of the two 800G OSFP cages supporting a GPU are linked to separate leaf switches on different network plans. This allows you to build a 186,624-GPU cluster size as diagrammed below and even scale up to 746,496-GPU cluster sizes.

\( 2\left(\frac{\frac{115{,}200}{800}}{2}\right)^3 = 2\left(\frac{144}{2}\right)^3 = 746,496\)

![](https://substackcdn.com/image/fetch/$s_!-SrC!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F513cc763-5600-427d-a834-c1649efcc764_2626x1711.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

We think the second cluster with two switch planes will likely be the more prevalent reference architecture for Vera Rubin NVL72 InfiniBand deployments.

Aside from the X800-Q3400 air-cooled switch, NVIDIA will also offer a CPO version, which is the X800-Q3450 containing the same 144 ports of 800G. As pointed out earlier, what is unique about both switches is that each switch box consists of four 28.8T Quantum-3 Switch ASICs for a total of 115.2T per box switching capacity. When used in conjunction with the VR NVL72 servers, the signal from the NIC at the leaf layer is split four ways – 200G each way – to each switch ASIC within the box. Such a configuration bears logical equivalence to a 4-plane network architecture.

![](https://substackcdn.com/image/fetch/$s_!4bBE!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fab4648e8-1c21-41ba-92dc-457ddb09e3dc_2133x1368.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

### Ethernet-Based Cluster Deployments

Although InfiniBand has been the more popular network architecture for previous NVIDIA chips such as the H100 and GB200, NVIDIA is aggressively pushing out Spectrum Ethernet-based networks and have introduced various switch SKUs:

1. SN6600, a 102.4T liquid-cooled switch; 2. SN6800, a 4 ASIC, 2048-radix 409.6T multi-plane CPO switch, offering 512 ports of 800G; 3. SN6810, a high-radix 102.4T CPO switch with three further deployment options: 512 ports of 200G, 256 ports of 400G and 128 ports of 800G.

For the SN6600 switch, the scale-out reference architecture is an 8-plane network where each GPU fans out eight ways to eight different planes. This is similar to the reference architecture for the 8-plane scale-out network using SN6810 switches.

![](https://substackcdn.com/image/fetch/$s_!Ooam!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc31a2ad9-ef3a-4da2-83be-b8b39200d7e0_2605x1330.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

We think that the SN6800 switch with 512 ports of 800G will be quite attractive to Neoclouds because it simplifies deployments. Similar to the X800-Q3400 scale-out network, an SN6800 scale-out network could consist of two switch planes though the SN6800 enables a much larger feasible scale-out world size.

The diagram below shows what such a network could look like – though it only shows one of two planes as readers can deduce by the fact that we are only depicting 1x800G from each GPU. Note also that each SN6800 switch box consists of four ASICs, each with its own switch plane, which we will elaborate on later in the article.

![](https://substackcdn.com/image/fetch/$s_!TYad!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5e626b67-f940-4e47-a5d8-d3790f86d155_2611x1315.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

For a 512-port switch, we can connect up to 131,072 GPUs with two layers of switches or a ludicrous 33,554,432 GPUs on 3 layers.

\(2\left(\frac{512}{2}\right)^2 = 131,072\)

\(2\left(\frac{512}{2}\right)^3 = 33,554,432\)

What advantages do CPO switches such as the SN6800 deliver for Neoclouds like Coreweave and Lambda when it comes to large-scale cluster deployments?

As discussed in our recent [deep dive article on co-packaged optics,](https://newsletter.semianalysis.com/p/co-packaged-optics-cpo-book-scaling) the first reason is that a significant amount of power can be saved by eliminating most of the transceiver content. If we compare the power consumption of one 800G DR4 optical transceiver (16-17W) to the power required by optical engines (OEs) and external light source (ELS) modules to delivery an equivalent 800G of bandwidth in the scale-out network, we see an average ~70% reduction in power used for optical transceivers. Taking a step back, this would translate to 10% in savings for the total networking equipment power consumption in a 3-Layer HGX Rubin NVL8 cluster. This reduction in networking equipment power consumption is however relatively insignificant and amounts to only ~1% of total cluster power consumption because the server’s power budget dominates the equation.

![](https://substackcdn.com/image/fetch/$s_!eRja!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdb19c505-aef9-494d-ab39-8e3caa913cf7_2902x936.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

The second benefit is a reduction in cost stemming from eliminating almost all transceivers. There is even more room for price reduction if we are looking at NVIDIA LinkX transceivers, which tend to be priced at significant premium to their generic equivalent. If we compare total networking costs for a 3-Layer network with and without CPO-based switches in the scale-out domain, we see an average of ~75% reduction in transceiver costs. However, as with the power savings above, such costs savings tend not to move the needle dramatically considering the full cluster costs.

![](https://substackcdn.com/image/fetch/$s_!RL4i!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F23326c48-f03b-409d-ad25-a64c79a62581_2902x953.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

We outline these calculations in more detail and discuss this topic at greater length in our [CPO Book Report](https://newsletter.semianalysis.com/p/co-packaged-optics-cpo-book-scaling).

Increased overall network reliability is another compelling point. Transceivers can be unreliable, with a large cluster certain to have ongoing link flaps. [Meta’s study presented at ECOC](https://newsletter.semianalysis.com/i/178153689/when-will-cpo-be-ready-for-primetime) showed strong reliability results over 15M 400G port-device hours, which is about equivalent 15 CPO switches tested for 11 months in a lab. It is an encouraging start – but we think this point could get stronger with more in field test deployments.

The last factor in favor of adoption of CPO that we would like to mention is the fact that some of Nvidia’s CPO switch SKUs contain the integrated fiber shuffle and can simplify the installation and maintenance of multi-plane network architectures. Recall that the SN6800 contains four Switch ASICs in a multi-plane configuration connected to ports via an integrated fiber shuffle, delivering 409.6T aggregate bandwidth, while the SN6810 uses one Switch ASIC, but without any integrated fiber shuffle, to deliver 102.4T aggregate bandwidth.

But first, we will explain why we think multi-plane networking architectures are here to stay as an important preface.

Large-scale cluster deployments where cluster sizes exceed 100k GPUs typically utilize multi-plane network architectures because single-plane network architectures do not have enough logical ports at current switch generations to support larger networks without resorting to a high number of switch layers of 3 or more layers.

Recall from above that a Vera Rubin NVL72 cluster built with Q3400-X800 switches at 1.6T logical ports per GPU cannot scale beyond the maximum cluster size of 93,312 GPUs. Even if future switch generations continue to double the maximum possible switching capacity per switch box, the per GPU bandwidth is also expected to double, which means that the effective logical port count in a cluster network is unlikely to change.

What this means is that deployment of large-scale GPU clusters will continue to require multi-plane network architectures. Do note however that multi-plane networking architectures are not limited by size and we have also seen NVIDIA reference architecture deployments with multi-plane clusters that are significantly below 100k GPUs each.

In multi-plane network architectures using the SN6600 switch instead of the CPO switch, each GPU fans out to multiple switch boxes using fiber shuffles. This requires customers to deploy shuffle boxes, patch panels and unwieldy octopus cables outside the switch box that introduce complexity in installation and maintenance.

Some of Nvidia’s CPO SKUs – such as the SN6800 and Q3450 –contain such a fiber shuffle within the switch box, with each optical engine fanning out to different logical ports. They therefore deliver higher aggregate bandwidth – 409.6T and 115.2T respectively than is possible with a switch box based on a single Switch ASIC.

![](https://substackcdn.com/image/fetch/$s_!8mCA!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F41bf7a29-4917-41d8-957a-86cc9773b39c_2897x3821.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

For the SN6800 CPO switch, even though the bandwidth engine responsible for converting electrical to optical signals scales from 1.6T to 3.2T or 2x compared to the SN6600 switch, each 3.2T OE within the SN6800 switch box is split into four 800G logical ports that fan out within the box itself and exit the front panel through fiber connectors. This allows a single 1.6T GPU to fan out to two independent switch planes. In fact, the SN6800 switch box consists of four ASICs, which is similar to the X800-Q3400 switch box.

![](https://substackcdn.com/image/fetch/$s_!foD7!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F21284057-cc2b-423a-836f-cce6283ef615_2916x1102.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

As the per GPU bandwidth continues to scale to 3.2T, it is not hard to imagine a 4-plane network using SN6800 switches, where each 3.2T GPU is split four ways to connect to four different switch boxes at 800G per link.

In fact, if you have not already noticed – there are strong parallels between the X800-Q3400 switch (non-CPO) explained earlier in the article and a CPO switch in that both facilitate high-radix, multi-plane networking architectures while encasing within the box complex cabling that saves customers on the hassle of cable management.

Outside of the NVIDIA ecosystem, the main switch ASIC players are Broadcom, which will be manufacturing the Tomahawk 6 and Tomahawk 6 CPO ASICs, as well as Cisco, which recently announced the G300 102.4T ASIC. There are two flavors of hyperscaler backend network deployments:

* 8-plane “flat” network utilizing the full 512 switch radix;

![](https://substackcdn.com/image/fetch/$s_!deTC!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2249c887-6af9-4933-9297-6b698aca46e3_2622x1323.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

* Single plane network with 1.6T OSFP cages at the NIC.

![](https://substackcdn.com/image/fetch/$s_!Z-9f!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9cc07e85-ea9f-4089-a0a2-4d15b7c5ac8d_2782x1258.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

For Meta, we think the VR NVL72 deployments will comprise only of non-scheduled fabric (NSF) clusters built using Tomahawk 6-based Minipack-4 OCP Rack 102.4T switches in each datacenter. While Meta will be using optics to connect all the switches within its cluster, it will use 1.6T AECs for NIC-to-TOR connections once 1.6T AECs become broadly available in the market. We expect the 1.6T AEC ramp to happen in the second half of calendar year 2026.

![](https://substackcdn.com/image/fetch/$s_!dp6K!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc2c75af2-9d1e-41c6-86de-aede72445f14_1981x1623.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/https://semianalysis.com/ai-networking-model/)

The catch is that 102.4T Minipack-4 switches may not be shipped in time for Vera Rubin NVL72 rack deployments, and if this were to be the case, some NSF clusters will be shipped using 51.2T Minipack-3 switches instead. This means that gearboxes within the AECs will have to be used to convert 200G per lane SerDes speed at the NIC to 100G per lane SerDes speed at the switch.

Meta will not be the only hyperscaler using 1.6T AECs for its VR200 deployments, however. We think xAI will use 1.6T AECs for both NIC-to-TOR and switch-to-switch connectivity at the leaf, spine and core layers. It will be a single-plane network replacing most 1.6T transceivers at the switch boxes – and this can give Credo plenty of pricing power.
