Following the COVID boom that boosted internet traffic with way more Zoom calls, e-commerce and more time spent online, datacenter CPU growth was at an all-time high. In the five years leading up to ChatGPT’s launch in November 2022, Intel shipped over 100 Million Xeon Scalable CPUs to cloud and enterprise datacenters.

From then on, AI model training and inference serving would upend the CPU’s role in the datacenter, causing widespread changes in CPU deployment and design strategies. Computing AI models requires lots of matrix multiplication, an operation that can be easily parallelized and done at massive scales on GPUs which had large arrays of vector units originally used to render 3D graphics for games and visualizations.

While accelerator nodes still used host CPUs, the highly structured and relatively simple compute requirements did not take advantage of the CPU’s ability to run branchy, latency sensitive code. And with tens of vector units compared with thousands on GPUs, performance and efficiency was 100-1000x worse on CPU, especially when AI-specific GPUs added MatMul focused Tensor Cores to the mix. Despite Intel’s efforts to add more vector and matrix support with doubled AVX512 ports and dedicated AMX accelerator engines, the CPU was relegated to a support role in the datacenter. However, the internet still had to be served while power in the datacenter got prioritized to GPU compute. As a result, CPUs evolved with the times and were split into two categories.

### Head Nodes

The head node CPU’s role is to manage the attached GPUs and keep them fed with data. High per-core performance with large caches and high bandwidth memory and IO are desired to keep tail latencies as low as possible. Dedicated designs such as NVIIDA’s Grace were made with coherent memory access for GPUs to utilize CPU memory as model context Key Value Cache expansions, requiring extremely high CPU to GPU bandwidth. For head nodes, 1 CPU is usually paired with 2 or 4 GPUs in each compute node. Examples include:

* 1 Vera CPU to 2 Rubin GPUs per superchip

* 1 Venice CPU to 4 MI455X GPUs per compute tray

* 1 Graviton5 CPU to 4 Trainium3 per compute tray

* 2 x86 CPUs to 8 TPUv7 per node

### Cloud-Native Socket Consolidation

As GPUs hogged more datacenter power budgets, the need to serve the rest of the internet as efficiently as possible accelerated the development of “Cloud-Native” CPUs. The goal is maximum throughput and requests served per socket at the best efficiency (throughput per Watt). Instead of adding more, newer CPUs to boost total throughput, old, less efficient servers are decommissioned and replaced with a far smaller number of cloud-native CPUs that met the total throughput requirement while sipping a fraction of the power, lowering operating costs and freeing up power budget for more GPU compute.

![](https://substackcdn.com/image/fetch/$s_!TfPu!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fbe59d15e-c167-4a38-b904-c6f6e4efa593_2821x1421.png)

*AMD Turin Dense 7:1 Socket Consolidation. Source: AMD*

Socket consolidation ratios of 10:1 or greater can be achieved. Millions of Intel Cascade Lake servers bought during the COVID cloud spend are being retired for the latest AMD and Intel CPUs that process at the same performance level but at less than a fifth of the power.

Design wise, these Cloud-native CPUs target higher core counts with area and power efficient medium-sized cores, and have less cache and IO capabilities compared to traditional CPUs. Intel brought their Atom cores to the datacenter with Sierra Forest. AMD’s Bergamo used a more area and power efficient layout of their Zen4 core. Power efficient ARM-based designs such as AWS Graviton saw great success, while Ampere Computing targeted cloud-native compute with the Altra and AmpereOne lines.
