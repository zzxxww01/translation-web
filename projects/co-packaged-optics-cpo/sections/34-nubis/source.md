Nubis was recently [acquired by Ciena](https://www.ciena.com/about/newsroom/press-releases/ciena-to-acquire-nubis-communications-to-expand-its-inside-the-data-center-strategy-and-further-address-growing-ai-workloads) in October 2025. Similar to Ayar, Nubis offers optical engine chiplets to integrate with customer host silicon, but with an emphasis on single wavelength connections. Nubis has focused on interoperability – both protocol and mechanical (I.e., pluggable) – which has determined their technology choices. Nubis also has a broader mission to address the I/O wall in general, and their solutions encompass both optics and copper.

Their existing optical engine product is the Vesta 100 1.6T NPX optical engine. It is a socketable module that offers 1.6T of bi-directional bandwidth with 16 lanes of 100G. The module has a footprint of 6x7mm. Nubis, unlike other companies, are using MZMs in large part due to the interoperability, reliability, and maturity of the modulator. The other major design choice is that the Nubis is designed to be compatible with IEEE/OIF standards-compliant electrical interfaces as they believe most ASIC developers will continue to utilize these technologies.

A key point of differentiation for Nubis is how they couple fiber. Nubis couples the surface of the PIC, and specifically they use a thin piece of glass to help route and align the fibers. Unlike edge coupling where optical fibers are connected to the chip’s edge, Nubis’s 2D fiber array approach involves connecting optical fibers from the top of the silicon photonics die.

Looking at the diagram below: the PIC (green at bottom) contains modulators, photo detectors and waveguides with EICs mounted on top. The red poles are optical fibers, while the block that contains the optical fibers is a glass block (FAU) which is used as a fiber holder. The FAU has laser-drilled holes at the top of the block to ensure exact fiber positioning. By employing a 2D fiber array, they are able to connect 36 optical fibers (16 for transmit, 16 for receive, 4 for lasers) to the PIC and avoid the need for WDM to get more lambdas over fewer fibers. This makes the Nubis FAU one of the densest currently shipping.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_070.png)

Source: Nubis

While 2D fiber arrays are on the roadmap for companies like TSMC and a key advantage to vertical coupling, no one apart from Nubis is shipping this yet which distinguishes them, though others plan to move to 2D arrays later on.

The optical fibers go up and they bend sideways by employing special optical fibers, termed FlexBeamGuidE, developed by Sumitomo Electric that is able to exhibit high reliability and low loss whilst being bent at a 90-degree angle.

Another benefit of using a 2D array rather than edge coupling is that you are less physically limited by the number of fibers that can be connected. As seen in the diagram below, using Nubis’s 2D Fiber array structure, multiple rows of optical engines can be placed around the ASIC, increasing bandwidth density provided the package permits that.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_071.png)

Source: Nubis

In April 2025, Nubis announced the availability of its next generation PIC, a 16 x 200G per lane silicon photonics IC with unidirectional beachfront density of 0.5Tbps/mm (which matches electrical host interface densities). In addition, Nubis announced a partnership with Samtec whereby Nubis would sample a 32x 200G (6.4T) optical module snap-in compatible with Samtec Si-Fly HD Co-Packaged copper connector. Compared to alternative CPO approaches, this approach enables a common copper and optical footprint; this also over time could create an open pluggable ecosystem for deploying CPO.

Lastly, in copper, Nubis has also announced and demonstrated at OFC their linear redriver chip, Nitro, for active copper cables (ACC’s) that can extend the reach of 200G over copper to several meters. This is done in partnership with Amphenol who will build ACC’s based on the Nitro linear redriver.
