When the lasers enter the PIC, they undergo a modulation phase (driven by drivers) where electronic signals are encoded into laser’s wavelength. The three primary types of modulators used for this process are Mach-Zender Modulators (MZMs), Micro-Ring Modulators (MRMs), and Electro-Absorption Modulators (EAMs). Each individual lambda (individual wavelength on an individual optical lane) requires one modulator.

### Mach-Zehnder Modulator (MZM)

MZM encodes data by splitting a continuous-wave optical signal into two waveguide arms whose refractive indices are varied by an applied voltage. When the arms recombine, their interference pattern modulates the signal’s intensity or phase.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_040.png)

Source: Luceda Academy

MZMs are the easiest of the three to implement and have low thermal sensitivity, reducing the need for precise temperature control. Their high linearity supports advanced modulation formats like PAM4 and coherent QAM (although QAM is not suitable for HPC/AI workloads). MZM’s Low chirp improves signal integrity for higher-order modulation and long-distance transmission. MZMs also enable higher bandwidth per channel: 200G per lane has been proven working, and 400G per lane is believed possible with non-coherent PAM modulation.

However, MZM’s drawbacks are:

* **Large form factor with dimensions measured in millimeter scale for** ***length*** (compared to MRM in micron scale), since they require two waveguide arms and a combining region, consuming more chip area and limiting the density of modulators (and thus channels) contained in an OE PIC. MZM sizes are on the order of ~12,000µm2, GeSi EAMs at around 250µm2 (5x50µm) with MRMs at between 25µm2 and 225µm2 (5-15µm2 in diameter). This is one critical drawback of MZMs that can limit scaling. However, if one considers the size of a full PIC/EIC combination, including drivers and optical/ electrical control circuitry around the modulators, MZMs size disadvantage could appear less notable,

* **High power consumption**, as the phase-shifting process demands significant energy. It also has higher bias conditions – basically initiating voltages – than MRM (which operates at sub-voltage). However, firms like Nubis are trying to develop clever designs to ameliorate the power disadvantages of MZMs.

In the startup ecosystem, Nubis is one of the firms that mainly utilize MZM for their scale-up CPO solutions. MZMs are not widely selected in the startup ecosystem due to its large form factor and limited number of lambdas.

### Micro-Ring Modulators (MRMs)

MRM uses a compact ring waveguide coupled to one or more straight waveguides. An electrical signal alters the ring’s refractive index, shifting its resonant wavelength. By tuning resonance to align or misalign with the input light, MRMs modulate the optical signal’s intensity or phase, thereby encoding data.

A light source is passed into the ring from the input port – for most wavelengths of light, there will be no resonance in the ring such that the light will pass through the device, from the input port to the through port. If the wavelength satisfies the resonance condition, then light will constructively interfere in the ring, and will be instead pulled into the drop port. As illustrated in the normalized power graph below, light of a specific wavelength will cause a sharp peak in transmission power at the drop port and a corresponding drop in transmission at the through port. This effect can be used for modulation.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_041.png)

