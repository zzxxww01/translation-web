Ayar Labs’ product is their TeraPHY optical engine chiplet, which can be packaged into XPU, switch ASIC, or memory. The first generation of TeraPHY can deliver 2Tbit/s of uni-directional bandwidth while using just 10W of power. The second gen TeraPHY provides 4 Tbit/s of unidirectional bandwidth. It is the world’s first UCIe optical retimer chiplet, performing E/O conversion within the chiplet for transmitting the host signal optically onward. The choice of UCIe should make it attractive for customers as it has a standardized interface that can be easily implemented into their host chips.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_065.png)

Source: Ayar Labs

Ayar Labs manufactured the first two generations of TeraPHY on GlobalFoundries’ 45 nm process as a monolithic solution that integrates both electronics and silicon photonics, while the third generation of TeraPHY instead adopts TSMC COUPE. This close integration of ring modulators, waveguides, and control circuitry helps reduce electrical losses. However, the mature monolithic nodes used in the first two generations constrain the performance of the EIC and is why the first few generations of TeraPHY used a low modulation rate.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_066.png)

Source: Ayar Labs

In the 4 Tbit/s unidirectional second generation code-named “Eagle”, TeraPHY integrates eight 512 Gbit/s I/O ports, each powered by a 32 Gbit/s NRZ x 16-wavelength architecture, modulated by MRM. The external laser source, called SuperNova, is supplied by Swedish company Sivers. The laser combines 16 lambda (“colors”) into one fiber using DWDM. Each port then uses one single-mode fiber pair for transmit (Tx) and receive (Rx), meaning each 4T chiplet connects to a total of 24 fibers – 16 for Rx/Tx and 8 for laser inputs. The company employs edge coupling (EC) in its packaging process, though it is also capable of supporting grating coupling (GC).

For scaling bandwidth per chiplet, the company noted that fiber density (currently 24 per chiplet) could realistically double over the next few years as connector technology advances. Additionally, bandwidth per port/fiber could double as well by increasing the per-wavelength data rate, contributing to an overall 4x bandwidth expansion in the near future roadmap.

The SuperNova laser is MSA (Multi-Source Agreement) compliant, allowing it to interoperate with other CW-WDM standard optical components.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_067.png)

*Souce: Ayar Labs*

Ayar’s third generation of TeraPHY pivots to using TSMC COUPE and can deliver more than 3x the bandwidth of the second generation at 13.5 Tbit/s uni-directional per each optical engine, with 8 optical engines providing the ~108Tbit/s of total package scale-up bandwidth for the XPU solution featured in the Ayar Labs – Alchip collaboration below. This ~13.5+Tbit/s is achieved using ~200Gbit/s of bandwidth per lambda using PAM4 Modulation.

Though Ayar Labs has not disclosed the exact port architecture (i.e. the number of DWDM wavelengths, fibers per FAU, etc), its use of bi-directional optical links means that it will need at most ~64 fiber strands for Tx and Rx, and at most dozens more to connect to the external laser source. However – Ayar’s strategy has always been focused on WDM, meaning that that total fiber count per FAU could be as low as 32 in total. Like the first two generations, the third generation of TeraPHY continues to use Microring Modulators to enable optical chiplets to remain small while enabling CWDM or DWDM as a vector for future bandwidth scaling.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_068.png)

Source: Ayar Labs, Alchip

Ayar Labs has also partnered with Alchip and GUC to enable integration of their chiplet into Alchip and GUC’s XPU solutions. The above example illustrates an XPU with two reticle size compute dies and 8 TeraPHY optical engines, which could enable up to 108 Tbit/s uni-directional of bandwidth.

At Hot Chips 2025, [Ayar Labs shared results](https://www.youtube.com/watch?v=mZXsIfLKXrM) a slow thermal cycling link test – showing over four hours of thermal cycling at a rate of about 5C/min, demonstrating strong link BER throughout.

![](https://substack-post-media.s3.amazonaws.com/public/images/362d0b77-974d-435d-acca-af5d8464b34c_3030x1684.png)

Source: [Ayar Labs](https://www.youtube.com/watch?v=mZXsIfLKXrM)

However, studying the MRM’s resilience against rapid changes in temperature is just as important as demonstrating the stability of the link over a wide temperature range over a long period of time. In the same Hot Chips talk, Ayar explained how they opted to emulate a fast temperature ramp by sweeping laser wavelength in lieu of having an on-package ASIC that can actually perform the 0 to 500W step. Control circuits detect whether the ring resonance drifts – this can be caused by either the incoming laser changing wavelength or by a change in ring temperature, so they sweep the laser wavelength at rate that corresponds to an equivalent change in temperature. For example a 20nm/s sweep would simulate a 64C change over 0.2 seconds, amounting to 320 C/s. This study showed no bit errors for up to 800C/s of temperature change.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_069.png)

Source: Ayar Labs

Ayar Labs has a wide array of strategic backers including GlobalFoundries, Intel Capital, Nvidia, AMD, TSMC, Lockheed Martin, Applied Materials, and Downing.
