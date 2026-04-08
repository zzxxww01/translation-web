Let’s look at the LPX rack system, which has interesting details. Nvidia has displayed an LPX rack with 32 1U LPU compute trays with 2 Spectrum-X switches. This 32 tray 1U version that Nvidia has shown off at GTC is very close to Groq’s original server design before the acquisition. We believe that this server configuration is not the version that will be shipped in 3Q, with Nvidia implementing changes. Here, we will detail what we know about the actual production version. This was already detailed in the [Accelerator model](https://semianalysis.com/accelerator-hbm-model/).

![](https://substackcdn.com/image/fetch/$s_!_fd4!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F105f4b85-95b2-49c0-ad0a-7afa73fddff1_434x860.png)

Source: SemiAnalysis [Accelerator Model](https://semianalysis.com/accelerator-hbm-model/)

#### LPX Compute Tray

Each LPX compute tray or node has 16 LPUs with 2 Altera FPGAs, 1 Intel Granite Rapids host CPU and 1 BlueField-4 front-end module. As with other Nvidia systems, hyperscalers customers can and will use their own Front-end NIC of choice rather than paying for Nvidia’s BlueField.

![](https://substackcdn.com/image/fetch/$s_!6E50!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F45fbdc52-ed59-45e7-b666-5315c454d94b_1354x1851.png)

Source: SemiAnalysis [Accelerator Model](https://semianalysis.com/accelerator-hbm-model/)

The LPU modules are mounted in a belly-to-belly on the PCB, meaning 8 LP30 modules on the top side of the PCB and the other 8 LP30 modules on the bottom. All of the connectivity that comes out of the LPU are via PCB traces and given the dense all-to-all mesh for intra-node connections this requires a very high spec PCB to support the routing. The belly-to-belly mounting is used to reduce PCB trace lengths across the ‘X’ and ‘Y’ dimensions.

![](https://substackcdn.com/image/fetch/$s_!RBl1!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F57bb1916-27a0-42d5-85c7-0f81c305cb3c_1839x399.png)

Source: SemiAnalysis [Networking Model](https://semianalysis.com/ai-networking-model/)

Something interesting about the system is the important role the FPGAs play. Nvidia refers to the FPGAs as “Fabric Expansion Logic” which serves multiple purposes. First, they act as a NIC which converts the LPU’s C2C protocol into Ethernet to connect to the Spectrum-X based ethernet scale-out fabric. It is this scale-out fabric through which the LPUs connect to GPUs in the decode system.

Second, the LPUs also traverse through the FPGAs to reach the host CPU, with the FPGAs converting C2C to PCIe to the CPU.

Third, the FPGAs are connected to the backplane to talk to other FPGAs in the node, we believe this is to help manage control flow and timing of all the LPUs. The FPGAs also bring extra system DRAM of up to 256GB each. This pool of memory can be used for KVCache if the user wants the entire decode process served by the LPX.

On the front panel there are 8 x OSFP cages for cross-rack C2C, while there will be 2 cages (likely QSFP-DD) that goes to the Spectrum-switches that is used to connect the LPUs and the GPUs for the disaggregated decode system. We will share more about this when we describe the network.
