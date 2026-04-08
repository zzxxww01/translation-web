The MMA instruction is the core operation that performs matrix multiplication. MMA performance has grown increasingly shape-dependent from Hopper to Blackwell. Here we investigate this phenomenon, sweeping through different shapes and data types to quantify the performance differences.

Blackwell comes with 2SM MMA, a new type of MMA instruction (`.cta_group::2`) where a CTA pair collaboratively executes one MMA operation across 2 SMs. Specifically, the input matrix A is duplicated while matrix B and D are sharded across the 2 SMs, and the CTA pair can access each other's shared memory. This enables even larger MMA shapes. We investigate whether 2SM MMA exhibits weak scaling, strong scaling, or both.

We benchmarked MMA performance with a configuration space below:

![](https://substackcdn.com/image/fetch/$s_!Vi8a!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3b115c81-e5c1-4904-a640-9d239536fbd1_1342x412.png)
