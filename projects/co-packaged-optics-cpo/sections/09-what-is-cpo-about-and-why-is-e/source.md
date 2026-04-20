**CPO** integrates optical engines directly within the same package or module as high-performance computing or networking ASICs. These optical engines convert electrical signals into optical signals, enabling high-speed data transmission over optical links. Optical links must be used for data communication over distances beyond a few meters, as high-speed electrical communication over copper cannot reach beyond a few meters.

Today, most electrical to optical conversion occurs via pluggable optical transceivers. In such cases, an electrical signal will travel tens of centimeters or more from a switch or processing chip through a PCB to a physical transceiver cage at the front plate or back plate of the chassis. The pluggable optical transceiver resides in that cage. The transceiver receives the electrical signal which is reconditioned by an optical Digital Signal Processor (“DSP”) chip and then sent to the optical engine components which convert the electrical signal to an optical signal. The optical signal can then be transmitted through optical fibers to the other side of the link where another transceiver undergoes this process in reverse to turn the optical signal into an electrical signal all the way back to the destination silicon.

In this process, the electrical signal traverses over a relatively long distances (for copper at least) with multiple transition points before getting to the optical link. This causes the electrical signal to deteriorate and requires a lot of power and complicated circuitry (the SerDes) to drive and recover it. To improve this, we need to shorten the distance the electrical signal needs to travel. This brings us to the idea of “**co-packaged optics**” where the optical engine that was found in a pluggable transceiver is instead co-packaged with the host chip. This reduces the electrical trace length from tens of centimeters to tens of mm because the optical engine is much closer to the XPU or Switch ASIC. This significantly reduces power consumption, enhances bandwidth density, and lowers latency by minimizing electrical interconnect distances and mitigating signal integrity challenges.

The schematic below illustrates a CPO implementation, where there is an optical engine that resides on the same package as the compute or switch chip. Optical engines will initially be on the substrate, with OEs placed on the interposer in the future.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_014.png)

Source: SemiAnalysis

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_015.png)

Source: SemiAnalysis

Today, the front pluggable optics solution, as illustrated in the diagram below, is ubiquitous. The main takeaway from this diagram is to illustrate that the electrical signal needs to traverse a long distance (15-30cm) across a copper trace or flyover cable before it gets to the optical engine in the transceiver. As discussed above, this also necessitates the need for long-reach (LR) SerDes to drive to the pluggable module.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_016.png)

Source: SemiAnalysis

Additionally, there are intermediate implementations that fall between CPO and traditional front-pluggable optics, such as Near-packaged optics (NPO) and On-Board optics (OBO).

In recent years, NPO has emerged as an intermediate step toward CPO. NPO has multiple definitions. NPO is where the OE doesn’t sit directly on the ASIC’s substrate, but is co-packaged onto another substrate. The optical engine remains socketable and it can be detached from the substrate. An electrical signal will still travel from a SerDes on the XPU package through some copper channel to the Optical Engine.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_017.png)

Source: SemiAnalysis

There is also On-Board Optics (OBO), which integrates the optical engine onto the system PCB inside the chassis, positioning it closer to the host ASIC. However, OBO inherits many of the challenges of CPO, while delivering fewer benefits in terms of bandwidth density and power savings. We view OBO as the “worst of both worlds” because it combines the complexity of CPO while inheriting some of the limitations of front-pluggable optics.

![](https://substack-post-media.s3.amazonaws.com/public/images/faa2a72c-e270-4e1f-a13f-a0fe827c9b66_1024x276.png)

Source: SemiAnalysis
