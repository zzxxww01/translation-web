To appreciate the design changes and philosophies of the 2026 CPUs, we have to understand how multi-core CPUs work and the evolution of interconnects as core counts grew. With multiple cores comes the need to connect those cores together. Early dual-core designs such as Intel’s Pentium D and Xeon Paxville in 2005 simply consisted of two independent single cores, with core-to-core communication done off-package via the Front Side Bus (FSB) to a Northbridge chip that also housed the memory controllers. AMD’s Athlon 64 X2, also in 2005, could be considered a true dual-core processor with two cores and an integrated memory controller (IMC) on the same die, allowing the cores to communicate with each other and to memory and IO controllers directly within the silicon through on-die NoC (Network on Chip) data fabrics.

![](https://substackcdn.com/image/fetch/$s_!BLWt!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3fc1fbd3-39c1-4650-ab74-54f841f233fc_2329x1801.png)

*Intel Tulsa Die Shot. Source: Intel, Hot Chips 2006*

Intel’s subsequent Tulsa generation included 16MB of L3 cache shared between the two cores and functions as an on-die core to core data fabric. As we will see later, these on-die data fabrics will become a crucial factor in datacenter CPU design as core counts grow in the hundreds.
