As mentioned above the VR NVL72 compute tray is designed around the cableless concept. As we discussed in our **[PCB Supercycle Core Research note in August last year](https://semianalysis.com/institutional/ai-server-pcb-super-cycle-copper-foil-content-upgrade/)** as well as our recent **[Core Research note on Amphenol’s AI Content](https://semianalysis.com/institutional/amphenol-content-growth-vr-nvl144-backplane-board-to-board-connectors-dac-acc-aec-tam-kyber-midplane-backplane/)**, there are two reasons for this design. First, flyover cables present multiple different points of failure as they can easily be damaged during assembly. Second, the high-density design of VR NVL72 leaves limited space for cables to be routed.

### Replacing Internal Cables with Board-to-Board Connectors

For the GB200/300, the most valuable cable that is exclusively supplied by Amphenol is the DensiLink OverPass cable set within the compute tray. This cable provides the ethernet connection between the CX-7/8 NIC and the OSFP cages. However, this cable is extremely vulnerable to scratches and damage of the cable termination during assembly, thereby creating many points of failure. There are also several other lower-end PCIe cables in use (MCIO and SlimSAS) that also suffer from the same points of failure. These cables involve many other suppliers as well – complicating procurement and vendor management. Given the delicate nature of the cable, workers must be extremely careful while placing the cables in a very dense and compact chassis, which prolongs assembly time.

Although a cableless design might initially appear unfavorable for Amphenol, it is in fact a positive. Signals between the Strata module and the daughter modules still need a physical interconnect. In this architecture, those signals exit the Strata board through Amphenol’s PaladinHD2 board-to-board connectors. The signal is then routed through a PCB midplane sitting in the middle of the chassis. On the other side of the PCB midplane, the daughter modules connect to the PCB midplane via another set of Paladin HD2 B2B connectors. In our [VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/) we have a detailed breakdown of Amphenol’s compute tray content in Vera Rubin NVL72. This is also discussed in more detail in our article on **[Amphenol’s AI Content.](https://semianalysis.com/institutional/amphenol-content-growth-vr-nvl144-backplane-board-to-board-connectors-dac-acc-aec-tam-kyber-midplane-backplane/)**

![](https://substackcdn.com/image/fetch/$s_!Im-q!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F675f09bf-ba67-4a1c-9586-eee07284d81d_2256x418.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

### Relocating ConnectX-9

To accommodate this cableless design, the CX-9 NICs, that would have been on the Strata modules, are relocated to the Orchid module (from the back half to the front half of the chassis) as illustrated in the diagram below.

![](https://substackcdn.com/image/fetch/$s_!NMLS!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9a44425c-aa7a-46e2-bc0a-9c5f1cdfce92_1354x2353.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

![](https://substackcdn.com/image/fetch/$s_!3ZiJ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F164f7aed-a3bb-4037-be5a-039fcebf216f_1422x2419.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

For the GB200/GB300, the PCIe signal distance between the GPU/CPU and the CX-7/8 is shorter than the Ethernet/InfiniBand signal distance between the CX-7/8 and the OSFP cages. Previously – having to transmit a 200G Ethernet/InfiniBand signal from the NIC in the back half of the compute tray to the OSFP cage in the front of the compute tray necessitated the use of flyover cables as the signal loss over PCB at 200Gbit/s (uni-directional) per lane is too high.

But now that the NIC is closer to the OSFP cage, the lower speed PCIe Gen6 signal (64Gbit/s per lane uni-directional) travels the longer distance. By making the PCIe Gen6 signal longer, the signal can travel over PCB given that PCIe Gen6 has better signal integrity than the higher speed 200G Ethernet/InfiniBand signal.

### PCB vs Flyover Cables

Nevertheless, it is still challenging to drive a PCIe Gen6 signal over around 500mm of PCB distance from the Strata Module to the front of the Orchid Module. In addition to having high quality SerDes, proper signal integrity is still achievable by upgrading PCB materials.

First, we must understand why high-speed signals perform worse on PCB versus flyover cables. As SerDes rates increase, high-speed channels become increasingly constrained by insertion loss introduced by PCB traces, vias, dielectric materials and conductor roughness. Insertion loss is defined as the signal power that is lost as a signal is traveling through an interconnect channel.

![](https://substackcdn.com/image/fetch/$s_!ty_8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc4ac828d-47ff-4fa3-953a-cc21a29d201a_1020x648.png)

Source: Doosan, SemiAnalysis

The three main mechanisms contributing to insertion loss in a PCB channel are conductor loss from skin effect and copper surface roughness, dielectric loss from laminate absorption, and geometry loss from discontinuities such as vias and layer changes.

![](https://substackcdn.com/image/fetch/$s_!nWxq!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa9047e9c-d055-47c2-b963-d09f338fb564_1199x675.png)

Source: DesignCon, Circuit Foil Luxembourg

Conductor loss is driven by copper surface roughness. As signals travel down the copper traces in the PCB, energy is lost due to the resistance in copper. At higher frequencies, the signal traveling through the copper crowds toward the surface of the trace, which is known as the skin effect. On top of the natural resistance of copper, if the surface is rough, the current will not travel along a uniform path incurring more resistance and loss.

Dielectric loss is driven by the energy absorption nature of the dielectric materials. Dielectric materials, resins and glass fiber cloth, provide insulation and mechanical reinforcement function for the PCB traces. At high frequency, high-speed signal doesn’t simply travel through the copper traces, the signal traves as an electromagnetic wave with electric field extending into the dielectric materials. As the signal propagates, the dielectric absorbs a portion of the energy and dissipates as heat, contributing to insertion loss. Dielectric loss scales with frequency, hence dielectric loss is a dominant limiter of signal performance of long reach PCB traces.

Geometry loss describes the insertion loss incurred from abrupt structures of the PCB traces. Real PCB channels include many abrupt structures, such as vias and layer swaps. These are like bumps in a highway, and signals could reflect backward and be interrupted increasing insertion loss.

Another factor that affects signal performance is cross-talk. Given the increase in the number of I/Os per GPU, lane density in the PCB also increases. Cross-talk describes the scenario where the copper traces are too close to each other and the signal from one lane affects the signal in a neighboring lane. Some copper traces are designed for power as well. When the power lanes are too close to the signal lanes, noise from the power lanes can also modulate the signal as well.

In conclusion, insertion loss scales with signal frequency, and high-speed signal suffers more insertion loss from PCB than from fly over cables. Hence, as traditional CPU servers upgrade to higher signaling frequencies such as upgrading to newer PCIe generations, the CPU server design increases the adoption of fly over cables to compensate for insertion loss from the PCB. The alternative solution would be upgrading PCB materials, however, fly over cables are more cost effective and remain feasible for traditional server applications.

For VR NVL72, the design has turned toward cableless given the higher density and manufacturing complexity of AI server. The cost saved on improving higher manufacturing yields and assembly time reduction more than offsets the higher cost of the upgraded PCB materials. It is critical that all the factors that contribute towards insertion loss in the PCB are mitigated, hence PCB material upgrades are necessary for VR NVL72. [We break down the cost by component here](https://semianalysis.com/vr-nvl72-model/).

### PCB Materials Upgrade and Area Growth

PCB content value in VR NVL72 will grow significantly compared to that of GB200/GB300. The two main drivers of this content growth are significant material upgrades and the notable increase of high-end PCB area and layers. Our [VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/) has provides the $ content breakdown of high end CCL and PCB content for VR NVL72 vs GB200/GB300.

![](https://substackcdn.com/image/fetch/$s_!ypvn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F48aa0d51-0ac3-472d-8674-aa48f5fbe1c1_2710x663.png)

Source: [VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

On the material side, CCL content upgrades from M7 to M8/M9 drives material upgrades. Copper foil is upgraded to HVLP4 across the board for the main compute and networking boards. A glass fiber cloth upgrade is necessary to reduce dielectric loss, but whether quartz cloth (Q glass) is necessary remains a debate. Below let’s discuss the materials upgrade and the key considerations behind the adoption of each material.

The Table below shows the CCL classification and PCB specification of each main board in Blackwell versus Rubin.

![](https://substackcdn.com/image/fetch/$s_!kixR!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F88c63783-7d94-4c4f-a2ad-b1ca150403f5_2845x1393.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

The classification of CCL materials is determined by its dielectric constant (Dk) and dissipation factor (Df) at a given frequency. Insertion loss is lower at lower Dk and Df value. The common classification is anchored to the Megtron series from Panasonic as they have been setting the industry standard. When people describe the CCL as M7 classification it usually means it matches the same Dk and Df specifications as Megtron 7 of Panasonic.

![](https://substackcdn.com/image/fetch/$s_!NIi4!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6b72a49b-42c7-4197-8098-dee66c98dc54_976x415.jpeg)

Source: Panasonic

Copper foil content in Rubin is upgraded from HVLP2 to HVLP4 grade copper foil for the signal layers. As discussed earlier, due to the skin effect, smoother copper foil equals to lower insertion loss. HVLP is the classification of copper foil standing for Ultra-Low Profile Copper Foil. The higher the HVLP grade equals to lower surface roughness.

For the power layers, the additional layers in Strata compared to Blackwell are mostly power layers to accommodate more power going into the GPU. By adding more dedicated power layers, cross talk is reduced as power layers and signal layers are separated. Power layer copper foils are much thicker to insulate the current travelling through it.

The glass fiber cloth upgrade aims to reduce the dielectric constant of CCL. Beside glass fiber cloth, resin is also a key factor contributing to dielectric constant. To achieve a desirable dielectric constant, the CCL makers have their unique recipes to their formulation of the two dielectric materials in the CCL. Currently, debate around the CCL spec is around the adoption of Quartz cloth (Q glass).

Quartz cloth is the next generation material that replaces the glass fiber cloth materials as the reinforcing layer, pushing dielectric constant even lower. Besides lower dielectric constant, quartz cloth also has the benefits of being stronger, more temperature resistance, and having a lower CTE. On the other hand, the cost is multiples higher than that of the highest-grade glass fiber cloth and is much harder to process at the PCB manufacturing level, leading to worse yield.

Within VR NVL72, Quartz is initially adopted for the Orchid board and the midplane to allow the longest distance PCIe Gen 6 signal traveling through these two boards with as little insertion loss as possible. However, given the cost of the Quartz cloth and the difficulty in Q cloth processing, Nvidia is currently exploring the option of downgrading back to glass fiber cloth. The final decision is pending on the signal performance with the downgraded glass fiber cloth.

![](https://substackcdn.com/image/fetch/$s_!23tC!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F90d73db2-1e48-4675-8fab-46e2d57d2671_2255x1609.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

Beside material upgrade, the other driver of PCB content value is the increase of high end PCB area coverage. In Grace Blackwell, the only boards with high end material are the Bianca board with M7 grade CCL and the NVSwtich board with M8 grade CCL, leaving front half of the compute tray uncovered by high end PCB board. For VR NVL72, the Orchid board and the midplane board increases the high end PCB board area in the compute tray covering the front half of the chassis. With the Strata board bigger than the Bianca board and the extra peripheral boards in the compute tray, we estimate that the area of high end PCB board increases by ~2.3 times from GB300 to VR NVL72. As the tables shows, the Orchid board is the main contributor to the delta of total high-end PCB area between GB300 and VR NVL72 rack.

Our [VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/) has provides the $ content breakdown of high end CCL and PCB content for VR NVL72 vs GB200/GB300.
