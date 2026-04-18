![](https://substackcdn.com/image/fetch/$s_!B76F!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc24a930f-d8f1-4622-96e6-9a39a7388ea5_2880x1620.jpeg)

*Direct Detection vs. Coherent-Lite vs. Coherent Transceiver Comparison. Source: Marvell, ISSCC 2026*

Marvell presented an 800G transceiver for coherent-lite applications. Traditional transceivers have a limit on how far they can reach, less than 10 kilometers. Coherent transceivers support much further reach, but they are complex, consume more power, and are more expensive. Marvell’s Coherent-lite transceiver targets a middle ground with respect to power consumption, cost and range, which is perfect for large datacenter campuses with links spanning at most tens of kilometers.

![](https://substackcdn.com/image/fetch/$s_!1xhk!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9995a322-bad8-4a3c-97e1-b84fde0aa424_2880x1620.jpeg)

*Coherent and Coherent-Lite Optical Band Comparison. Source: Marvell, ISSCC 2026*

Coherent transceivers primarily use C-band wavelengths for their low attenuation. However, the long-haul links in which coherent transmission is used typically have a very high dispersion, needing heavy DSP processing. The long range of traditional Coherent optics can often be overkill for datacenter campuses with buildings that are only tens of kilometers apart.

Coherent-Lite transceivers instead use O-band wavelengths, which have near-zero dispersion over the relatively short distances on a datacenter campus. This enables minimal DSP processing, saving power and reducing latency.

![](https://substackcdn.com/image/fetch/$s_!oACP!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0faa6bfc-c1c4-44bc-b8c8-c3b14f466c32_2880x1620.jpeg)

*Marvell Coherent-Lite Transceiver Architecture. Source: Marvell, ISSCC 2026*

The Coherent-lite transceiver is a DSP-based pluggable module consisting of two 400G channels. Each 400G channel runs a dual polarization QAM and consists of two parallel modulation streams, X and Y.

![](https://substackcdn.com/image/fetch/$s_!qDgr!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcc181023-63b7-4e6e-8769-eb69fdc1ca81_682x375.jpeg)

*Marvell Coherent-Lite Measured Link Performance. Source: Marvell, ISSCC 2026*

The key to this demonstration is highlighting other methods of scaling channel bandwidth that are optimized for the campus application.

Higher-order modulation coupled with the dual polarization using X and Y axes delivers 400G channel bandwidth. There are 8 bits per channel for a total of 32 constellation points as demonstrated above. These 8 bits times the 62.5 GBd signal rate equals ~400G of total bandwidth.

This modulation scheme is not entirely new to the industry, but it is now being brought into the datacenter campus setting for use in those shorter links.

![](https://substackcdn.com/image/fetch/$s_!jtsE!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F79b51c03-3812-498e-8f41-b9465e2c8164_2880x1620.jpeg)

*Marvell Coherent-Lite Performance vs. Prior Coherent Transceivers. Source: Marvell, ISSCC 2026*

Marvell’s approach significantly reduces power to only 3.72 pJ/b excluding silicon photonics, half of other full-fledged coherent transceivers. Their measurements were taken over a fiber length of 40km, with a latency of less than 300 ns.
