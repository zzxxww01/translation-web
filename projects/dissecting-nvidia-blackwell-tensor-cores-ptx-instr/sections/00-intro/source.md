### Microbenchmarking, tcgen05, 2SM MMA, UMMA, TMA, LDGSTS, UBLKCP, Speed of Light, Distributed Shared Memory, GPC Floorsweeps, SM Yield

By [Kimbo Chen](https://substack.com/@kimbobachen) and [Dylan Patel](https://substack.com/@semianalysis)

Mar 31, 2026 · Paid

Nvidia’s Datacenter Blackwell GPU (SM100) represents one of the largest GPU microarchitecture change in a generation, yet no detailed whitepaper exists. Until today, there is no public datacenter Blackwell architecture microbenchmarking study on PTX and SASS instructions, such as UMMA and TMA, with a focus on AI workloads.

After our in-depth [Nvidia Tensor Core Evolution: From Volta To Blackwell article](https://newsletter.semianalysis.com/p/nvidia-tensor-core-evolution-from-volta-to-blackwell), SemiAnalysis has spent months of engineering time, tearing into the Blackwell architecture and measuring the raw PTX instruction performance, to establish hard practical performance upper bounds and compare them with the theoretical peaks. We do this to discover unit- and instruction-level hardware throughput and latency limits, providing a useful characterization from an ML systems and kernel development perspective. We focus on deep learning workload configurations, such as benchmarking asynchronous memory copy setups used in popular deep learning library FlashInfer.

We open sourced our Blackwell micro-architecture-level benchmarking repo [here](https://github.com/SemiAnalysisAI/microbench-blackwell). Please drop a star if you find it useful.
