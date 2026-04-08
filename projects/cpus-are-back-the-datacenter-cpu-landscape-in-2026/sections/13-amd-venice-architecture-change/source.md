![](https://substackcdn.com/image/fetch/$s_!hYF-!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5ccdb80a-accb-4092-90d4-09ebda6b6953_1530x1600.png)

*AMD Venice die layout. Source: @HighYieldYT*

While Intel went away from EMIB, AMD finally adopts the equivalent advanced packaging technology for Venice, with high-speed short reach links connecting the CCDs to the I/O die. We have the volumes for this in our [Accelerator, HBM, and Advanced Packaging Model.](https://semianalysis.com/accelerator-hbm-model/)

The additional shoreline required for the CCD links takes up additional width, necessitating the central I/O hub to be split into 2 dies. This creates another die to die hop to cross the different halves of the chip, forming another NUMA domain that Intel’s solution avoids. The I/O dies now feature 16 memory channels in total, up from 12 in 2022’s Genoa. AMD also catches up to Intel in finally supporting Multiplexed memory for higher bandwidth, where 16-channel MRDIMM-12800 gives 1.64TB/s, 2.67x Turin.

AMD has also moved to a mesh network within the CCD, with 32 Zen6c cores in a 4x8 grid, although there may be an additional spare core included for yield recovery. Eight TSMC N2 CCDs bring core counts to 256, a one-third increase from the 192-core Turin-Dense 3nm EPYC 9965. Zen6c receives the full 4MB L3 cache per core that was previously halved on Zen5c, creating large 128MB cache regions per CCD.

Lower core count and frequency optimized “-F” SKUs for AI head nodes will employ the same 12-core Zen6 CCD design used in their consumer desktop and mobile PC line for up to 96 cores across 8 CCDs. While this is a regression from the 128-core Turin-Classic 4nm EPYC 9755, it does bring 50% more cores than the high frequency 64-core EPYC 9575F.

Lastly, 8 small dies can be seen beside the I/O dies next to where the DDR5 interface exits. These are Integrated Passive Devices (IPD) that help smooth power delivery to the chip in the heavily I/O dense area, where the SP7 package routing is saturated with memory channel fanout.

![](https://substackcdn.com/image/fetch/$s_!0aVL!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe982a29b-8dbe-48a8-b2d8-a5a595d09ffe_3053x1668.png)

*AMD Venice Performance Claims. Source: AMD*

On the performance front, AMD claims the top 256-core variant is over 1.7x better in performance per watt than the top 192-core Turin in SPECrate®2017\_int\_base, meaning an even higher performance per core thanks to the new Zen 6 core microarchitecture with higher Instructions per Clock (IPC). Zen 6 also introduces new instructions for AI datatypes including AVX512\_FP16, AVX\_VVNI\_INT8 and a new AVX512\_BMM instruction for Bit Matrix Multiplication and bit reversal operations on the CPU’s floating point unit.

For BMM, the FPU registers store 16x16 binary matrices and computes BMM accumulates using OR and XOR operations. Binary matrices are far easier to compute than floating point matrices, and could offer large efficiency gains for software that can make use of it such as Verilog simulations. However, BMMs do not have sufficient precision for LLMs, and so we believe adoption of this instruction will be limited.

As AMD already enjoys significantly higher performance per core than Intel (96c Turin matches 128c Granite Rapids), the performance gap between AMD Venice and Intel Diamond Rapids will widen even more in the 2026 to 2028 generation of datacenter CPUs. Core to core latency on Venice should improve over Turin thanks to the new die to die interconnect and larger core domains.

AMD is also doubling down where Intel is pulling out. While Intel cancels its 8-channel processor, AMD will introduce a new 8-channel Venice SP8 platform as a successor to the EPYC 8004 Siena line of low power, smaller socket offerings, while still bringing up to 128 dense Zen 6c cores to the table. With this, AMD will see large share gains in the enterprise markets, a traditional Intel stronghold.
