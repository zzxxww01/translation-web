Since the announcement of GB200 at Nvidia GTC 2024, the concept of an AI server system has shifted from a chassis to a rack scale system. In our **[GB200 article](https://newsletter.semianalysis.com/p/gb200-hardware-architecture-and-component)**, we discussed the evolution of Nvidia AI server form factor from HGX (8 GPU per node) to Oberon (NVL72 rack scale). While the HGX form factor still exists, the majority of Nvidia’s Blackwell GPUs are integrated in the Oberon form factor. Rubin will also be offered in both HGX and Oberon systems.

The key difference between the Blackwell and Rubin Oberon architecture is the number of SKUs offered to customers. As Blackwell Oberon was the first ever mass deployment of a rack scale solution with rack power density over 100KW for the GB200 NVL72 SKU, many datacenters did not have the infrastructure ready to support 100kw+ per rack. Nvidia offered two SKUs of Blackwell Oberon: GB200 NVL72 and GB200 NVL36x2. The latter being a lower density SKU offered for customers who did not have the infra ready to handle the thermals of a single high density rack. We discussed the difference between the two form factors in the **[GB200 article](https://newsletter.semianalysis.com/p/gb200-hardware-architecture-and-component)**[.](https://newsletter.semianalysis.com/p/gb200-hardware-architecture-and-component)

Unlike Blackwell, Rubin is only offered in the VR NVL72 SKU. The set up is very similar to that of GB200/GB300 NVL72. Each VR NVL72 system consists of:

* 72 Rubin GPU packages

* 36 Vera CPUs

* 36 NVLink 6 Switch ASICs

![](https://substackcdn.com/image/fetch/$s_!xB_f!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F42660b70-c898-4e6b-a117-7490baf5ae4c_733x1702.png)

Source: [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

On a side note, VR NVL72 was initially known as VR NVL144 as [Jensen math](https://newsletter.semianalysis.com/i/174558496/jensen-math-changes-every-year) from GTC 2025 defined the number of GPU as the number of GPU compute die in system (with 2 compute dies per package and 72 Rubin packages per Oberon rack = 144 compute die). The naming was changed back to VR NVL72 to represent the 72 Rubin GPU packages in the system in late December. This was right before CES 2026 where the naming was officially confirmed as VR NVL72.

### CPX Form Factor

![](https://substackcdn.com/image/fetch/$s_!BH0r!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F30fd28ad-beb1-46a4-844e-bab6c4d4b216_1507x1697.png)

Source: [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

Although Nvidia initially planned to integrate the CPX accelerator into the VR NVL72 rack, the current development suggests that CPX will only be offered as a standalone rack as we detailed in [our article introducing Nvidia](https://newsletter.semianalysis.com/p/another-giant-leap-the-rubin-cpx-specialized-accelerator-rack) **[CPX](https://newsletter.semianalysis.com/p/another-giant-leap-the-rubin-cpx-specialized-accelerator-rack)** . To recap Rubin-era system planning in our previous CPX article, Nvidia initially contemplated three VR NVL72 configurations:

* **VR NVL72 (Regular):** Standard Oberon VR NVL72 without CPX

* **VR NVL72 CPX (Integrated):** Rubin GPU and Rubin CPX within the same compute tray

* **VR NVL72 CPX (Dual Rack):** Rubin CPX deployed in a separate rack alongside the VR NVL72 rack

The standalone/dedicated rack direction materially changes the deployment calculus. A dual-rack approach allows hyperscalers to scale prefill and decode capacity independently, optimize datacenter power envelopes, and reduce system-level failure domains versus tightly coupled trays. More importantly, it formalizes architectural disaggregation between inference prefill (compute-bound) and decode (bandwidth-bound).

Rubin CPX was originally architected as a GDDR7-based accelerator optimized for prefill, based on three key considerations:

* Prefill is primarily FLOPs-limited, not bandwidth-limited, making HBM less indispensable.

* HBM’s increased bandwidth is structurally underutilized in prefill.

* GDDR7 offers materially lower cost per GB and avoids the need for 2.5D packaging,

However, Nvidia began exploring HBM-equipped variants for prefill, either via modified CPX configurations or through lower memory spec (such as using HBM3E) Rubin deployments dedicated to prefill, which we [noted](https://semianalysis.com/institutional/rubin-delay-and-gb300-revision-b30a-h200-rubin-cpx-hbm-update-new-specs-sheet/) this way back in [early December last year](https://semianalysis.com/institutional/rubin-delay-and-gb300-revision-b30a-h200-rubin-cpx-hbm-update-new-specs-sheet/) in our [Accelerator & HBM model](https://semianalysis.com/accelerator-model/).

We also think a lot this shift is driven by evolving memory economics. **Conventional DRAM pricing has risen sharply:** As DDR pricing increases, the relative premium of HBM compresses because pricing is more locked down in long term contracts, narrowing the cost gap between a GDDR-based CPX and lower-spec HBM configurations, therefore eliminating a lot of the cost benefits GDDR offers relative to performance. While memory bandwidth is not as important for pre-fill compare to decode, it is still necessary.
