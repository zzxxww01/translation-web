NVIDIA revealed its CPO Roadmap at the GTC Keynote 2026, with Jensen following up with additional commentary in the Financial Analyst Q+A meeting held the following day. Though many had their hopes up for CPO to be used for scale-up within the rack for Rubin Ultra Kyber, Nvidia’s focus was instead on using CPO to enable larger world size compute systems.

![](https://substackcdn.com/image/fetch/$s_!7CeZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7d80c4f7-60e6-41ea-859b-f4ad8ddbf5ea_2064x397.png)

Source: [SemiAnalysis AI Networking Model](https://semianalysis.com/ai-networking-model/), Nvidia

**In the Rubin Generation**, Nvidia will offer the Rubin GPU in an Oberon NVL72 form factor with an all-copper scale-up network. For Rubin Ultra, as we expected, there will only be a copper scale-up option for Rubin Ultra in the Oberon and Kyber Rack form factor. Rubin Ultra will also be offered in a larger world size system that connects 8 Oberon Racks of 72 Rubin Ultra GPUs to form what will be referred to as NVL576. CPO scale-up will be used to build the larger world size, connecting between the racks in a two-tier all to all network, though scale-up inside the racks will remain copper-based.

**When we reach the Feynman Generation**, CPO usage will expand via another large world size rack, the NVL1152 which is formed by combining 8 Kyber racks. While the [Nvidia Technical Blog](https://developer.nvidia.com/blog/nvidia-vera-rubin-pod-seven-chips-five-rack-scale-systems-one-ai-supercomputer/) that outlines the rack configuration roadmap states that “NVIDIA Kyber will scale up into a massive all-to-all NVL1152 supercomputer using similar direct optical interconnects for rack-to-rack scale-up”, Jensen Huang in a Financial Analyst Q+A session did say that NVL1152 in Feynman would be “all CPO”. There is some disagreement on whether copper will still be used for scale-up within the rack or whether CPO will replace copper.

Nvidia’s approach has been to use copper where they can, and optics where they must. The architecture of NVL1152 in the Feynman generation will follow the same principle. It is clear that the NVL1152 will adopt CPO to connect between racks, but from GPUs to NVLink Switches is currently copper POR. Nvidia is unable to achieve another doubling of electrical lane speed from 224Gbit/s bi-di to 448Gbit/s uni-di means bandwidth isn’t that amazing.

While 448G high speed SerDes have big challenges for shoreline, reach, and power versus using a die-to-die connection to an optical engine, the manufacturing challenges, cost, and reliability for Feynman necessitate using copper to the Switch.

With that said, the NVL1152 SKU is years out – and the roadmap is highly likely to shift. For now, our base case stands at copper being used within each rack and CPO between the racks, but this could easily change.

For now – our best estimate of Nvidia’s CPO roadmap is as follows:

Rubin:

* NVL72 – Oberon all copper scale up

Rubin Ultra:

* NVL72 – Oberon all copper scale up

* NVL144 – Kyber rack all copper scale up

* NVL288 – Kyber rack all copper scale up with copper connecting 2 racks together

* NVL576 – 8x Oberon Racks copper scale up within rack and CPO on switch between racks in a two tier all to all topology. This would be low volume for test purposes

Feynman:

* NVL72 – Oberon Rack – All Copper

* NVL144 – Kyber Rack – All Copper

* NVL1152 – 8xKyber Rack – Copper within rack and CPO on the switch between racks

![](https://substackcdn.com/image/fetch/$s_!NjAg!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F10cf337a-41ad-4a0e-b9a3-bd2f11c911f0_2389x905.png)

Source: SemiAnalysis, Nvidia
