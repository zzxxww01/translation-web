![](https://substackcdn.com/image/fetch/$s_!kR_h!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F903517c9-6ff3-4ac5-9d4a-c0130cb9cbea_2880x1620.jpeg)

*TSMC Passive vs. Active LSI Comparison. Source: TSMC, ISSCC 2026*

TSMC’s advanced packaging division presented their Active Local Silicon Interconnect (aLSI) solution. As opposed to standard CoWoS-L or EMIB, aLSI improves signal integrity and reduces the complexity of PHYs and SerDes on the top dies.

![](https://substackcdn.com/image/fetch/$s_!Gjwp!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa8f473a9-3f0e-4b7a-b717-2bc9999adae6_2880x1620.jpeg)

*TSMC Active LSI Die-to-Die Link Overview. Source: TSMC, ISSCC 2026*

The device that TSMC showed used a 32 Gb/s UCIe-like transceiver. Due to aLSI improving signal integrity, the area of the transceivers could be decreased, and the bump pitch could also be reduced from 45 µm to 38.8 µm. The combination of a tighter pitch and a switch to a Manhattan grid allowed them to reduce the PHY depth from 1043 µm to 850 µm, saving space that designers can reallocate to compute, memory, or IO, or use to shrink the die. The transceiver is only UCIe-like and not true UCIe, as UCIe mandates a hexagonal bump map rather than the Manhattan grid used here.

As designers eke out every bit of die space for next-generation AI accelerators, the switch to aLSI is inevitable.

The ‘active’ part of aLSI comes from replacing the passive long-reach metal channel in the bridge die with active transistors forming an Edge-Triggered Transceiver (ETT) circuit to maintain signal integrity over longer reaches. This also reduces the signal driving requirements of the top die’s Transmit/Receive ports. ETT circuits within the aLSI only add an additional 0.07pJ/b to the energy cost, minimizing thermal concerns from adding active circuits in stacked dies. By moving the signal conditioning circuits to the bridge die, PHY area on the top die TX/RX can be reduced by using smaller pre-drivers and clock buffers and remove the need for signal amplification on the receive end.

The ETT integrates a driver, an AC-coupling capacitor (Cac), an amplifier with both negative and positive feedback, and an output stage. Running the signal through the Cac introduces peaks in the signal transition edges, which is then picked up by the dual-loop amplifier, hence the edge-triggered nomenclature. The amplifier leverages both positive and negative feedback loops to stabilize the voltage level. In this design, Cac is set to be 180 fF for a 1.7 mm channel length, with 2kΩ resistance on die A and 3kΩ on die B respectively.

![](https://substackcdn.com/image/fetch/$s_!wpmP!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc151958f-7fdb-4903-b06a-38a0eace27d5_2667x1500.jpeg)

*TSMC CoWoS-L Integrated Power Delivery with eDTC. Source: TSMC*

These aLSI bridges can also integrate embedded deep trench capacitors (eDTC) along the front-end to improve power delivery to the PHY and D2D controllers. Instead of compromising the power grid by having a bridge die in the way, aLSI with eDTC improves both the power and signal routing along the D2D interfaces.

![](https://substackcdn.com/image/fetch/$s_!Yp1W!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7d837ed3-5395-4e1a-b579-c95f1d9497cc_2880x1620.jpeg)

*TSMC Active LSI Routability and Cross-Section. Source: TSMC, ISSCC 2026*

Only 388 µm of shoreline is required for 64 TX and 64 RX data lanes, coming out to a total area of 0.330 mm². Only the top 2 metal layers are required for routing the signals. The remaining metal layers can be used for the front-end circuitry.

![](https://substackcdn.com/image/fetch/$s_!7zt3!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa2747466-8e4c-4447-ad94-6c2e8b71ea4a_2880x1620.jpeg)

*TSMC Active LSI Shmoo Plots at KGD and KGP Stages. Source: TSMC, ISSCC 2026*

TSMC explained how the Active LSI can be tested at multiple stages. The first is Known Good Die (KGD) with just the LSI for die validation. Next is Known Good Stack (KGS) with the SoCs connected by the LSI for stack functionality. Lastly is Known Good Package (KGP) with the full assembly to comprehensively verify functionality, performance and reliability.

They showed shmoo plots at the KGD and KGP stages, both showing the interconnect hitting 32 Gb/s at 0.75V and 38.4 Gb/s at 0.95V.

![](https://substackcdn.com/image/fetch/$s_!jY_b!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff44de7d8-9b9f-4086-a305-6c16677e9895_2880x1620.jpeg)

*TSMC Active LSI Die Shot and Power Breakdown. Source: TSMC, ISSCC 2026*

The package reveals two SoC dies and two IO dies. Interestingly, the test vehicle appears to match AMD’s MI450 GPU’s design, with 2 base dies connected to each other, 12 HBM4 stacks and 2 IO dies with Active LSI. Instead of each individual HBM4 stack having its own Active LSI, two HBM4 stacks share one.

As for the power, the total is only 0.36 pJ/b at 0.75V, with only 0.07 pJ/b being used by the ETT in the Active LSI. Below is a comparison with other D2D solutions.

![](https://substackcdn.com/image/fetch/$s_!GHcE!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd194a9ff-d0ee-4e74-98a9-1f426f98205c_2880x1620.jpeg)

*TSMC Active LSI vs. Other Die-to-Die Interconnects. Source: TSMC, ISSCC 2026*
