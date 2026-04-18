![](https://substackcdn.com/image/fetch/$s_!Ejnk!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc7669995-eecb-4441-843f-bfaa0348e31e_2494x1403.jpeg)

*Intel UCIe-S Die-to-Die Link Die Shot and Overview. Source: Intel, ISSCC 2026*

Intel presented their UCIe-S compatible die-to-die (D2D) interface. It can reach up to 48 Gb/s/lane over 16 lanes with UCIe-S and up to 56 Gb/s/lane with a custom protocol. It works on a standard organic package for a distance of up to 30mm. Interestingly, it was manufactured on Intel’s 22nm process.

![](https://substackcdn.com/image/fetch/$s_!J1Ms!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fccbdc885-60a6-4372-b840-6e6525a06002_2494x1403.jpeg)

*Intel UCIe-S vs. Other Die-to-Die Link Comparison. Source: Intel, ISSCC 2026*

At VLSI 2025, Cadence demonstrated their own UCIe-S die-to-die interconnect on N3E. Despite the node disadvantage, Intel has managed to best Cadence’s interconnect in data rate, channel length and shoreline bandwidth, only losing out in energy efficiency.

![](https://substackcdn.com/image/fetch/$s_!NLKz!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Febe7307b-d87f-43d1-b7df-4b6cfbc8211a_2786x1606.jpeg)

*Intel Diamond Rapids Multi-Die Architecture Overview. Source: HEPiX via @InstLatX64*

The interconnect presented by Intel is likely to be a prototype of what will be used on their Diamond Rapids Xeon CPUs. Efficiency should be much better when designed on the Intel 3 process compared to this 22nm test chip and could serve to replace the advanced packaging approaches like EMIB on Granite Rapids. As we have [covered in our article on the Landscape of Datacenter CPUs](https://newsletter.semianalysis.com/i/187132686/intel-diamond-rapids-architecture-changes), Diamond Rapids consists of two IMH dies, and 4 CBB dies. With the long traces between each CBB die to both IMH dies, we believe this link is a viable candidate to connect the dies over standard package substrate, negating the need for EMIB.
