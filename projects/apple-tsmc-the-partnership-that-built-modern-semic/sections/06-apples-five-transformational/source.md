Apple’s overarching semiconductor philosophy is simple but ruthless: control the “primary technologies” that differentiate the product. This journey, which began with the A4 in 2010, has evolved into a comprehensive internalization strategy. It’s not just about the CPU (A-series/M-series); Apple has systematically replaced suppliers for almost every critical subsystem, developing custom silicon for Audio (H-series), Security (T-series), Wireless (W-series), Ultra-Wideband (U-series), and now Spatial Computing (R-series). The acquisition of Intel’s modem business in 2019 was the final piece of this puzzle, aiming to displace Qualcomm and complete the complete silicon independence.

![](https://substackcdn.com/image/fetch/$s_!T7QL!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F525ffa40-53d6-4bb0-b973-29dfacb9ebf1_1428x1299.png)

![](https://substackcdn.com/image/fetch/$s_!Ucm1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7d4acf1b-5410-4bd3-92ba-06c13b9cae5d_2546x728.png)

![](https://substackcdn.com/image/fetch/$s_!kX3T!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8d0e0494-d6e0-4615-aaaa-8e13050a8c93_2546x671.png)

![](https://substackcdn.com/image/fetch/$s_!TRXa!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8abc4e05-96d6-4198-aaf9-d36aba20cba4_2546x600.png)

![](https://substackcdn.com/image/fetch/$s_!qiO_!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F54e3d4f8-4dd7-4145-9be2-e499a9f727f2_2548x722.png)

![](https://substackcdn.com/image/fetch/$s_!D3JM!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F84ad5390-5034-4b76-8fe9-06e27a069db4_2544x851.png)

1. **P.A. Semi (2008, $278M): The Foundation**

P.A. Semi was a boutique chip design firm founded by Dan Dobberpuhl, one of the most respected processor architects in the industry (creator of DEC Alpha, StrongARM). The company had 150 engineers designing low-power, high-performance processors.

The team designed the A4, Apple’s first custom SoC. Jim Keller, who later designed AMD’s Zen architecture, led the A4/A5 development at Apple before departing. 2. **AuthenTec (2012, $356M): Touch ID**

Touch ID launched 13 months after the AuthenTec acquisition. AuthenTec’s architecture enabled the Secure Enclave, the hardware security subsystem that handles all biometric and cryptographic operations.

The Secure Enclave enabled Apple Pay (2014). A decade on, Apple Pay enabled $1.5T+ in transaction volume (2024). The $356M acquisition justified a financial services business that generates billions in annual revenue. A chip architecture decision in 2012 enabled a $100B+ Services business a decade later. 3. **PrimeSense (2013, $360M): Face ID**

PrimeSense developed the 3D depth-sensing technology behind Microsoft’s Kinect. Apple bought them for $360M and spent four years miniaturizing the technology to fit in a phone notch.

The TrueDepth camera projects 30,000 infrared dots onto your face, maps the 3D structure, and authenticates in milliseconds. Face ID is more secure than Touch ID (1 in 1,000,000 false positive rate vs. 1 in 50,000).

The same technology enabled Animoji, Memoji, and became the foundation for LiDAR Scanner in the iPhone 12 Pro. 4. **Intel Modem Business (2019, $1B): In-house 5G Modem**

Apple bought Intel’s smartphone modem business the same week they settled their lawsuit with Qualcomm. The timing was intentional. The settlement was a temporary truce.

With Intel, Apple acquired 2,200 engineers (modem design, RF, validation), 17,000 wireless patents, Labs, equipment, IP across San Diego and Munich

The 5G modem was the final frontier for Apple and despite delays, the C1 modem shipped in iPhone 16e (2025), after five years of development. By 2027-2028, Apple expects to eliminate Qualcomm entirely in its lineup, offering it a gross margin stacking opportunity. 5. **The Imagination Breakup (2017): In-House GPU**

Apple has licensed GPU designs from Imagination Technologies since the original iPhone. In April 2017, Apple notified Imagination they would stop using their IP within 15-24 months. Imagination’s stock dropped 70% overnight.

Apple had secretly built an internal GPU team. The A11 (September 2017) shipped with Apple’s first custom GPU. The Apple GPU delivered 30% better performance than Imagination’s designs.

Imagination nearly went bankrupt. They were sold to a Chinese-backed private equity firm. By 2020, both companies settled their disputes and entered into multi-year licensing agreements.

### Global Design Operations

Apple operates 8,000+ chip engineers across 15+ design centers on four continents:

![](https://substackcdn.com/image/fetch/$s_!L_yD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F66058ace-743d-430d-9cb3-fc188726f24a_2364x878.png)

Israel is where Apple’s CPU performance leadership is designed. The Herzliya team, many recruited from Intel Israel, which created Pentium M, Core, and Sandy Bridge architectures, designs the Firestorm, Avalanche, and Everest cores that dominate benchmarks.

The same country that gave Intel its best architectures now designs Apple chips that beat Intel.

The San Diego facility is squarely targeted at Qualcomm. Apple’s modem design operation sits literally down the street from Qualcomm’s headquarters. The office is staffed largely with ex-Qualcomm and ex-Intel engineers, people who know exactly how Qualcomm’s modems work and how to beat them.

### DTCO: Design-Technology Co-Optimization

Apple co-defines the Process Design Kit (PDK) with TSMC. TSMC effectively dedicates hundreds of engineers to Apple, creating what is essentially a “virtual IDM” (Integrated Device Manufacturer). When Apple dictates a need for wider memory buses or specific transistor architectures, TSMC adjusts the PDK to match.
