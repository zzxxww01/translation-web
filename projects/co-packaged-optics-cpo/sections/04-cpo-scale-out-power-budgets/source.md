Earlier this year, at GTC 2025, Nvidia’s CEO Jensen Huang highlighted the immense power consumption from transceivers alone as a key impetus for CPO. Using some of the per-rack power budgets from the above table, a 200,000 GB300 NVL72 (72 GPU packages and 144 compute chiplets per rack) GPU cluster on a three-layer network would consume 435 MW of Critical IT Power of which 17 MW would be consumed by optical transceivers alone. Clearly there is an immense amount of power that can be saved by eliminating most of the transceiver content.

This can be easily seen by comparing the power used in just one 800G DSP transceiver to the power consumed by optical engines and laser sources (per 800G bandwidth) within a CPO system. While an 800G DR4 optical transceiver consumes about 16-17W, we estimate that the optical engine together with external laser sources used in Nvidia’s Q3450 CPO switch consume about 4-5W per 800G of bandwidth, a 73% reduction in power.

These figures are very close to those presented by Meta in its paper published and presented at ECOC 2025. In this report – Meta showed how an 800G 2xFR4 pluggable transceiver consumes about 15W while the optical engine and laser source within the Broadcom Bailly 51.2T CPO switch consumes about 5.4W per 800G of bandwidth delivered, a 65% power savings.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_004.png)

Source: Meta

Let’s expand this analysis to the cluster level. Turning to a GB300 NVL72 cluster built on a three-Layer network, we see that moving from DSP transceivers to using LPO transceivers in the back-end network can reduce total transceiver power by 36% and total network power by 16%. A full transition to CPO yields even greater savings vs DSP optics – cutting transceiver power by 84% – though part of this power saving is offset by adding optical engines (OEs) and external light sources (ELSs) to the switches, which now consume 23% more power in aggregate. In the below example, optical transceiver power in the CPO scenario remains floored at 1,000W per sever because we assume that front-end networking will still use DSP transceivers.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_005.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

The use of Nvidia’s CPO scale-out switches implicitly means a high radix network is used by default, though this is “abstracted” from the end users because the shuffle happens inside the switch box as opposed to outside the switch box via patch panels or octopus cables when using high radix non-CPO switches. Instead, these Nvidia CPO switches present themselves as having a very high port count – the Quantum 3450 offering 144 ports of 800G, and the Spectrum 6800 offering 512 ports of 800G for example. We use the word “by default” because Nvidia’s non-CPO InfiniBand Quantum Q3400 switch also offers 144 ports of 800G, though its other InfiniBand switches such as the QM9700 only offer 32 ports of 800G - with only the former offering this “high radix in a box” to deliver a high number of effective ports. This high port count could potentially allow customers to flatten a network from a three-Layer to a two-layer network and is also saves customers the trouble of deploying shuffle boxes and patch panels or unwieldy octopus cables and could be a key selling point. In the two-layer case, transceiver power is reduced by 84%, switch power is down by 21% and total networking power can be reduced by 48% vs traditional DSP transceivers.

The Spectrum 6800 switch, with its large number of ports in both available logical configurations - 512 ports of 800G – specifically enables this when compared to the Spectrum 6810, which offers 128 ports of 800G, 256 ports of 400G or 512 ports of 200G. For the 128 ports of 800G option using the Spectrum 6810, a network could connect up to 8,192 GPUs for a two-layer network, while the Spectrum 6800 at 512 ports of 800G can connect 131,072 GPUs.

As a brief aside, the maximum number of hosts that can be supported using a switch of k ports on an L-layer network is given by:

\(2(\frac{k}{2})^L\hspace{2cm}2(\frac{512}{2})^2\)

The magic comes from the fact that the number of ports k is exponentiated by the number of layers. Thus, for a two-layer network, doubling the number of logical ports by assigning half the bandwidth per port (i.e. slicing an 800G port into two 400G ports) using either an internal shuffle (as is the case with the Spectrum 6800), breakout cables or twin-port transceivers means four times the hosts supported!

The power savings discussed in this section so far, 23% for a three-layer CPO network and 48% going down to a two-layer CPO network sounds fantastic, but the wrinkle is that networking is just 9% of total cluster power to begin with for a three-layer network. So, at the end of the day the impact of switching to CPO is diluted considerably at least for scale-out networks. Switching to use CPO for a three-layer network lowers networking power by 23% but only delivers 2% total cluster power savings. Moving to a two-layer network delivers 48% lower networking cost, but only 4% total cluster power savings.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_006.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_007.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/)

It is a similar story when looking at total cluster capital cost.
