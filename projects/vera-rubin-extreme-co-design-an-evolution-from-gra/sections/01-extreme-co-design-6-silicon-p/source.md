![](https://substackcdn.com/image/fetch/$s_!ZQyU!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7cdeb372-67f9-4140-889e-2f8f493cda0a_1984x1141.png)

Source: SemiAnalysis, Nvidia

Rubin’s dense FP4 and FP8 FLOPs increase by roughly ~3.5× versus GB200, while FP16 FLOPs rise by a more modest ~1.6x, underscoring NVIDIA’s continued emphasis on FP4/FP8 as the primary scaling vector. On the memory side, HBM capacity remains flat from GB300, while HBM bandwidth scales more aggressively at ~2.8x. Overall, the architecture prioritizes bandwidth and low-precision compute.

![](https://substackcdn.com/image/fetch/$s_!m2IG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6e9330b4-7407-4dcb-8a2b-fb323371ffba_2218x1210.png)

Source: SemiAnalysis, Nvidia

### Rubin

![](https://substackcdn.com/image/fetch/$s_!u2L6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbe50555c-6427-42ca-b58e-97716f2558c9_4800x2700.png)

Source: Nvidia

Rubin’s design is a logical evolution from Blackwell, with the move to a 3nm process and disaggregating I/O into chiplets while keeping the same basic structure of 2 reticle-sized dies with 8 stacks of HBM. 35 PFLOPS dense FP4 is a 3.5x improvement over Blackwell GB200, achieved by:

* Increasing SM count from 160 to 224

* Doubling Tensor Core width in the SM to 32768 FP4 MACs/clock

* Increasing clock speed 25% from 1.90GHz to 2.38GHz

Additionally, Nvidia claims up to an effective 50 PFLOPS of FP4 performance can be achieved with an updated 3rd generation Transformer Engine that replaces 2:4 structured sparsity from prior generations. We will detail this architectural feature for Rubin below.

Notably, the Tensor core width doubling only applies to FP4 and FP8, with BF16 and TF32 remaining the same as Blackwell, resulting in performance scaling only 1.6x of Blackwell. This architectural decision reflects NVIDIA’s belief that most training and inference workloads will move away from TF32 and BF16 and onto FP8 and FP4.

On the memory front, the move to HBM4 means double the bus width per stack, running at 10.8 GT/s for 22TB/s total bandwidth or 2.75x Blackwell at the same 288GB capacity as GB300. Memory bandwidth has been upgraded significantly from the original 13TB/s advertised at GTC 2025. In order to catch up to AMD MI450’s memory bandwidth, Nvidia requested much higher HBM4 pin speeds from the DRAM suppliers - well above the speeds that was in the JEDEC specification for HBM4.

While Nvidia is targeting 22TB/s, we understand that memory suppliers are having challenges hitting Nvidia’s requirements and we see it likely that initial shipments will come in slightly below at closer to 20TB/s. [We have discussed the implications to SK Hynix, Samsung, and Micron extensively for Accelerator and HBM model subscribers.](https://semianalysis.com/accelerator-hbm-model/) Micron is well behind Samsung and Hynix and we believe [they are effectively out of the picture for Rubin HBM4.](https://semianalysis.com/institutional/semianalysis-accelerator-model-micron-zero-hbm4-share-in-rubin/) We have more details on qualifications and pin speeds in the [Accelerator and HBM model](https://semianalysis.com/accelerator-hbm-model/)

The NVLink-C2C chiplet houses the SerDes for the Vera CPU connection, doubled in bandwidth to 1.8TB/s, while the larger NVLink 6 chiplet on the other end of the chip features 36 custom ‘400G’ SerDes links for 2x NVLink bandwidth to all 72 Rubin GPUs.

Transistor count has climbed 60% to 336 billion.

A notable omission from Rubin is the mention of Sparse FLOPs. In previous generations, 2:4 structured sparsity was used to double marketing FLOPs numbers. However, adoption was minimal especially at low precisions due to accuracy losses from the rigid sparsity structure forcing half of the values to be zero. Programmers basically ignored structured sparsity as it was not useful, which caused hardware designs to change as well. Blackwell Ultra GB300 added 50% more dense FP4 while keeping sparse FP4 FLOPs the same, while AMD’s MI355X stopped supporting structured sparsity on MXFP8, MXFP6 and MXFP4 formats to save silicon area.

Rubin’s adaptive compression engine in the improved Transformer Engine is a key feature to re-boost naturally sparser inference performance by doing dynamic computation of sparsity in-flight and eliminating zeros in the data stream without zeroing out non-zero values, thus maintaining model accuracy while still boosting performance. This is done automatically on existing models built for Blackwell without the need for a new programming model or specific optimizations. While models that utilize Post Training Quantization or Quantization Aware Training will be tuned to maximize adaptive compression speedups, they are not strictly needed to take advantage of dynamic compression.

This means the sparser the workload, the closer the performance will be to the 50 PFLOPS marketed peak performance. NVIDIA thus brands the 50 PFLOPS figure as FP4 Inference while the 35 PFLOPS FP4 Training number is for dense workloads. As accuracy is preserved, this allows the marketing team to claim 5x FLOPs for Rubin over GB200, comparing 50 PFLOPS dynamically compressed FP4 to 10 PFLOPS dense FP4. Whether actual GEMM performance reaches 50 PFLOPS depends on how many zeros are in the tensor. The more zeros, the closer it can reach. The less zeros in the tensor, the lower the speedup. Overall, we expect to see much greater traction for Rubin’s adaptive sparsity compression as opposed to structured sparsity thanks to the automatic implementation.

With that said, many ML Systems engineer are still skeptical that this new form of sparsity will work well, and it is very possible that Nvidia’s 50 PFLOPS is purely marketing like prior generations

Rubin’s chip level TDP increases up to 2,300W vs 1000-1400W for Blackwell. Supply chain rumors have indicated that there are 2 different “SKUs” with different power and performance profiles: a Max-P variant at 2,300W and a Max-Q variant at 1,800W. However, these are not distinct hardware SKUs but the 2 default power profiles that Nvidia is offering users based on their workload needs. Max-Q is what Nvidia believes offers the best performance per Watt. Max-P offers the greatest absolute performance though this would come with an efficiency penalty. Running the Max-P setting results in a 20% increase in rack power draw but the performance gain fall well short of this 20% power consumption increase.

These power profiles are software managed. Users can also choose whatever max power draw they prefer (as long as it is no more than 2,300W per GPU) and this has been the case for previous GPU generations as well. Several hyperscalers and labs have chosen to run their GPUs at lower power to optimize for performance per Watt as well as taking into account power availability constraints.

![](https://substackcdn.com/image/fetch/$s_!tbcG!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F61396626-3359-4a08-8dfa-58f7ed911443_2012x1118.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

For the mechanical structure of the Rubin package, upgrades have also been made with the addition of an upgraded heat spreader and a stiffener. This compares to Blackwell B200 and B300 packages that only have a heat spreader lid. The heat spreader lid allows more equal distribution of heat exiting the package. It also provides mechanical support for the package to prevent warpage.

For Rubin, the heat spreader lid is a module made up of two separate lids. Beside the heat spreader lid, a stiffener is added to the package structure to provide even more mechanical support to avoid warpage. At the surface of the heat spreader lid, there will also be a layer of electroplated gold. The reason for this is to prevent corrosion from liquid metal TIM2, which is between the heat spreader lid and the cold plate.

### Vera

![](https://substackcdn.com/image/fetch/$s_!XgXK!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb0795695-2bda-4134-a982-12e59acc76f9_3000x3040.jpeg)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

[NVIDIA was aggressive on the CPU front](https://newsletter.semianalysis.com/i/187132686/nvidia-vera), with Vera doubling performance over Grace by moving to a 3nm reticle-sized compute die and disaggregating the memory controllers and I/O into chiplets. Core count increases from 72 to 88, with 91 cores printed on die to leave redundancy for yield improvement. These cores mark the return of NVIDIA’s custom ARM CPU designs, with the ‘Olympus’ core now supporting SMT multi-threading for a total of 176 processing threads. L3 cache also received a 40% capacity bump to 162MB. Memory bus width doubled to 1024-bit and speed increased to 9600MT/s for 2.5x bandwidth, while maximum capacity tripled to 1.5TB with 8 SOCAMM modules. The NVLink-C2C to the Rubin GPUs also doubled in bandwidth to 1.8TB/s. PCIe6 and CXL3.1 are now supported as well. All this results in transistor count increasing 2.2x to 227 billion.

### NVLink 6 Switch

![](https://substackcdn.com/image/fetch/$s_!p8aL!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F722c91c0-0b9e-43c6-9ca6-76714eb7fa70_3000x3048.jpeg)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

While the rack-level switching bandwidth has doubled, the number of NVLink Switch chips per rack has also doubled to 36, with each switch tray now housing 4 Switch chips. This means the new NVLink 6 Switch chip has the same 28.8T bandwidth as NVLink5 Switch, with half the number of ports but running at double the rate using ‘400G’ bi-directional SerDes. This allows the high bandwidth switch design to remain as a single monolithic die, saving on design complexity. The layout remains the same as NVIDIA’s previous switches, with 2 sides for IO and a central logic section crossbar and 3.6 TFlop SHARP in-network compute acceleration.

### ConnectX-9

![](https://substackcdn.com/image/fetch/$s_!so7W!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fcb34a228-9fff-45eb-8851-68a1d54acf66_1781x1780.jpeg)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

The ConnectX-9 is largely iterative from ConnectX-8, with the same 800G networking bandwidth and 48-lane PCIe6 switch capability. However, CX-9 now supports 800G Ethernet with 4x200G PAM4 SerDes, compared to CX-8 that only supported it on InfiniBand. For the Rubin platform, NVIDIA is doubling the number of NICs per GPU to achieve 2x scale-out bandwidth.

### BlueField-4

![](https://substackcdn.com/image/fetch/$s_!Wfwi!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F60828488-61bb-416d-a9c8-df3e8fe3c284_2506x1673.jpeg)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

BlueField-4’s design departs significantly from BlueField-3. Instead of doing a bespoke tapeout with compute and networking, NVIDIA simply reuses their large Grace CPU die, co-packaged with a ConnectX-9 die to make an 800G DPU with massive compute capabilities. 128GB of LPDDR5 feeds the Grace CPU at half the bandwidth of regular Grace. That is 4x the memory capacity of BlueField-3. BlueField-4 can also function as a storage controller, with four BF-4 chips in each Context Memory Storage system.

### Spectrum-6

![](https://substackcdn.com/image/fetch/$s_!qbIl!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2e1932aa-e7cf-438e-bc2a-984a03d9cd25_3000x2983.jpeg)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

While not part of the Rubin NVL72 rack, Spectrum-6 CPO enables even larger scale-out clusters with its doubled radix. The design retains the same features as Spectrum-5, with 8 IO chiplets surrounding the main switch die. 102.4T switching bandwidth is achieved with 512x 200G SerDes. 32 3.2T optical engines on the package convert these electrical signals to optical links, each with a detachable fiber connector. The SN6810 features one of these chips, while the SN6800 houses four, multiplexed together to create a 409.6T switch box. There will also be a non-CPO version with pluggable OSFP cages in the SN6600. The non-CPO version will be more common in our view.
