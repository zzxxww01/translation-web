Beyond the redesigned fanless front chassis and the 100% liquid-cooled compute tray, the most notable point in the Vera Rubin cooling architecture discussion was Jensen’s comment on coolant/water warm temperatures and the use of chillers. For many (for Mr. Market more broadly!) the statement that Vera Rubin can operate with 45C inlet temperatures, potentially avoiding mechanical compressor-based chillers, was viewed as a major surprise for much of the cooling supplier ecosystem. We instead view this as a continuation of existing trends.

Vera Rubin will be able to operate at a 45C inlet temperature, but Blackwell is already capable of operating with inlet water temperatures above 40C (see for example Supermicro’s DLC-2 system). Major system vendors such as Lenovo and HPE have also been discussing 100% liquid-cooled architectures operating at 45C since early 2025. In 2024, HPE announced an industrial cooling system based on full liquid cooling, and similar approaches have long been used before in HPC. Lenovo discussed the next generation of its Neptune liquid solution at the 2025 OCP Summit, which is fully liquid-cooled and also uses 45C water.

![](https://substackcdn.com/image/fetch/$s_!P5WH!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9fe04678-76b1-406b-bb5a-c7822727bab0_1863x1070.png)

Source: HPE

Consider Schneider’s GB300 Reference Design 111, presented in September 2025, as another example. In this reference design, the datacenter uses a dual-loop architecture: a chilled-water loop dedicated to air cooling (feeding the fan walls) and a separate, higher-temperature loop dedicated to liquid cooling. On the liquid side, the TCS circulates coolant to the cold plates at roughly 40C and returns it at a higher temperature, while the CDU transfers that heat into the facility water loop, which can enter the CDU at approximately 37C.

![](https://substackcdn.com/image/fetch/$s_!13E2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F345a084e-4701-4993-819c-892c840fbb4d_1717x960.png)

Source: Schneider

So 45C cooling is not entirely new. Even with this capability, most operators deploying Blackwell are still designing for 20-30C water temperatures. As a rough approximation, current Blackwell inlet temperatures are around room temperature, with outlet temperatures in the 40-50C range. Only a small number of operators, such as Firmus, have removed chillers from the loop (even with systems like GB200) in favor of highly optimized economizer designs where climate permits. Avoiding the compression step in mechanical cooling can deliver meaningful energy efficiency gains.

Now, how does Nvidia cool this heat monster, given that Vera Rubin’s power consumption and heat generation is roughly double that of Blackwell? Before answering, it is worth adding another consideration. Warmer inlet temperatures, while improving energy efficiency, can make cooling more challenging as inlet temperatures approach the maximum outlet temperature (the system’s ceiling temperature) and the delta-T tightens. With less temperature differential, you need higher water/coolant flow to remove the same amount of heat. In Blackwell reference architectures, the ceiling temperature is around 65C (e.g. see the Vertiv GB200 NVL72 reference design).

![](https://substackcdn.com/image/fetch/$s_!Wxin!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8dfbf6ca-5b7c-4296-b4e3-56f41888f963_2801x1132.png)

Source: Vertiv

Although NVIDIA initially did not formally publish full specifications for Vera Rubin’s liquid cooling system, we believe the platform will support maximum coolant return temperatures up to 65C. This aligns with Nvidia’s warm-water operating envelope, and while the exact implication for delta-T depends on the chosen supply setpoint and flow control strategy, we can expect a slightly tighten delta-T. The pressure envelope is expected to be unchanged versus GB200, with maximum operating pressure of 72 psig (5 bar) and minimum burst pressure of 217 psig (15 bar), aligning with OCP’s MGX rack-level liquid-cooling specification.

![](https://substackcdn.com/image/fetch/$s_!SWCn!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F80029eec-d319-4b7a-8fa2-452e463f396e_1782x774.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

In practice, cooling follows straightforward physics. To cool a system, you must deliver sufficient water/coolant at the appropriate temperature and pressure through the loop. If you want to increase the cooling capacity of a CDU, you increase flow rate while managing pressure, which in this case implies around a 2.0-2.5x flow increase, depending on how far outlet temperatures are actually pushed by operators.

Nvidia has indicated that Vera Rubin increases liquid flow rate and achieves nearly double the thermal performance vs Blackwell, without increasing CDU pressure head or introducing additional cooling complexity or cost. Nvidia has achieved this by optimizing the entire hydraulic path. We expect larger quick disconnects to support higher flow, as well as updated manifolds and piping. As seen in the image below, vendor roadmaps suggest that, at least for the next generation of racks, 2 inch QDs should be sufficient to accommodate higher flow while staying within pressure and flow-velocity limits.

![](https://substackcdn.com/image/fetch/$s_!LwLu!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F00716966-64d3-4d63-b50d-823b873e285c_2026x1132.png)

Source: CoolIT
