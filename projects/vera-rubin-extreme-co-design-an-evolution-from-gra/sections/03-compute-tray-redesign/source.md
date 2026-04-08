One of the major changes with VR NVL72 is within the compute tray. This redesign of the compute tray is centered around simplifying assembly, namely eliminating cables from the compute tray as cables have been the major point of failure of GB200/300 assembly. As Jensen put it at CES 2026, the cableless design reduces the compute tray assembly time from 2 hours to 5 minutes. To achieve this, the VR NVL72 compute tray adopts a modular design with the modules connecting to each via board-to-board connectors.

![](https://substackcdn.com/image/fetch/$s_!PGJb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fff713757-9939-4bc5-a9b7-b21ea415c5bc_832x1398.png)

Source: [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/institutional/rubin-delay-and-gb300-revision-b30a-h200-rubin-cpx-hbm-update-new-specs-sheet/)

To understand the compute tray of VR NVL72 we must first understand the 6 modules that make up the VR NVL72 compute tray:

1. Strata Module x 2 2. Orchid Module x4 3. Compute Tray Midplane x 1 4. Power Delivery Module x 1 5. BlueField-4 Module x 1 6. System Management Module x 1

We break down these components costs and all the subcomponent costs in the [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/).

### Strata

![](https://substackcdn.com/image/fetch/$s_!3S86!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3e60d518-4f27-49ac-b476-45433bca8a0a_911x1066.png)

*Strata Module, Source: [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)*

![](https://substackcdn.com/image/fetch/$s_!0YnS!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F4ccb2f3a-f952-4300-bc34-96c1470be6ba_1032x1080.png)

*Bianca Module. Source: [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)*

Situated at the back of the chassis, the Strata module of VR NVL72 is the equivalent of the Bianca board of GB200/300. It houses two Rubin GPUs and one Vera CPU. Unlike Bianca, the LPDDR5X memory for Vera is socketed via SOCAMM module. 8 SOCAMM sockets are placed on the left and right of Vera. Two SOCAMM modules of different capacities are offered, 192GByte and 128GByte, for a maximum of 1,534GByte and a minimum of 1,024GByte per Vera. The Connect-X NICs mezzanine module is also taken off the Strata module as CX-9 is moved to the front of the chassis. Under the cableless design, all the cable connector ports are also removed and replaced by Paladin HD2 board-to-board connectors at the bottom of the module. On the other side, the same set of Paladin HD2 backplane connectors as GB200 and GB300 are identically placed at the back of the module connecting to the NVLink 6 Switches via the NVLink backplane.

### Orchid

![](https://substackcdn.com/image/fetch/$s_!764T!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F74182e8e-49ce-4a30-b7bd-c2b0a35b6419_584x1115.png)

Source: [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

The Orchid Module houses two ConnectX-9 NICs, two 800G transceiver cages, and one E1.S module slot. Four Orchid modules sit at the front of the chassis. With two Orchid modules stacked on top of each other, they occupy the front left and front right chassis space. At the end of the module there is one Paladin HD2 board-to-board connector that mates with the connector on the midplane. The Orchid module is slim and long, allowing the PCIe 6 signal to travel from the midplane to the CX-9 NICs at the front of the chassis.

### Midplane

![](https://substackcdn.com/image/fetch/$s_!bnHy!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1b2c77d5-6f60-4022-9753-07ffa81846fe_1089x814.png)

Source: [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

The midplane acts as a bridge for the PCIe signal between the two Strata modules and the modules at the front of the chassis. The midplane module is vertically placed across the middle of the chassis with Paladin HD2 board-to-board connector on both sides of the module. Strata modules connect to one side of the midplane while the Orchid modules, the BlueField-4 module, the PDB module, and the management modules connects to the other side.

### BlueField-4

![](https://substackcdn.com/image/fetch/$s_!9hkF!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fea791cfc-972f-4952-b1fd-283e63357743_823x1648.png)

Source: [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

The BlueField-4 DPU sits in center of the front of the chassis between the left-side Orchid module and the management module. As mentioned in the sections above, BlueField-4 is made up of a Grace CPU and a CX-9 NIC. The module also comes with 128GByte of on board LPDDR5x, 512Gbyte of on board pluggable SSD and an integrated AST2600 BMC from Aspeed. In the reference design of the VR NVL72 compute tray, BlueField-4 acts as a DPU providing up to 800Gb/s of front end networking capability. However, just like BlueField-3, BlueField-4 will only be adopted by a handful of customers, namely CoreWeave and other smaller Neoclouds customers who have less customization capability. For most hyperscalers’ deployments, the BlueField-4 module will be replaced with their in-house frontend networking module or simply with a CX-9 which is cheaper.

Speaking of BlueField-4, it is important to discuss the new offering Jensen highlighted at CES earlier this year: ICMS, or Inference Context Memory Storage — a platform that we hear may be rebranded to “CMX” at GTC. ICMS, or CMX, introduces a third, entirely separate network dedicated solely to context memory. CMX is a purpose-built KV cache fabric. As long-context inference pushes context windows toward millions of tokens and agentic concurrency scales across users and services, the current memory hierarchy used to store KVcache begins to look insufficient.

KV cache grows linearly with sequence length and multiplicatively with workload parallelism, quickly expanding beyond what any single tier of memory was designed to hold. GPU HBM, while unmatched in bandwidth and latency, is not enough on its own to store KV especially for longer sequence length queries that are becoming popular between turns or tool calls. Host DRAM extends capacity but remains node-bound and limited in aggregate footprint and ultimately has limited capacity. Meanwhile, traditional shared storage—architected for durability rather than latency —has more access time and power overhead, making it unsuitable for participation in the decode loop.

As we noted in mid-January in our [Memory Model note](https://semianalysis.com/institutional/ssd-and-storage-anchoring-note-the-best-is-yet-come/), Nvidia's ICMS inserts a new G3.5 tier between local SSD (G3) and shared storage (G4), optimized specifically for ephemeral, recomputable KV cache. The ICMS requires a dedicated networking layer designed exclusively for KV traffic. Wherever networking is used in this architecture, it is provisioned as a context memory network — isolated from general data movement and optimized for predictable decode latency.

The challenge with this is that the volumes of SSDs going to ICMS / CMX are quite overblown by the industry. We worked through the math in the [Memory model](https://semianalysis.com/memory-model/) and [Tokenomics model](https://semianalysis.com/tokenomics-model/).

BlueField-4 will be the silicon anchor of this third network. Positioned on the storage array, it terminates NVMe-oF and RDMA traffic at line rate and manages KV movement independently of host CPUs and GPUs. With 2×400G SerDes links providing 800Gb/s of bandwidth, integrated Grace CPU, and LPDDR, BlueField-4 would act as the controller for a distributed context memory fabric. In a preferred DGX-style configuration, a single BlueField-4 per tray may serve four Rubin processors, with the DPU dedicated purely to KV cache traffic and not shared with generic storage I/O.

The new CMX/ICMS ecosystem will likely include leading storage providers such as Weka, DDN, Dell Technologies, NetApp, VAST Data, and others.

### Power Delivery

The power delivery module sits above the BlueField-4 module. The module receives 50V power from the internal busbar cable. Then the current is stepped down to 12V with a modular power brick. Then, 12V current is delivered to the Orchid module, the BlueField-4 module, the management modules via smaller internal busbars.

In the [VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/) we have the breakdown of the power delivery content for BlueField, Strada board, and the rest of the rack’s components.

### System Management

The management module is made up of multiple smaller management modules that fall under this category. These modules occupy a long slim space between the BlueField-4 module and the right-side Orchid modules. The management modules are the following:

* System Management Module (SMM)

* Trusted Platform Module (TPM)

* Datacenter Secure Control Module (DC-SCM)

These modules provide management security functions over the compute tray. Hyperscalers usually have their own in-house management module design. Therefore, the management modules may be different for each end customer. Besides BlueField-4, the power delivery module and the management modules are the only other two components within the compute tray that Nvidia allows customization for. Some end customers are considering integrating the management modules into the power delivery module. Nevertheless, the modules need to follow the form factor that Nvidia provides so it can fit into the designated connector on the compute tray midplane.

### Compute Tray Topology

The compute tray topology of VR NVL72 is roughly similar to that of GB200 and GB300. The three main differences to Grace Blackwell are the connections between GPU and ConnectX NICs, the connections to the local NVMe storage, and the connection between the BlueField-4 and ConnectX-9.

![](https://substackcdn.com/image/fetch/$s_!9T2Z!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F571bad1d-efd0-4475-8d55-1563d0c00448_3772x1694.png)

Source: [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

![](https://substackcdn.com/image/fetch/$s_!xV2T!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F596ff1e3-1d12-4353-8d7f-c71ac273ae75_3105x2014.png)

Source: [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

Firstly, the connection between the GPU and the ConnectX NICs evolved from GB200 to GB300 then to Vera Rubin. For GB200, the GPU does not have direct access to the ConnectX-7. Instead, B200 connects to Grace CPU via C2C connection then the Grace CPU talks to the ConnectX-7 over PCIe 5. For GB300, Nvidia introduced NIC direct to ConnectX-8, which allows the B300 GPU to communicate directly with the ConnectX-8 NIC without going through the Grace CPU.

Essentially, this means ConnectX-8 has two hosts, Grace CPU and B300 GPU. This improves latency in the backend network. However, for VR NVL72, the direct connection between Rubin GPU and ConnectX-9 is reverted back to the same design as GB200, as Rubin does not have PCIe bandwidth for two Connect-9. Rubin connects to Vera via C2C link, then Vera will connect to ConnectX-9 via PCIe6 lanes.

Secondly, the local NVMe storage for Rubin has been moved to a different location from that of NVMe storage in Grace Blackwell. Previously, local NVMe storage was managed by BlueField-3. For VR NVL72, the local NVMe storage is physically on the Orchid module managed by the ConnectX-9.

![](https://substackcdn.com/image/fetch/$s_!299t!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fedcb2919-19ac-481a-851c-24e14c7eedee_3422x2419.png)

Source: [Nvidia](https://developer.nvidia.com/blog/redefining-secure-ai-infrastructure-with-nvidia-bluefield-astra-for-nvidia-vera-rubin-nvl72/), [Nvidia VR NVL72 BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

Lastly, the BlueField-4 DPU is able to control the 8 ConnectX-9 backend NICs allowing for unified management of both front end north-south network & back end high speed East-West networks. This system, known as Advanced Secure Trusted Resource Architecture (Astra), thus takes the provisioning and monitoring load off of the host CPU. The only issue with this is that BlueField-4 is expensive, so we expect most hyperscale customers to deploy their in-house DPU solutions instead. We will discuss customization more in the later sections.

### Evolution from Blackwell

All of these modules in the VR NVL72 compute tray, while not exactly the same, are found in the compute tray of GB200/300. The only difference is the midplane module as it is a new component introduced to eliminate internal cables form the compute tray. Also, the modules at the front of the chassis (daughter modules) are much longer than their equivalent in Blackwell to connect the signal from the midplane to the front I/O ports via PCB. In the sections below we will discuss the cableless design, the changes in thermal design, and the changes in mechanical design in the compute tray.
