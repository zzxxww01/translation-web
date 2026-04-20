TSMC is racing ahead as the foundry partner of choice for the next generation of OEs for both the fabless giants and startups. The first high-volume products featuring CPO endpoints are being introduced under the name “COUPE” - short for “Compact Universal Photonic Engine”. This includes the fabrication of EICs and PICs, as well as heterogeneous integration under TSMC’s COUPE solution. Nvidia proudly displayed their COUPE optical engines at GTC 2025, and these will be the first COUPE products to ship. Broadcom is also adopting COUPE for their future roadmap, despite having existing generations of their OEs with other supply chain partners. As mentioned earlier, Ayar Labs, who has previously relied on Global Foundries’ Fotonix platform for monolithic optical engines, now also has COUPE on their roadmap.

Unlike its dominance in traditional CMOS logic, TSMC previously had a limited presence in silicon photonics, where Global Foundries and Tower Semi were the preferred foundry partners. However, in recent years, TSMC has been quickly catching up when it comes to their photonic capabilities. TSMC also brings its unquestionable strength in leading edge CMOS logic for the EIC component, as well as its leading packaging capabilities – TSMC is the only foundry that has successfully demonstrated die-to-wafer hybrid bonding capabilities at reasonable scale, having shipped various AMD hybrid bonded chips in volume. Hybrid bonding is a more performant approach to bond the PIC and EIC, though it does comes with a significantly higher cost. Intel is working to develop a similar capability but has faced significant challenges in pioneering this technology.

Overall, TSMC has now become a very key player in CPO despite its previously weaker standalone SiPho capabilities. Like other major players, TSMC aims to capture as much of the value chain as possible. By adopting TSMC’s COUPE solution, customers effectively commit to using TSMC-manufactured PICs, as TSMC does not package SiPho wafers from other foundries. Many CPO focused companies have indeed pivoted decisively towards making TSMC’s COUPE as part of their go to market solution for the next few years.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_032.png)

Source: TSMC

**Die fabrication**: TSMC offers a comprehensive suite of solutions for die fabrication. The EIC is manufactured on the N7 node, integrating high-speed optical modulator drivers and TIAs. It also incorporates heater controllers to enable functions such as wavelength stabilization. The PIC, on the other hand, is fabricated on the SOI N65 node, and TSMC provides extensive support for photonic circuit design, photonic layout design and verification, as well as simulation and modeling of photonic circuits (which covers aspects such as RF, noise, and multi-wavelength).

EICs and PICs are bonded using the TSMC-SoIC-bond process. As we mentioned previously, longer trace lengths mean more parasitics, which degrades performance. TSMC’s SoIC is a bumpless interface offering the shortest trace length possible without being monolithic and is therefore the most performant possible way to heterogeneously integrate the EIC and PIC. As shown below, at iso-power, SoIC based OEs offer more than 23x the bandwidth density of an OE integrated with bumps.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_033.png)

Source: TSMC

COUPE supports the whole optical engine design and integration process. For optical I/O, it supports µLens design, enabling the integration of micro-lenses at the wafer or chip level, as well as optical I/O path simulations covering mirrors, µLenses, grating couplers (GC), and reflectors. For 3D stacking, it supports 3D floorplanning, SoIC-X/TDV/C4 bump layout implementation, interface physical checking, and high-frequency channel model extraction and simulation. To ensure seamless development, the company provides a complete PDK and EDA workflow for COUPE design and verification, enabling designers to implement their technologies efficiently.

**Coupling**: As we will detail more later, there are two main coupling methods – grating coupling (GC) and edge coupling (EC). COUPE uses one common EIC on PIC bumpless stacking structure for both GC and EC. However, the COUPE-GC structure will distinctively use Silicon lens (Si lens) and MR (metal reflector), while COUPE-EC will uniquely have EC facet (for terminating EC to fiber). In the case of GC, the Si lens is designed on a 770µm silicon carrier (Si-carrier) and the MR is positioned directly underneath the GC, along with the optimization dielectric layers required for optical performance. The Si-carrier is then WoW (wafer-on-wafer) bonded to a CoW (chip-on-wafer) wafer.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_034.png)

Source: TSMC

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_035.png)

Source: TSMC

**Fiber Attach Unit (FAU)**: The FAU needs to be co-designed according to the optical path of COUPE. The purpose of the FAU is to couple the light from Si lens into the optical fiber at low insertion loss. The manufacturing difficulty increases as number of I/O increases, but development time and costs are reduced if industry can adhere to specific standards. Overall, each component requires an optimized design to achieve the best optical performance.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_036.png)

Source: TSMC

**Product roadmap**: The first iterations of COUPE will be optical engines on the substrate with the ultimate goal being able to put the OEs on the interposer. The interposer offers far more I/O density, therefore enabling greater bandwidth between the OEs and the ASIC PHYs, with the possibility of individual OEs having up to 12.8Tbit/s of bandwidth each, translating to approximately 4 Tbit/s/mm. The challenge for integrating the interposer is scaling the interposer size (which is more expensive than the package substrate) to accommodate the OE.

This is why Broadcom is transitioning to TSMC COUPE for its CPO solutions, despite having iterated multiple generations of CPO using a Fan-Out Wafer-Level Packaging (FOWLP) approach developed by SPIL. Notably, Broadcom has committed to COUPE for its future switch and customer accelerator roadmaps. We understand that the FOWLP approach doesn’t allow scaling beyond 100G per lane due to excessive parasitic capacitance, as electrical signals must pass through the Through-Mold Vias (TMV) to get to the EIC. To maintain a competitive roadmap, Broadcom must transition to COUPE, which offers superior performance and scalability. This highlights TSMC’s technological edge, enabling them to secure wins even in optics, a domain where they have historically been considered weaker.

![](https://substack-post-media.s3.amazonaws.com/public/images/52efaf06-fa1a-4c3d-95b3-c4510f59128c_1312x738.png)

Source: Broadcom

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_037.png)

Source: Broadcom
