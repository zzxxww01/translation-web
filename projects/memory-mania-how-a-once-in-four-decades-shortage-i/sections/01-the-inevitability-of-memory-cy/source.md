Since its commercial introduction in the 1970s, DRAM has benefited from the two scaling laws that defined the semiconductor industry: Moore’s Law and Dennard scaling. The 1T1C DRAM cell, with one access transistor and one storage capacitor, scaled for decades. Shrinking transistors reduced cost per bit, while clever capacitor engineering preserved sufficient charge to maintain signal integrity.

For much of the industry’s history, DRAM density scaled faster than logic, doubling roughly every 18 months instead of 24 months and driving dramatic cost reductions. As a commoditized product, manufacturers needed to sustain cost-per-bit declines to stay competitive. Suppliers who couldn’t compete on cost fell into a downward spiral: low sales left them short on cash to finance next-generation nodes, which in turn left them further behind on cost-per-bit. Many DRAM producers fell victim and went into bankruptcy, resulting in consolidation to just a few major players today.

For more details on the industry and DRAM basics, check out our technical deep dive:

* [The Memory Wall: Past, Present, and Future of DRAM](https://newsletter.semianalysis.com/p/the-memory-wall) - Dylan Patel, Jeff Koch, and 3 others · September 3, 2024

Yet DRAM scaling has slowed significantly over the past few decades, and density gains over time have shrunk. Over the past decade, DRAM density has increased by only ~2× in total, versus roughly ~100× per decade during the industry’s peak scaling era. Capacitors are now extreme three-dimensional structures with aspect ratios approaching 100:1, storing just tens of thousands of electrons. For comparison, a small static shock when you touch a metal doorknob might involve the transfer of billions of electrons. The static charge on just a speck of dust might be 10,000x what is stored in a modern DRAM cell.

Bitlines and sense amplifiers, once secondary concerns, are now dominant constraints. Every incremental shrink reduces signal margin, increases variability, and raises cost.

![](https://substackcdn.com/image/fetch/$s_!CvGg!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fda0878c8-fd9f-4bef-8ffc-109915c2a982_1001x558.jpeg)

Source: Micron

An easy way to understand the technical challenge in DRAM scaling is to think of a DRAM cell as a tiny bucket that holds electricity instead of water. Each bucket stores a bit of data by holding a small electrical charge. Over the years, engineers made these buckets smaller to fit more memory on a chip. At first this worked well. But today, those buckets are not just tall they are tall and narrow, each is like a tiny drinking straw standing upright. Because of the size each bucket now holds very very few electrons.

This is a problem. When the system tries to read the data, it has to detect this very faint electrical signal and distinguish it from noise. The wires that connect these cells (the “bitline”) and the tiny sensors that read them (called sense amplifiers) are now the main bottleneck. The signal is so weak that even small variations in manufacturing or temperature can cause errors.

![A graph showing a line of gold Description automatically generated with medium confidence](https://substackcdn.com/image/fetch/$s_!Lw1D!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fc9f2fca5-03aa-4d33-96d8-cdace84b33b3_1379x684.png)

Source: [SemiAnalysis Memory Model](https://semianalysis.com/memory-model/) - [Sales@SemiAnalysis.com](http://Sales@SemiAnalysis.com)

Together, these constraints explain why DRAM density has stagnated and why DRAM scaling has slowed down significantly over the years. The collapse of DRAM scaling has far-reaching consequences across cost, architecture, and industry structure.

As density gains slow, cost per bit reductions have slowed down. DRAM pricing is now more dependent on capacity additions and cyclical supply-demand dynamics rather than technology-driven cost reductions which have been a powerful deflationary force.
