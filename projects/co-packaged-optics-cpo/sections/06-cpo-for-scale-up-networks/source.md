On the contrary, we see CPO for scale-up as the killer application. As mentioned earlier, major hyperscalers are already making commitments to suppliers for deployment of CPO-based scale-up solutions by the end of the decade.

Currently, the incumbent copper-based scale up paradigm is being pushed to its limits due to the limited reach of copper cables – two meters at best when running at 200Gbit/s per lane, as well as the increasing difficulty of doubling bandwidth per lane. CPO can solve these problems as it can meet bandwidth density requirements, provide multiple vectors for scaling bandwidth well into the future as well as unlock much larger scale up world sizes.

Once CPO is deployed for scale-up networking, the scale-up domain will no longer be limited by the interconnect reach. In principle, customers would be able to grow scale-up domains to arbitrarily large sizes. Of course, if one wants to keep the scale-up domain within a single-tier fan-out network that allows for all-to-all connections, the scale-up domain size would become limited by the switch radix.

### Scale-out vs Scale-up TAM

Networking requirements of the scale up fabric are far more demanding than that of the back-end scale-out network. The GPU to GPU or switch links require much higher bandwidth and lower latency to enable the GPUs to be interconnected so that they can coherently share resources such as memory.

To illustrate, 5th generation NVLink on Nvidia Blackwell offers 900GByte/s (7,200 Gbit/s) of uni-directional bandwidth per GPU. That is 9x more bandwidth per GPU than the 100GByte/s (800Gbit/s) per GPU on the back-end scale out network (using the CX-8 NIC for the GB300 NVL72). This also creates the need for much higher shoreline bandwidth density from the host which has been the impetus for pushing GPU SerDes line speeds forward.

It is also important to realize that as the size of scale-up domains increases and as the speed of scale-up interconnect grows as well, the TAM of scale-up interconnect (and eventually, scale-up CPO) has already considerably dwarfed that of scale-out networking. CPO TAM is likely to be dominated by scale-up rather than scale-out networking applications.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_009.png)

Source: SemiAnalysis

### Copper vs Optics for Scale-Up: World Sizes, Density and Reach

Currently, scale up networks run entirely on copper for good reasons. Matching NVLink bandwidth with optical transceivers in the current pluggable paradigm would be prohibitively expensive in terms of cost and power as well as introducing unwanted latency. There also might not be sufficient face-plate space on the compute tray to even fit all of these transceivers. Copper excels at these low-latency, high-throughput connections. However, as mentioned above, copper’s limited reach restricts the “world size”—the number of GPUs that can be connected within a single scale-up domain.

Increasing scale-up world size is a vitally important avenue of compute scaling. Adding more compute, memory capacity, and memory bandwidth in a single scale up domain has become increasingly critical in today’s regime of inference-based model scaling and test time compute.

Nvidia’s GB200 system offered an immense performance boost because it brought the world size to 72 interconnected GPUs in an all-to-all topology from just 8 interconnected GPUs. The result was unlocking tremendous throughput gains through implementing more sophisticated collective communication techniques that are not feasible on the scale out network.

On copper, this could only be done within the footprint of a single rack creating immense demands on power delivery, thermal management and manufacturability. The complexity of this system has the downstream supply chain still struggling to ramp up capacity.

Nvidia will continue to persist with copper. They also need to push their scale up world size even higher to keep ahead of competitors such as AMD and the hyperscalers who are catching up with their own scale up networks. As such, Nvidia is forced to go to drastic lengths to expand the scale up domain within a single rack. Nvidia’s extreme Kyber rack architecture for Rubin Ultra that was shown at GTC 2025 can scale up to 144 GPU packages (576 GPU dies). This rack is 4x denser than the already dense GB200/300 NVL72 rack. With the GB200 already being so complicated to manufacture and deploy, Kyber takes it to the next level.

Optics enables the opposite approach, scaling across multiple racks to increase world size, rather than packing more accelerators in a dense footprint which is challenging for power delivery and thermal density. This is possible with pluggable transceivers today, but again the costs of optical transceivers along with their high power consumption makes this impractical.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_010.png)

Source: SemiAnalysis

### Copper vs Optics for Scale-Up: Scaling Bandwidth

Scaling bandwidth on copper is also increasingly difficult. With Rubin, Nvidia is achieving the doubling of bandwidth by implementing a novel bi-directional SerDes technology, where both transmit and receive operations share the same channel, enabling full-duplex communication at 224Gbit/s transmit + 224Gbit/s receive per channel. Achieving “true” 448G per lane on copper remains another challenging feat with an uncertain time to market. In contrast, CPO presents multiple vectors for scaling bandwidth: Baud rate, DWDM, Additional Fiber Pairs and Modulation – all of which will be discussed in detail later in this article.
