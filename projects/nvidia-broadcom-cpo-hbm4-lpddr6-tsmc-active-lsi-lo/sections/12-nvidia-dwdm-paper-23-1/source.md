The choice of optical signaling format will affect the go-to-market timeline for scale-up co-packaged optics (CPO). Nvidia is ramping up production of COUPE optical engines that support 200G per lane PAM4 for scale-out switching in the near-term.

![](https://substackcdn.com/image/fetch/$s_!gqo1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa1a30ce9-0d17-45f9-9e83-026ba5f0a876_2880x1620.jpeg)

*Nvidia DWDM Architecture Overview. Source: Nvidia, ISSCC 2026*

However, at ISSCC, Nvidia proposed using 32 Gb/s per lambda, with 8 wavelengths multiplexed using DWDM. A 9th wavelength is used for clock forwarding at half rate — that is 16 Gb/s.

Clock forwarding means that SerDes can be made somewhat simpler by removing the Clock and Data Recovery (CDR) circuit as well as other circuitry, improving energy and chip shoreline efficiency.

Earlier in March, just before OFC 2026, the [formation of the Optical Compute Interconnect MSA](https://www.businesswire.com/news/home/20260312254951/en/Optical-Scale-up-Consortium-Established-to-Create-an-Open-Specification-for-AI-Infrastructure-Led-by-Founding-Members-AMD-Broadcom-Meta-Microsoft-NVIDIA-and-OpenAI) (OCI MSA) was announced, and it will focus on a 200 Gb/s Bi-directional link, with each of transmit and receive formed using 4 lambdas of 50G NRZ, which will be sent bi-directionally across the same fiber. Did I hear anyone mention OCS?

![](https://substackcdn.com/image/fetch/$s_!Eh4Q!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F62c2c764-5aab-4981-aedc-1e6ba3864cf4_2869x1869.jpeg)

*OCI MSA Optical Link Specifications. Source: [OCI MSA](https://oci-msa.org/)*

Interestingly, the OCI MSA did not make use of an additional wavelength for clock forwarding, and it appears that reserving all wavelengths for actual data transmission is the priority.

Much of Nvidia’s published research on scale-up CPO has centered on DWDM, though today’s CPO optical engines are oriented around 200G PAM4 DR Optics, which makes more sense for scale-out networking. The OCI MSA centering around DWDM for scale-up optics resolves this apparent contradiction, as it is now clear that Nvidia and others will center around the use of DWDM for scale-up and DR Optics for scale-out.

The OCI MSA also illustrates different implementations, an On-Board Optics (OBO), a version of CPO that is integrated via the substrate on the ASIC package, and a version where the optical engine is integrated directly on the interposer. The implementation illustrated in the middle figure (b) will be the most common one used for scale-up and scale-out CPO for the next few years, but it still requires some form of serialized links that can pass through the ASIC substrate and will still require some form of SerDes on both sides. For example, UCIe-S could be used as a protocol for such transmission.

![](https://substackcdn.com/image/fetch/$s_!r0uo!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F02eb01f6-1c42-4388-b07d-744346a1d768_2262x1962.jpeg)

*Optical Engine Integration Levels (OBO, Substrate CPO, Interposer CPO). Source: [OCI MSA](https://oci-msa.org/)*

The “Final Boss” when it comes to implementing CPO will be when the optical engine can be integrated onto the interposer itself, connecting to the ASIC using a parallelized die to die (D2D) connection as depicted in (c) above. This could considerably improve shoreline bandwidth density, enable much higher radix and improve energy efficiency. This implementation thus unlocks benefits of CPO in ways that the other implementations cannot, but achieving it is still a few years away and requires further improvements in advanced packaging technology.
