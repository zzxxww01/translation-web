In the [GB200 article from 2024](https://newsletter.semianalysis.com/p/gb200-hardware-architecture-and-component), we discussed the previous evolution on power delivery from node level PSU (power supply unit) to centralized rack level power shelf. As VR NVL72 rack TDP reaches 180kW-220kW per rack from 120kW-140kW for GB200 and GB300, the power delivery infrastructure has evolved yet again. In the section below we will discuss the power delivery infrastructure at the rack level of the reference design and the power delivery at the compute tray level for VR NVL72.

Since the deployment of GB200, the main theme of the power delivery infrastructure evolution has been about transmission efficiency and power stability. Hyperscalers are developing power delivery infrastructure to address the challenges that comes with high density AI server racks with the roadmap set to 1MW per rack in the next couple of years. Hence, HVDC (high voltage direct current) power rack, BBU (battery back up units), CBU (capacitor backup units), liquid cooled busbar, and SST (solid state transformers) are being developed to increase transmission efficiency and power stability. These will be deployed by customers depending on their proprietary infrastructure designs. [For more detail on this, we wrote about the challenge on the grid with AI training in this report.](https://newsletter.semianalysis.com/p/ai-training-load-fluctuations-at-gigawatt-scale-risk-of-power-grid-blackout)

![](https://substackcdn.com/image/fetch/$s_!YedG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F06dbd2aa-7e3c-4f9a-ab81-60bcc8b26b5c_733x1702.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

For the VR NVL72 reference design, the power delivery infrastructure at the rack level includes four 110kW power shelves. The VR NVL72 system has a TDP up to 220kW for the 2300W Rubin TDP SKU. The design with four 110kW power shelves is an N+1 redundancy approach. Each 110kW power shelf is 3U tall and includes six 18.3kW PSU with built in capacitors in the PSU. Each power shelf receives three phase 415VAC-480VAC of power from two 100A whips. The power shelves step down the power from 415VAC-480VAC to 50VDC and sends it to the busbar. Interestingly, the busbar of VR NVL72 is rated for 5000A+, which is much higher than that of Grace Blackwell at 2900A. Given the extremely high current and the lack of fans in the rack, the busbar has to be liquid cooled.

![](https://substackcdn.com/image/fetch/$s_!mnFo!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fea4bba56-9812-4977-8f9e-201a0cab7ff1_1640x940.png)

Source: TE Connectivity, OCP 2025

For the hyperscale customers, they might choose to deploy a standalone power rack either in LVDC (low voltage direct current) or HVDC (high voltage direct current). Below we provide two possible scenarios of the power rack deployment for VR NVL72.

![](https://substackcdn.com/image/fetch/$s_!HQjd!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F882952fa-6781-496c-b90a-2bcb9eb0f1bc_3165x2172.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

First, VR NVL72 rack with an HVDC power rack running at 800VDC (Nvidia Spec) or +/-400VDC (OCP Spec). Since the VR NVL72 rack busbar is still running at 50V and the compute tray can only take in 50V, the 800VDC from the power rack cannot be directly delivered to the busbar. There would still be DC-DC power shelves in the VR NVL72 rack. The DC-DC power shelves will step down the voltage of the current from 800VDC to 50VDC as demonstrated below.

![](https://substackcdn.com/image/fetch/$s_!nFTK!,w_720,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F003855a3-c39f-4c22-a4bc-3783e1b20428_1460x833.png)

Source: OCP, Meta, SemiAnalysis

Second, some customers, namely Meta, may look to integrate their network switch rack with BBU and CBU shelves for efficiency and peak shaving. This allows more CBU and BBU capacity that wouldn’t have been able to fit in the GPU rack. The BBU/CBU and switch rack will be connected to the GPU rack with 50V horizontal busbars. Meta calls this the high power rack, discussed at OCP.

We have more detailed power and architecture details in our [VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/).
