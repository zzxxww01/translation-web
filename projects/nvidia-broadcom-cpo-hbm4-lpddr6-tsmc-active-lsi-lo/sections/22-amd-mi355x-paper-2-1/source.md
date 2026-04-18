![](https://substackcdn.com/image/fetch/$s_!o-hR!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F62444551-a7bc-4619-ae99-74199208f209_2880x1620.jpeg)

*AMD MI300X vs. MI355X XCD Comparison. Source: AMD, ISSCC 2026*

AMD presented on their MI355X GPUs. In conference presentations, AMD usually rehashes prior announcements while only introducing one or two new pieces of information. This paper was much better in that regard, explaining how the MI355X XCD and IOD were improved as compared to the MI300X.

![](https://substackcdn.com/image/fetch/$s_!zxX3!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb0f76dac-c592-4dd4-ab6d-0d1054fc2f8b_2880x1620.jpeg)

*AMD MI300X vs. MI355X XCD Area Efficiency. Source: AMD, ISSCC 2026*

AMD detailed how they doubled the matrix throughput per CU while keeping the total area the same and the number of CUs largely similar. First, of course, was the move from N5 to N3P; this provided the bulk of the transistor density improvement. The additional two metal layers provided by N3P allowed for improved routing and thus, higher cell utilization. AMD designed their own standard cells, as they have with N5 before, to optimize the node for their HPC use case.

They also used denser placement algorithms, similar to how the Zen 4c cores used in EPYC Bergamo CPUs are much smaller than the Zen 4 cores used in EPYC Genoa CPUs.

There are two approaches when performing the same calculations with many different data formats like FP16, FP8, MXFP4, etc. The first is using shared hardware, where every format goes through the same circuits. However, this comes with a power cost as there is little optimization for each format. The second option is each data format using an entirely different set of circuits for calculations. However, this takes up a lot of additional space. Of course, the optimal approach is somewhere in the middle. This optimization was an important focus for AMD.

![](https://substackcdn.com/image/fetch/$s_!tuPF!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2c313972-5315-4d1e-aa02-be6f1ffad996_2880x1620.jpeg)

*AMD MI355X XCD Frequency and Power Efficiency Gains. Source: AMD, ISSCC 2026*

As the next node with improved transistors, N3P provides performance improvements by itself. Nevertheless, AMD was able to improve frequency iso-power by 5% before process node improvements. They also designed multiple flip-flop variants with varying power and performance characteristics deployed across different areas of the chip depending on usage and architectural requirements.

![](https://substackcdn.com/image/fetch/$s_!Yxoy!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8b8604cb-0c0d-404c-942a-7b8fe000edd8_2880x1620.jpeg)

*AMD MI355X IOD Merging Power Efficiency. Source: AMD, ISSCC 2026*

MI300X featured 4 IO Dies. MI355X cuts that down to two. By doing this, AMD saves area on die-to-die interconnects. A larger monolithic die improves latency and reduces SerDes and translations. Moreover, the efficiency of the HBM was also improved by increasing the interconnect width. The saved power could be reallocated to the compute dies to increase performance.

![](https://substackcdn.com/image/fetch/$s_!rkb_!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Faee3a34c-c53c-4661-ac14-8907a7764064_2880x1620.jpeg)

*AMD MI355X IOD Interconnect Power Optimization. Source: AMD, ISSCC 2026*

As a large die with many routing options between any two areas on the chip, AMD had to do a lot of work to optimize the wires and interconnects. Through custom engineering of the wires, AMD was able to reduce the interconnect power consumption by ~20%.
