### Vera, Rubin, NVLink 6 Switch, ConnectX-9, BlueField-4, Spectrum-6, Seamless Cableless Compute Tray Design, Power Rack, VR NVL72 TCO and BoM

By [Wega Chu](https://substack.com/@wegachu), [Dylan Patel](https://substack.com/@semianalysis), [Daniel Nishball](https://substack.com/@danielnishball730869), and 8 others

Feb 25, 2026 · Paid

![](https://substackcdn.com/image/fetch/$s_!NB4l!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7257cc0c-a57b-4aa2-b03b-1ead3d930e8c_4800x2700.png)

At CES 2026, Nvidia officially announced in detail all 6 Rubin platform products: the Rubin GPU, Vera CPU, NVLink 6 Switch, ConnectX-9, BlueField-4, and Spectrum-6. VR NVL72 is the second generation of Nvidia’s rack scale Oberon architecture that takes the stage. With competition catching up on rack scale game, Trainium 3 in the Gen2 UltraServer, AMD MI450X Helios Racks, and [Google’s TPU which was at rack scale even before GB200](https://newsletter.semianalysis.com/p/tpuv7-google-takes-a-swing-at-the), Nvidia answers with “extreme co-design” supremacy. With extreme co-design, Nvidia takes rack scale integration to the next level. Rack system becomes a unit of compute, a single distributed accelerator, and Nvidia designs the system.

![](https://substackcdn.com/image/fetch/$s_!mG2N!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4d3419ee-609e-490d-999f-2454ec532c80_2683x1577.png)

Source: Nvidia

For the Vera Rubin platform, Nvidia is asserting even more control over the system and rack level design. Rack scale integration and assembly have become more challenging, as every component is being pushed to the limit, whilst also optimizing for cost efficiency. VR NVL72 has a much more holistic design with a modular approach compared to Grace Blackwell for the purpose of integration efficiency and throughput.

Nvidia’s competitiveness strengthens with its extreme co-design supremacy. It is the only player with the best in class or close to the best in class silicon product offerings for all the major silicon contents in an Nvidia trail-blazed AI server system design. Nvidia offers the best accelerator, a SOTA scale up switch, the best NIC, and one of the best Ethernet networking switch, and [a much improved purpose-designed CPU](https://newsletter.semianalysis.com/i/187132686/nvidia-vera). No other competitors have such a complete suite of integrated silicon products.

In the sections below, we will discuss the 6 silicon products of the Vera Rubin platform at the silicon level. Then, we will discuss the rack and compute tray evolution from Grace Blackwell to Vera Rubin from the design perspective and the implication to components: cables, connectors, PCB, thermal, mechanical, and power.

Next, we will discuss the major networks of the VR NVL72 system, namely the scale up NVLink 6 network and the backend scale out network. We will discuss the logistical implications of much more limited hyperscaler customisation and the assembly supplier landscape.

Lastly, the report ends with a discussion on the TCO of the VR NVL72 system as well as the BoM and Power Budget estimate supporting the TCO analysis. Behind the paywall, we also provide readers with insight into Nvidia’s plans for their Groq IP. We will also cover some of the challenges with regards to HBM ramp for Micron, SK Hynix, and Samsung.

Today we are also launching the [VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/). It provides a system-level bill of materials and power budget analysis for the VR NVL72 system covered in this article. This is important because various vendors and their shares of the subcomponents will drive whether they are winners or losers in the $500B Rubin buildout. The downstream impacts and dislocations in the market are large. The model covers:

* **Nvidia Compute Tray Content:** Strata module with Rubin GPU, Vera CPU, SOCAMM memory; BlueField-4; ConnectX-9

* **NVLink System:** NVSwitch, NVLink backplane and cabling, associated connectors, host CPU management module

* **Liquid Cooling Content: Coldplates, QDs, Manifolds**

* **PCB, Substrate, and Materials Content:** key system boards, ABF substrates, CCL content

* **Connectors**: Paladin HD2 Board to Board Connectors, Paladin HD2 NVLink 6.0 Connectors

* **Power Delivery Content**: power shelves, busbars, VRMs, power delivery modules

* **Mechanical Structure**: chassis, loading mechanism, railkits, rack chassis

* **Management modules**: BMC

* **Networking**: Transceivers, CX-9

![](https://substackcdn.com/image/fetch/$s_!FRrs!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7563ee69-3f02-47f8-944f-a7ac5b62cf0a_3362x844.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

Please visit this [self service portal](https://semianalysis.com/vr-nvl72-model/) to purchase the model. Contact sales@semianalysis.com for any questions regarding the product.
