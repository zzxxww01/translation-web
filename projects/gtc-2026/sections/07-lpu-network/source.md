The LPU network can be divided into the scale-up ‘C2C’ network and scale-out network which interacts with the Nvidia GPUs through Spectrum-X. First let’s discuss the scale-up network which can be divided into 3 portions: intra-node, inter-node/intra-rack, inter-rack. For C2C within the rack Nvidia announced a total of 640TB/s of scale up bandwidth per rack which comes from 256 LPUs x 90 lanes x 112Gbps/8 x 2 directions = 645TB/s. Note that Nvidia uses the total 112G line rate rather than 100G of effective data rate.

#### Intra-Tray Topology

![](https://substackcdn.com/image/fetch/$s_!i4Vn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ff5b18381-6c96-4d0f-912e-e7978cc30446_1414x1617.png)

Source: SemiAnalysis [Networking Model](https://semianalysis.com/ai-networking-model/)

Within each tray or node, all 16 LPUs are connected to each other in an all-to-all mesh. Each LPU module connects to the 15 other LPUs within the node with 4x100G of C2C bandwidth. Note that this ‘C2C’ is not related to NVLink, but Groq’s own scaleup fabric. These connections are all via PCB trace, which necessitates an extremely high spec PCB to support this routing density. This is why the belly-to-belly layout is used: it reduces the ‘X’ and ‘Y’ distance between all the LPUs and instead have routing go in the ‘Z’ dimension.

The LPU also has 1x100G going to one FPGA, with each FPGA interfacing with 8 LPUs. The 2 FPGAs each have 8x PCIe Gen 5 going to the CPUs. The LPU needs to traverse through the FPGA to interface with the CPU as LPUs don’t have PCIe PHYs to interface directly.

#### Inter-node/Intra-rack

![](https://substackcdn.com/image/fetch/$s_!xA-t!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F25d7c5ea-dce9-4703-9d95-eda3887a2e72_1066x1155.png)

Source: SemiAnalysis [Networking Model](https://semianalysis.com/ai-networking-model/)

Each LPU connects to one LPU from each of the 15 other nodes in the server. Each of these inter-node links is 2x100G so there are 15x2x100G inter-node links coming out of each LPU. These inter-node links are via a copper cable backplane. In addition, each FPGA also connects to an FPGA in every other node at either 25G or 50G per link for 15x25G/50G. This also goes through the backplane. This means that each node has 16 x 15 x 2 lanes for inter-node C2C and 2 x 15 lanes for inter-node FPGA which is a total of 510 lanes or 1020 differential pairs (for Rx and Tx). Therefore, the backplane is 16 x 1020/2 = 8,160 differential pairs – we divide by 2 as each device Tx channel is a corresponding device’s Rx channel.

#### Inter-rack

![](https://substackcdn.com/image/fetch/$s_!Wn2b!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Feaf1f2a7-972d-4d67-b1e8-aa596dcca070_3060x4100.png)

Source: SemiAnalysis [Networking Model](https://semianalysis.com/ai-networking-model/)

Lastly, there is the inter-rack C2C. Each LPU has 4x100G lanes that go to the OSFP cages to connect LPUs across 4 racks. There are various configurations that can be used for this inter-rack scale up. One option is 4x100G from each LPU going to one OSFP cage, each OSFP escaping 800G of C2C from 2 LPUs. However, for greater fan out the preferred configuration seems to be each 100G lane from the LPU going to 4 individual cages, with each cage escaping 800G of C2C from 8 LPUs. In terms of how the racks are networked together it appears to be a daisy chain configuration, with each Node0 connected to 2 other Node 0. This can all be achieved within the reach of 100G AECs, though optics can be used if necessary.
