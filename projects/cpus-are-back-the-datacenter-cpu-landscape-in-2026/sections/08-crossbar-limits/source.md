As designers tried to increase core counts further, they ran into scaling limits of these early interconnects. As minimal latency and uniformity was desired, crossbar designs were used in an all-to-all fashion, where every core has a discrete link to all other cores on die. However, the number of links increased greatly with more cores, increasing complexity.

2 cores: 1 connection

4 cores: 6 connections

6 cores: 15 connections

8 cores: 28 connections

The practical limit for most designs ended at 4 cores, with higher core count processors achieved with multi-chip modules and dual-core modules that shared and L2 cache and data fabric socket between core pairs. The crossbar wiring is usually done in the metal lines above the shared L3 caches, saving area. Intel’s 6-core Dunnington in 2008 used three dual-core modules with 16MB of shared L3.

![](https://substackcdn.com/image/fetch/$s_!6t7R!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F26443b09-cd4f-4635-8189-0a85234e9709_1504x2079.png)

*AMD Opteron Istanbul 6-core die. Source: AMD*

AMD launched their 6-core Istanbul in 2009 with a 6-way crossbar and 6MB L3. Their 12-core Magny-Cours in 2010 used two 6-core dies, with the 16-core Interlagos consisting of two dies each with four Bulldozer dual-core modules.
