Other than getting rid of power hungry and costly DSPs and minimizing or eliminating the use of LR SerDes, the other huge benefit of adopting CPO is greater interconnect bandwidth density relative to energy consumption.

Bandwidth density measures the amount of data transferred per unit area or channel, reflecting how effectively limited space can be utilized for high-speed data transmission. Energy efficiency quantifies the energy required to transmit a unit of data.

Thus, interconnect bandwidth density relative to energy consumption is a very important figure of merit (FoM) when determining the objective quality of a given interconnect. Of course, the optimal interconnect is the one that also fits within distance and cost parameters.

When examining the chart below, a clear trend emerges: this figure of merit degrades exponentially for electrical links as distance increases. Also, moving from purely electrical interfaces to those requiring optical–electrical conversion introduces a substantial drop in efficiency—potentially by an order of magnitude. This drop is caused because it requires energy to drive signals some distance from the chip to the front-panel where the transceiver is. It requires even more energy to power optical DSPs. The figure of merit curve for CPO-based communication lies squarely above pluggables. As indicated in the chart below, CPO offers more bandwidth density per area per energy consumed over the same ranges of distance making it an objectively better interconnect.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_023.png)

Source: G Keeler, DARPA 2019, SemiAnalysis

**This chart also illustrates the adage “use copper where you can and optical when you must.”** Shorter reach communication over copper is superior when available. Nvidia embraces this mantra with their rack-scale GPU architectures architected solely for the purpose of pushing the limits of intra-rack density to maximize the number of GPUs that can be networked together over copper. This is the rationale behind the scale-up network architecture used for the [GB200 NVL72](https://semianalysis.com/2024/07/17/gb200-hardware-architecture-and-component/), and Nvidia is taking this idea even further in their [Kyber rack](https://semianalysis.com/2025/03/19/nvidia-gtc-2025-built-for-reasoning-vera-rubin-kyber-cpo-dynamo-inference-jensen-math-feynman/#kyber-rack-architecture). However – it is only a matter of time until CPO’s maturity makes accessing its part of the FoM curve viable for scale-up and worth it from a performance per TCO perspective.

* [GB200 Hardware Architecture - Component Supply Chain & BOM](https://newsletter.semianalysis.com/p/gb200-hardware-architecture-and-component) - Dylan Patel, Wega Chu, and 4 others · July 17, 2024

* [NVIDIA GTC 2025 - Built For Reasoning, Vera Rubin, Kyber, CPO, Dynamo Inference, Jensen Math, Feynman](https://newsletter.semianalysis.com/p/nvidia-gtc-2025-built-for-reasoning-vera-rubin-kyber-cpo-dynamo-inference-jensen-math-feynman) - Dylan Patel, Myron Xie, and 5 others · March 19, 2025

### Input/Output (I/O) Speedbumps and Roadblocks

While transistor densities and compute (as represented by FLOPs) have scaled well, I/O has scaled much more slowly, creating bottlenecks in overall system performance: there is only so much usable shoreline available for off-chip I/O as the data that goes off-chip needs to escape over a limited number of I/Os on the organic package substrate.

Additionally, increasing the signaling speed of each individual I/O is becoming increasingly challenging and power-intensive, further constraining data movement. This is a key reason why interconnect bandwidth has scaled so poorly over the past many decades relative to other computing trends.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_024.png)

Source: Amir Gholami

Off-package I/O density for HPC applications has plateaued due to limitations on the number of bumps in a single flip-chip BGA package. This is a constraint on scaling escape bandwidth.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_025.png)

Source: TSMC

### Electrical SerDes Scaling Bottlenecks

With limited number of I/Os, the way to realize more escape bandwidth is to push the frequency that each I/O signals at. Today, Nvidia and Broadcom are at the leading edge of SerDes IP. Nvidia shipping 224G SerDes in Blackwell which is what enables their blazing fast NVLink. Similarly, Broadcom has been sampling 224G SerDes since late 2024 in their optical DSPs. It’s no coincidence that the two companies that ship the most AI FLOPs in the industry also lead in high-speed SerDes IP. This reinforces the fundamental connection between AI performance and throughput, where maximizing data movement efficiency is just as critical as delivering raw compute power.

However, it is becoming increasingly challenging to provide higher line speeds at a desirable reach. As frequencies increase, insertion losses rise, as shown in the chart below. We see that losses increase at higher SerDes signaling speeds especially as the signal path lengthens.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_026.png)

Source: Broadcom

SerDes scaling is approaching a plateau. Higher speeds can only be sustained over very short distances without additional signal recovery components—which in turn increase complexity, cost, latency, and power consumption. It has been difficult to get to 224G SerDes.

Looking ahead to 448G SerDes, the feasibility to drive beyond just a few centimeters remains more uncertain. Nvidia is delivering 448G per electrical channel connectivity in Rubin by using a bi-directional SerDes technique. Achieving true 448G uni-directional SerDes will require further development. We may need to move to higher orders of modulation such as PAM6 or PAM8 instead of the PAM4 modulation which has been prevalent since the 56G SerDes era. Using PAM4, which encodes 2 bits per signal, to get to 448G will require a baud rate of 244Gbaud that is likely untenable due to excessive power consumption and insertion loss.

### SerDes Scaling Plateau as a Roadblock for Scaling NVLink

In the NVLink protocol, bandwidth in NVLink 5.0 has increased more than 11x compared to NVLink 1.0. However, this growth has not come from a significant increase in lane count, which has only risen slightly from 32 lanes in NVLink 1.0 to 36 lanes in NVLink 5.0. The key driver of scaling has been a 10x increase in SerDes lane speed, from 20G to 200G. In NVLink 6.0, however, Nvidia is expected to stay on 200G SerDes, meaning it will have to deliver a doubling in lane count - it delivers on this cleverly by using bi-directional SerDes to effectively double the number of lanes while using the same number of physical copper wires. Beyond this, scaling either SerDes speed and overcoming limited shoreline availability to fit more lanes lane count will become increasingly difficult and total escape bandwidth will be stuck.

Scaling escape bandwidth is critical for companies at the leading edge where throughput is a differentiator. For Nvidia, whose NVLink scale up fabric is an important moat, this roadblock could make it easier for competitors such as AMD, and the hyperscalers to catch up.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_027.png)

Source: Nvidia, SemiAnalysis

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_028.png)

Source: Nvidia, SemiAnalysis

The solution to this dilemma – or put another way the necessary compromise – is to shorten the electrical I/O as much as possible and offload data transfer to optical links as close to the host ASIC as possible to achieve higher bandwidths. This is why CPO is considered the “holy grail” of interconnect. CPO allows optical communication to happen on the ASIC package, whether via the substrate or the interposer. Electrical signals only need to travel over a few millimeters through the package substrate, or ideally an even shorter distance through a higher quality interposer, rather than tens of centimeters through lossy copper-clad laminate (CCL).

The SerDes can instead be optimized for shorter reach which needs much less circuitry than equivalent long reach SerDes. This makes it easier to design while consuming less power and silicon area. This simplification makes higher-speed SerDes easier to implement and extends the SerDes scaling roadmap. Nonetheless, we remain constrained by the traditional bandwidth model, where bandwidth density continues to scale in proportion to SerDes speed.

To achieve much higher B/W density, wide I/O PHYs are a better option over extremely short distances, offering better bandwidth density per power consumed than SerDes interfaces. Wide I/Os also come at the cost of a much more advanced package. However, in the case of CPO, this is a moot point: the packaging is already highly advanced, so integrating wide I/O PHYs adds little to no additional packaging complexity.
