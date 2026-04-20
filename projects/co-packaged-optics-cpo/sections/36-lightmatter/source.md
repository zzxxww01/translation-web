Lightmatter is well known for its Optical Interposer product, the Passage™ M1000 3D Photonic Superchip, but is also introducing a number of solutions to cater to the various phases of the CPO roadmap, with a number of chiplets being taped out at TSMC.

The first solution to come to market will be optical engines for Near Packaged Optics (NPO) in 2026/2027. In an NPO solution, the Optical Engine would be soldered to the baseboard, with copper connecting LR SerDes on the XPU to the Optical Engine. Lightmatter’s optical engine will support up to 3 FAUs with 40 fiber strands per FAU, for a total of 120 fiber strands. The NPO strategy is premised on the idea that Hyperscalers’ first step in adopting CPO will be to first gain operational experience with NPO, which derisks the product given the Hyperscaler need not “commit” to CPO as it can elect to ultimately use either optical or copper scale-up solutions to interface with LR SerDes on the XPU or switch.

As Lightmatter’s optical engine solution is based on TSMC COUPE and the GF 45nm SPCLO process, many vectors of scaling are on the table. In addition to delivering 200Gbit/s (uni-directional) per lane via 100Gbaud PAM4, it can also support 200Gbit/s on PAM4 with DWDM8 or 100Gbit/s on PAM4 using DWDM16 to achieve 3.2T per fiber.

While some of the other CPO companies have opted to use the merchant laser source ecosystem, Lightmatter has developed its own external laser source known as GUIDE, which is currently sampling. While other laser sources singulate InP wafers to create discrete laser diodes, GUIDE, the industry’s first Very Large Scale Photonics (VLSP) laser, which is a new class of laser that integrates hundreds of InP lasers onto a single silicon chip to support up to 50 Tbit/s of bandwidth. Lightmatter claims to bring a unique control technology to manage these many InP lasers that also has the benefit of increasing overall reliability by overprovisioning the number of InP lasers and allowing “self repair” by swapping in still functioning diodes. The Nvidia Quantum-X CPO Switch featuring 144 ports of 800G requires 18 ELSs, and Lightmatter claims that two GUIDE laser sources could cater to this same overall bandwidth requirements.

Lightmatter aims to align with the COUPE roadmap offering CPO solutions in earnest in 2027 and 2028 then focus on its flagship Passage™ M1000 solution in 2029 and beyond.

Lightmatter’s M1000 3D Photonic Superchip, is a 4,000 mm² optical interposer that is placed below the host compute engine and takes care of signal conversion from electrical to optical. The M1000 was [demonstrated in a live rack-scale demonstration at SC25](https://youtu.be/Gjee92kYmwg?si=bP09-v5rALXtwOkY), and Lightmatter has made it available as a reference design. Passage uses TSVs to deliver electrical signals and power between the XPU and the optical engine, and uses SerDes to connect the two. By placing the ASIC directly on the optical interposer, Passage eliminates the need for large, power-hungry SerDes. Instead, it utilizes 1,024 compact, lower-power SerDes (~8x smaller than conventional SerDes) to enable a total I/O bandwidth of 114Tbit/s (each SerDes operating at 112Gbit/s). By placing the ASIC directly on top of the optical interposer, the chip shoreline constraint is also relieved.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_084.png)

Source: Lightmatter

The system incorporates built-in OCS that manages redundancies – if one communication route fails, traffic can be rerouted through an alternate path to ensure uninterrupted operation in such a large-scale system. Additionally, neighboring tiles are electrically stitched together, enabling them to communicate electronically using interfaces such as UCIe.

Passage uses MRMs with diameters of ~15 µm, each integrated with a resistive heater, and achieves 56 Gbit/s NRZ modulation. The module consists of 16 horizontal buses, each capable of carrying up to 16 colors (wavelengths). These colors will be supplied by GUIDE, which delivers 16 wavelengths per fiber on a 200 GHz grid.

Passage utilizes 256 optical fibers, each carrying 16 wavelengths unidirectionally (or 8 wavelengths bi-directionally) via DWDM, delivering between 1 Tbit/s and 1.6 Tbit/s of bandwidth per fiber. To improve yield, they have minimized the number of fibers attached to the chip, reducing complexity and manufacturing challenges. Additionally, they have implemented a fiber attach system that allows faulty fibers to be easily disconnected from the panel and replaced, enhancing reliability and serviceability. The table below reflects the different modes that Passage supports currently.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_085.png)

Source: [Lightmatter](https://www.youtube.com/watch?si=QXXxGjE8Yv8gvSRB&t=265&v=Gjee92kYmwg&feature=youtu.be)

One of the key debates regarding PASSAGE is the thermal stability of the MRMs used given that the optical interposer is located directly beneath a very hot XPU. By comparison, other approaches to CPO do not envision the modulators being placed directly beneath the XPU, and as such are easier to thermally manage. In response to this point, Lightmatter has explained that the control loops used for MRMs in PASSAGE can handle 2,000C per second of excursion and can handle temperatures of between 0 to 105C – that is to say a 60 to 80C temperature transition could occur within 10ms without disrupting the optical links.

The [SC25 demonstration](https://www.youtube.com/watch?v=Gjee92kYmwg) video depicted an illustration of temperature variation of between 25C to 105C showing a wide range of operating temperatures, though this particular but with the 80C transition taking around one minute – for a fairly low 1.33C per second excursion, but a separate demonstration also at SC25 using an on-chip thermal aggressor reached the 2,000C/s rate, with the MRM stabilizer heater allowing a far lower range of -2 to +2 C/s at the MRM itself.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_086.png)

Source: Lightmatter
