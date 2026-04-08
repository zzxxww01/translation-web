NVIDIA claims specific throughput performance for different input data types, and here we show their claims for each (format + CTA group) and compare them with the max achievable throughput. We show that UMMA achieves near peak throughput for all formats and CTA groups, and even on 2SM versions where coordination overhead may be a concern.

![](https://substackcdn.com/image/fetch/$s_!gMEj!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd489809c-16d0-40d2-a3a5-030760568f0f_1600x800.png)

For 1SM MMA across all N sizes, we see that the smaller M=64 achieves max 50% theoretical peak throughput, and the larger M=128 achieves near 100%. This confirms that M=64 is utilizing half of the datapath. For 2SM MMA, we see that M=128 throughput starts at 90% peak for N=64 and reaches near 100% for all other N sizes. M128N64 throughput must be bound at a different hardware unit such as TMEM, L2, SMEM, etc. Meanwhile, M=256 sustains near 100% peak throughput across all configurations, this is because M=256 is M=128 per SM, which can utilize the full datapath. We note that throughput is identical across formats with the same data type bit width, and micro-scaling data types have virtually no overhead.

![](https://substackcdn.com/image/fetch/$s_!7P-g!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F17602e21-9606-451d-a8bc-3899ae442688_1600x695.png)

MMA supports two different AB layouts: Both input matrices stored in SMEM (SS), and matrix A stored in TMEM and matrix B stored in SMEM (TS). We observed that for M=128, while ABLayout=TS achieves near peak throughput, ABLayout=SS underperforms in smaller N sizes and catches up at N=128.

![](https://substackcdn.com/image/fetch/$s_!V8NQ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F314106a3-52a8-427e-9fcf-8be00badccc9_1600x617.png)

We can show that this is because the instruction itself is SMEM bandwidth bound below N=128 for SS mode. For example, for FP16 we know the hardware can do 8192 MMA FLOPs per cycle per SM, and the SMEM bandwidth is 128 B/cycle (per SM). So for M=128 N=64 K=16, we have:

`A_bytes = 2*M*K = 4096; B_bytes = 2*N*K = 2048;`

`FLOPs = 2*M*N*K = 262144`

`SMEM Cycles = (A_bytes + B_bytes) / (128 B/clk) = 48 cycles`

`Math Cycles = FLOPs / (16384 FLOPs/clk) = 32 cycles`

We compute this for increasing N and find we are finally Math limited starting from the N=128 instruction.

![](https://substackcdn.com/image/fetch/$s_!xHgb!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3700253d-db8b-462b-bdaa-6b03e9c1578d_1188x562.png)

The same is true for other datatypes - MMA instructions with both operands in SMEM are SMEM-bound below N=128.

To further illustrate the point, we plot the roofline for all shapes of FP8 1SM MMA. We see clearly that the N < 256 is at the memory-bounded region, and the slope is roughly 128 bytes / cycle, the SMEM bandwidth.

![](https://substackcdn.com/image/fetch/$s_!-agO!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2b6f6282-c294-432c-97fe-6646a3b9bacd_1517x948.png)

2SM MMA achieves perfect weak scaling across all formats and shapes, reaching 2x speedup when using 2x the amount of compute resources than 1SM MMA. In smaller shapes of ABLayout=SS, we observe over 2x speedup, which again happens because the instruction is SMEM bound below N=128 for SS and the 2SM version splits operand B between the two SMs.

![](https://substackcdn.com/image/fetch/$s_!pG8O!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc143b70f-f950-4e8f-a9de-7ce2d956f605_1600x1020.png)

*SS mode: Over 2x speedup for N < 128 due to being SMEM bound*

![](https://substackcdn.com/image/fetch/$s_!CSsj!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F76693f90-cbc0-428e-a2fd-84e872810fa8_1600x1020.png)

*TS mode: Near-perfect 2x speedup*

These experiments show that you should always use the largest instruction shape available for a given SMEM tile size to get maximum throughput.
