Within each Feynman Kyber rack, we tentatively assume double the bandwidth per logical GPU and double the NVLink Switch bandwidth to 28.8T and 57.6T respectively. Though Jensen, in the Financial Q+A the day after the GTC Keynote, characterized NVL1152 as “all CPO”, the key [technical blog outlining the new rack form factors](https://developer.nvidia.com/blog/nvidia-vera-rubin-pod-seven-chips-five-rack-scale-systems-one-ai-supercomputer/) only strictly referenced CPO for rack to rack interconnect. We will discuss the potential topography for both options.

To double the scale-up bandwidth using copper interconnect, NVIDIA would have to achieve a per lane bandwidth of 448Gbit/s uni-di (and implemented with simulatanous bi-directional SerDes so that each physical channel carries 448G of RX and 448G of TX). However, this is a challenging feat as they would first have to prove the feasibility of 448Gb/s PAM4 SerDes at large volumes, then implement [echo cancellation to achieve bidirectional bandwidth](https://newsletter.semianalysis.com/p/vera-rubin-extreme-co-design-an-evolution), which is in itself extremely difficult. We believe Nvidia is going for 448G uni-di only.

![](https://substackcdn.com/image/fetch/$s_!i-U0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fd34ddb8c-e8ae-4e4e-8478-62996d8775e7_1799x952.png)

Source: SemiAnalysis

Feynman could use in-rack optics, where switch blades are blind-mated to the midplane using optical connectors and thin fiber strands can be used to connect the optical connectors to the NVLink 8 Switches in place of flyover cables., but we believe this is very unlikely.

![](https://substackcdn.com/image/fetch/$s_!uIm6!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fecaed357-cd0b-4635-99c4-70bc5cf9fec9_1782x930.png)

Source: SemiAnalysis

For rack-to-rack interconnect, we explore two different topologies. The first is a two-layer CLOS network that is similar to the Oberon form factor, but with twice the bandwidth of each GPU and NVLink switch.

![](https://substackcdn.com/image/fetch/$s_!JB0C!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0cb78043-cb1d-4d66-9f72-d97c1cefe4de_1062x462.png)

Source: SemiAnalysis

The second is a reconfigurable dragonfly topology using OCS switches to connect the 8 racks. The number of OCS ports required for this topology remains tentative.

![](https://substackcdn.com/image/fetch/$s_!HR-M!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe606aa58-6349-444b-92f5-bf49c165ae4d_1141x1225.png)

Source: SemiAnalysis