Source: [Sam Palermo, Texas A&M University](https://people.engr.tamu.edu/spalermo/ecen689_oi/lecture11_ee689_rrm_tx.pdf)

Optical Engines typically use multiple MRMs, and each of these rings can be tuned to a different wavelength, enabling wavelength division multiplexing (WDM) using the rings themselves as opposed to requiring an additional set of devices to accomplish WDM.

MRMs have a few key advantages:

* The are extremely compact (scale in the tens of microns), allowing far higher modulator density than MZMs. MZM sizes are on the order of ~12,000µm2, GeSi EAMs at around 250µm2 (5x50µm) with MRMs at between 25µm2 and 225µm2 (5-15µm2 in diameter);

* Rings are very well-suited for WDM applications (including DWDM with 8 or 16 wavelengths), and built-in mux/demux functionality;

* MRMs can be highly energy efficient (lower power per bit);

* And finally - rings have low chirp, which improves signal quality.

However, MRMs also come with a few challenges:

* MRMs can be 10-100 times more temperature-sensitive than MZMs and EAMs, requiring very precise control systems that are challenging to design and manufacture;

* They are non-linear, complicating higher-order modulation like PAM4/6/8;

* MRMs’ sensitivity and tight temperature control tolerances can make standardization difficult, since each design has precise requirements.

Among the solution providers, Nvidia has a clear preference for MRMs. They claimed to be the first to design and put MRMs in CPO systems. The company believes MRM’s key advantages are its compact size and low driving voltage, which helps reduce power consumption. However, MRM technology is also known to be difficult to control, making design precision crucial for successful implementation – which is indeed an strength of Nvidia.

In terms of fabrication, TSMC’s advanced CMOS expertise is well suited for fabricating MRMs with high-precision and great Q-factor. In addition, Tower also bring strong fabrication capabilities to their photonics nodes.

MRMs are challenging to implement but is certainly feasible. They can potentially enable higher bandwidth densities than MZMs. That’s why TSMC, Nvidia, and many CPO companies such as Ayar Labs, Lightmatter, and Ranovus, focus on this technology roadmap.

### Electro-Absorption Modulators (EAM)

[EAMs modulate signals](https://people.engr.tamu.edu/spalermo/ecen689_oi/lecture10_ee689_eam_tx.pdf) by altering their ability to absorb light based on the voltage applied. More specifically, when low or no voltage is applied to an EAM, the device allows most of the incoming laser light to pass through, making it appear transparent or “open.” When a higher voltage is applied, the band gap of a GeSi modulator shifts to cover the high C-band range (above 1500nm), increasing the absorption coefficient for those wavelengths and attenuating “closing” the optical signal that is passing through the nearby waveguide. This is known as the Franz-Keldysh effect. This switching between “open” and “close” states modulates the intensity of the light, effectively encoding data onto the optical signal.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_042.png)

Source: [Texas A&M University, Liu 2008, Helman 2005](https://people.engr.tamu.edu/spalermo/ecen689_oi/lecture10_ee689_eam_tx.pdf)

The same principle is used today in transceivers that use Electro-Absorption Modulated Lasers (EMLs) for modulation. A continuous wave (CW) distributed feedback (DFB) lasers and an InP based EAM is coupled together to build up a single discrete EML, which can modulate one lane. For example, an 800G DR8 transceiver uses 8 EMLs across 8 individual fiber lanes, each using PAM4 modulation (2 bits/signal) and signaling at ~56 GBaud. Unlike GeSi based modulators, the band gap of an InP modulator corresponds to the O-band (1310nm) which is the standard wavelength used is all Datacom DR optics, allowing a great degree of interoperability.

InP modulators have a few downsides that make it less than ideal for use in CPO. InP wafers tend to be small (3” or 6”) and suffer from low yields – both factors drive up unit costs for InP-based devices when compared to Silicon which can be built on 8” or 12” processes. Coupling InP to Silicon is also far more difficult than coupling GeSi to other silicon devices.

EAMs have several advantages compared to MRMs and MZIs:

* Clearly – both EAMs and MRMs have control logic and heaters that act to stabilize both against variations in temperatures, but EAMs have fundamentally less sensitivity to temperature. Compared to MRMs, EAMs have much better thermal stability above 50° C while MRMs are very sensitive to temperature. A typical stability of 70-90 pm/C for MRMs mean that a 2° C variation shifts resonance by 0.14nm, well beyond the 0.1nm resonance shift at which MRM performance collapses. In contrast, EAMs can tolerate an instantaneous temperature shift of up to 35° C. This tolerance is important in particular for Celestial AI’s approach as their EAM modulator resides within an interposer beneath a high-XPU power compute engine that dissipates hundreds of watts of power. EAMs can also tolerate high ambient temperature ranges of around 80° C which may be applicable for chiplet applications which sit next to the XPU and not beneath it.

* Compared to MZIs, EAMs are much smaller in size and consume less power as the relatively large size of MZIs requires a high voltage swing, amplifying the SerDes to achieve a swing of 0-5V. Mach Zender Modulators (MZMs) are on the order of ~12,000µm2, GeSi EAMs at around 250µm2 (5x50µm) with MRMs at between 25µm2 and 225µm2 (5-15µm2 in diameter). MZIs also require more power usage for the heaters needed to keep such a large device at the desired bias.

On the other hand, there are a few drawbacks in using GeSi EAMs for CPO:

* Physical modulator structures built on Silicon or Silicon Nitride such as MRMs and MZIs have been perceived to have far greater endurance and reliability than GeSi based devices. Indeed, many worry about the reliability of GeSi based devices given the difficulty of working with and integrating Germanium-based devices, but Celestial argues that GeSi based EAMs, which are essentially the reverse of a Photodetector, are a known quantity when it comes to reliability given the ubiquity of photodetectors in transceivers today.

* GeSi modulators’ band edge is naturally in the C-band (i.e. 1530nm-1565nm). Designing quantum wells to shift this to the O-band (i.e. 1260-1360nm) is a very difficult engineering problem. This means that GeSi based EAMs will likely form part of a book-ended CPO system and cannot easily be used to participate in an open chiplet-based ecosystem.

* Building out a laser ecosystem around C-band laser sources could have diseconomies of scale when compared to using the well-developed ecosystem around O-band CW laser sources. Most datacom lasers are built for the O-band but Celestial points out that there are considerable volumes of 1577nm XGS-PON lasers manufactured. These are typically used for consumer fiber to the home and business connectivity applications.

* A SiGe EAM has an insertion loss of around 4-5dB vs 3-5 dB for both MRMs and MZIs. While MRMs can be used to directly multiplex different wavelengths, EAMs require a separate multiplexer to implement CWDM or DWDM, adding slightly to the potential loss budget.

Overall, EAMs are not widely used in current CPO implementations, with Celestial AI standing out as one of the few companies actively pursuing this approach.
