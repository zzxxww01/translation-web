![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_056.png)

Source: SemiAnalysis

Broadcom was among the first companies to offer real CPO-enabled systems and as such is considered a leader in CPO. Broadcom’s first‐generation CPO device, known as Humboldt, served largely as proof of concept. Dubbed “TH4‐Humboldt”, it is a 25.6Tbit/s Ethernet switch that equally divides its total capacity between traditional electrical connections and CPO. Of that, 12.8Tbit/s is handled by four 3.2 Tbit/s optical engines, each delivering 32 lanes of 100 Gbit/s. This hybrid design of copper and optics has some prominent uses cases. In one scenario, top‐of‐rack (ToR) switches rely on electrical interfaces for short‐distance copper connections to nearby servers, while their optical ports uplink to the next tier of switching. In another scenario, at the aggregation layer, electrical ports interconnect the various switches within a rack, and optical links extend to switching tiers above or below that layer.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_057.png)

Source: Broadcom

In this design, Broadcom employed a silicon germanium (SiGe) EIC but switched to CMOS in the next generation (i.e. Bailly).

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_058.png)

Source: Broadcom

Broadcom’s second‐generation CPO device, Bailly, is a 51.2 Tbit/s Ethernet switch that—unlike its half‐optical predecessor—relies entirely on optical I/O. It consists of eight 6.4Tbit/s optical engines, each delivering 64 lanes of 100 Gbit/s. Another notable change is that instead of using a SiGe EIC, it now uses a 7nm CMOS EIC. Moving to a CMOS EIC allowed for a more complex, integrated design with additional control logic, which in turn enabled higher lane counts—scaling from the previous 32 lanes up to 64 lanes in the new optical engine.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_059.png)

Source: Broadcom

Another notable shift from the first to the second generation is the transition from a TSV process to fan‐out wafer‐level packaging (FOWLP). In this design, the EIC leverages through‐mold vias (TMVs) to route signals up to the PIC while copper pillar bumps connect it to the substrate. A major reason for adopting FOWLP is that it’s already proven in the mobile handset market and widely supported by OSATs, giving the technology greater scalability. ASE/SPIL was the OSAT partner for this FOWLP process.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_060.png)

Source: Broadcom

Broadcom revealed at Hot Chips 2024 an experimental design that integrates a 6.4 Tbit/s optical engine onto a package with one logic die, two HBM stacks, and a SerDes tile. They proposed using a fan‐out approach that places HBM on the east and west edges of the substrate, allowing room for two optical engines on the same package. By moving from CoWoS‐S to CoWoS‐L, you move to substrates that exceed 100 mm on an edge. As such, they will be able to accommodate up to four optical engines and achieve 51.2 Tbit/s of bandwidth.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_061.png)

Source: Broadcom

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_062.png)

Source: Broadcom

This year, Broadcom is launching its Tomahawk 6-based Davisson CPO switches, which incorporates sixteen 6.4T OEs. The switch ASIC is fabricated using TSMC’s N3 process node and delivers 102.4 Tbit/s of bandwidth per package. Broadcom uses contract manufacturers (CMs) such as Micas and Celestica for box assembly. Additionally, NTT Corp (Japan) is reportedly purchasing Broadcom’s TH6 bare dies and building its own CPO systems using proprietary OEs and optical solutions not sourced from Broadcom. This approach expands the potential business opportunities for TH6-based CPO systems and encourages a more open vendor ecosystem.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_063.png)

Source: SemiAnalysis

As we see greater value for CPO in scale-up fabrics, we believe the first mass-produced CPO system delivered by Broadcom will be in their customers’ AI ASICs. Broadcom’s experience with CPO makes them an attractive design partner for customers who see CPO on their ASIC roadmap in the medium term. We understand this was a key factor that led OpenAI to choose Broadcom. Interestingly, Google, Broadcom’s largest ASIC customer, is the hyperscaler that is most hesitant to deploy CPO in their datacenters. Google’s infrastructure philosophy places more emphasis on reliability over absolute performance, and CPO’s reliability is a deal breaker for them. We do not expect Google to adopt CPO any time soon.

Future generations of Broadcom CPO endpoints are also moving to the TSMC’s COUPE platform – a clear signal that the features COUPE offers provides a path to bandwidth scaling. This will not only be a change in how they package the OE, but also Broadcom’s previous generations have used edge coupling as well as MZMs – both of these choices were simpler from an implementation standpoint, but also less scalable as we discussed above. COUPE is biased towards grating coupling and MRMs which is a dramatic change from their existing approach. Despite Broadcom having the most CPO experience, this change in technical approach means that Broadcom must essentially start fresh on some aspects of their technology. The question is how much help TSMC can provide to make designing easier for Broadcom.
