VR NVL72 takes liquid cooling to the next level. The VR NVL72 compute tray is 100% liquid cooled, whereas GB200 and GB300 compute trays adopt a hybrid of 85% liquid cooling and 15% air cooling. As a result of this, fans are removed from the compute tray and the cold plate coverage increases to remove heat from the front half of the chassis. An internal manifold will be placed in the middle of the chassis to distribute inlet coolant to the various modules and to collect the outlet coolant. Each of the modules within the compute tray will have a cold plate module attached. Each cold plate module connects to the internal manifolds via MQD (a smaller form factor quick disconnect specification standard by Nvidia for compact area application within the compute tray).

![](https://substackcdn.com/image/fetch/$s_!Ra3T!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2397b285-cb78-4081-8813-51a223db97bb_1354x2343.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

The coolant enters the compute tray via UQD from the left rear side of the chassis. Then, the coolant enters the internal manifold via a tube, where the coolant is distributed to all the modules. The coolant collects the heat from the different modules and re-enters the internal manifold. Finally, the coolant exits the compute tray via UQD at the rear right side of the chassis.

![](https://substackcdn.com/image/fetch/$s_!DhHR!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fce22913e-61af-49e3-9487-fad91f7a8af7_2012x722.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

Several upgrades are also made on the cold plate for VR NVL72. For each Strata module, the cold plate will be provided as a single module covering the entire Strata board including two Rubin GPUs, one Vera CPU, SOCAMM modules, and the various VRM components. The cold plate of the Rubin GPU is upgraded to a “micro-channel cold plate” (MCCP). Essentially, the pitch between the channels in the cold plate is reduced to to 100 micron from 150 micron. This increases the surface area and increases the thermal dissipation capacity of the cold plate. Also, there will be a layer of gold plated on the surface contacting the Rubin GPU. The reason for this is to prevent corrosion of the copper from the liquid metal Indium TIM2.

![](https://substackcdn.com/image/fetch/$s_!P-4a!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F78fa8a53-ba67-4917-96be-3d5da6051095_1876x584.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

Beyond the Strata module, the modules at the front of the Chassis will also have a cold plate module attached. Each Orchid module will have a cold plate module covering the CX-9, the E1.S SSD, the transceiver cages and the various VRMs. The cold plate and the board will be less than 0.5U tall as two Orchid modules are stacked on top of each other in a 1U chassis. Each pair of Orchid modules shares only a pair of QD from the manifold. There will be another set of manifolds that distribute the coolant to the top and the bottom cold plates for the pair of Orchid modules. In our [VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/) we have the content for all the various thermal components including the cold plate modules, manifolds, and the Quick Disconnects.

![](https://substackcdn.com/image/fetch/$s_!Z-zU!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F8e1b96be-6742-4679-8180-275aaad0521d_3164x999.png)

Source: [Nvidia VR NVL72 Component BoM and Power Budget Model](https://semianalysis.com/vr-nvl72-model/)

Previously, cold plates were assembled at the L10 assembly level where the various components are put into place in the chassis. Given the modular approach, the cold plates need to be more tightly integrated with the module itself. Hence, the cold plate will be attached at the L6 assembly level right after the PCBA process. This increases the assembly efficiency as the assembly at L10 is simplified to slotting in the completed modules into the corresponding connectors and quick disconnects.
