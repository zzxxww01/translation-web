The groupings of TPCs into GPCs we presented above are *logical* groupings. They represent software’s view of the GPCs, with no information about which of the 20 actual physical SMs in each GPC are enabled, or where each physical GPC is located on the two dies. In reality, B200 chips with the same logical configuration need not have exactly the same physical SMs yielded in each GPC. This can be a potential source of performance non-determinism between GPUs which otherwise might look the same from the view of software. Additionally, the logical groupings of SMs into GPCs tells us nothing about which GPC is on each of the two dies in the B200 package.

To discover more information about the physical layout of the SMs, we have every SM traverse a pointer-chase array that fills L2 cache, measuring the latency of each load. For each address, we compare the latency seen from each SM to the latency seen by every other SM, to produce an SM`<->`SM distance matrix. X and Y axes are SM ID.

![](https://substackcdn.com/image/fetch/$s_!1JbI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F59a90c5b-7a40-4984-9872-717122402fe0_1600x1353.png)

We can see two clear sets of SMs, separated by >300 cycles average distance to L2; this must be the die-to-die crossing. We’ve also labeled the SMs with their logical GPC groupings as identified in the last section; interestingly, the singleton TPCs are close together and seem to correlate well with GPC0 in this benchmark, so one might guess that those TPCs physically reside on GPC0.

Based on this information, we can refine the list of yielded TPCs for each GPC, though the 5+3 is still just a guess.

**Die A**: [10, 10, 10, 9]

**Die B**: [9, 9, 9, 5+3]

Additionally, though in a roundabout way, we can conclude that the die-to-die latency penalty is roughly 300 cycles. This is also evident when looking at the latency profile for a singular SM from the benchmark (which also includes a lot of L2 congestion):

![](https://substackcdn.com/image/fetch/$s_!U0jj!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbec3b195-e042-4f89-b7b7-52e79a20d31b_2048x1015.png)

We would like to thank Orian from Decart AI for the benchmark inspiration.
