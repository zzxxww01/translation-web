DSP Transceivers handle both the transmission and reception of optical signals and contain an “optical engine” (OE) which is responsible for electro-optical conversion. The OE consists of a driver (DRV) and modulator (MOD) to transmit optical signals, and a transimpedance amplifier (TIA) and photodetector (PD) to receive optical signals.

Another important component is the optical DSP chip, which sometimes integrates the Driver and/or TIA into one package. The high frequency electrical signal that is transmitted from the host switching or processing chip needs to travel a relatively long distance over lossy copper traces to reach the transceiver at the front of the server chassis. The DSP is responsible for retiming and reconditioning this signal. It carries out error correction and clock/data recovery to compensate for electrical signal degradation and attenuation as the signal passes from the switch or ASIC silicon through the substrate or other transmission medium. For modulation, in the case of PAM4 Modulation (Pulse Amplitude Modulation with 4 Levels), the DSP maps a binary signal into four distinct amplitude levels in order to increase the number of bits per signal, allowing higher bitrates and more bandwidth.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_020.png)

Source: SemiAnalysis

The DSP chip is one of if not the most power-hungry and expensive components within the transceiver. For an 800G SR8 Transceiver – the DSP accounts for nearly ~50% of the module’s total power consumption, which is why there has been so much focus on getting rid of the DSP.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_021.png)

Source: [Dr. Radha Nagarajan et al.: Recent Advances in Low-Power Digital Signal Processing Technologies for Data Center Applications](https://ieeexplore.ieee.org/document/10526441/)

An 18k GB300 Cluster build with a two-layer InfiniBand network will require 18,432 800G DR4 transceivers and 27,648 1.6T DR8 transceivers. The extra cost and power requirements stemming from the use of DSPs can add considerably to the total cost of ownership. Budgeting 6-7W for the 800G DSP and 12-14W for the 1.6T DSP, this would add up to 480kW of DSP power for just the back-end network alone for this entire cluster, or about 1.8kW per server rack. When sourced from premium brand-name suppliers, transceivers can account for nearly 10% of the cluster’s total cost of ownership. So – accounting for 50% of the power draw and 20-30% of the BoM of a typical transceiver – some regard DSPs as public enemy number one of cost and power efficiency.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_022.png)

Source: SemiAnalysis AI Networking Model

### The Crusade Against DSPs

The high cost and power proportion taken up by DSPs has motivated the industry to find technologies that can disintermediate the DSP. The first wave of attack on the DSP was linear pluggable optics (LPO) – which attempt to remove the DSPs altogether and have the SerDes from the switches directly drive the TX and RX optical elements in the transceiver. However, LPO has not yet taken off as [DSP Diviner Loi Nguyen correctly predicted in our interview with him back in 2023](https://semianalysis.com/2023/03/08/marvells-dsp-dilemma-networkings/).

* [Marvell's DSP Dilemma? Networking’s Tectonic Shift Led By Broadcom, Nvidia, Arista Networks, Microsoft, Meta, Macom, and more](https://newsletter.semianalysis.com/p/marvells-dsp-dilemma-networkings) - Dylan Patel · March 8, 2023

CPO takes the LPO concept to the next step by placing the optical engine on the same package as the compute or switch chip. A key benefit of CPO is that the DSP that was found in the transceiver is no longer required because the distance between the host and the optical engine is so short. CPO also goes further than LPO because it unlocks much greater chip shoreline density by eliminating the need for power and area-hungry LR SerDes in favor of shorter reach SerDes or even clock forwarded wide D2D SerDes in the case of wide I/O interface.

The oft-cited expression is that CPO has been just around the corner for the last two decades – but why has it failed to take off for so long. Why has the industry preferred to stick with pluggable DSP transceivers?

One key advantage of pluggable transceivers is their high interoperability. With standard form factors such as OSFP and QSFP-DD and adherence to OIF standards, customers can generally select transceiver vendors independent of switch and server vendors, enjoying procurement flexibility and stronger bargaining power.

Another huge advantage is field serviceability. Installing and replacing transceivers is simple as they can be unplugged from a switch or server chassis by a pair of remote hands. In contrast, with CPO any failures in the optical engine could render the entire switch unusable. Even serviceable failures could be complicated to troubleshoot and fix. Often, the laser is the most common point of failure, and most CPO implementations now use pluggable external laser source for better serviceability and replaceability, but anxiety remains regarding the failure of other non-pluggable CPO components.
