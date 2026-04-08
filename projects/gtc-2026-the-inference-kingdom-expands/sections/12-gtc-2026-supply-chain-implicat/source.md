Here, we will discuss our findings on where we see there are big changes in content for the supply chain coming out of all these announcements at GTC.

#### AlphaWave 112G Serdes in LP30

It may surprise readers that Qualcomm has IP in the Groq LPU 3 chip! More specifically it is AlphaWave, which Qualcomm acquired last year, that is providing the 112G SerDes for Groq’s C2C. AlphaWave was selected as the only IP provider that has high speed SerDes for Samsung Foundry. It was AlphaWave’s SerDes that caused issues for Groq LPU 2. Alphawave will continue to be used for the LP35, but Nvidia will of course use their own NVLink SerDes IP from LP40 when it transitions back to TSMC.

#### LPX PCB

Next, we mentioned that a very high spec PCB is required for the LPX compute tray. We estimate that each compute tray main board PCB will carry $7k ASP. The suppliers for this are Victory Giant and WUS. Of course, there are several other PCB modules in the compute tray, but they do not need a high spec. Nvidia is continuing with their cable-less philosophy similar to the Vera Rubin compute tray which requires a lot of board-to-board connectors, which brings us to the next big beneficiary.

#### Cables and Connectors: Amphenol Continues to Benefit

For the LPX, Amphenol will be a beneficiary for all the connectors for the backplane. Each LPX node requires 16 80DP Paladin connectors for the backplane. There are also board to board connectors required to connect all the various modules within the tray: the main LPU board with the host CPU module and the OSFP/QSFP modules that sit below the CPU module, the front-end NIC module, and the management module. Amphenol will supply the cable backplane too which is 8,160 DP per rack.

#### NVL288 System

For the Vera Rubin Ultra NVL288 System that we discussed above, we would say the cable backplane return for Kyber. If Rubin Ultra is deployed in such a form factor – each of the Rubin Ultra GPUs will have a scale-up bandwidth of 14.4Tbit/s uni-di, requiring 144 DPs of cables to connect to the NVSwitches. 144 DPs times 288 GPUs means a total of 41,472 DPs to connect this larger world size domain. This is a lot of cables, so it is more of an upper bound of how much cable content could be used here. If there is oversubscription or if the inter-rack connection is made through the switches – it is possible fewer DPs would be needed.

#### FIT Joining the Party

Backplane cable cartridge and Paladin connector demand is so strong that Amphenol cannot keep up with supply. Amphenol has now completed licensing of the VR NVL72 backplane cable cartridge as well as Paladin HD connectors to FIT, who can now manufacture these components. This has been in the works for a long time but is finally settled. Amphenol will earn licensing fees from FIT’s sales of these licensed components.

#### Kyber Voronoi – Another FIT Win?

The Kyber midplane will utilize many 8×19 DP connectors to interface with the compute trays at the front of the rack, and to the switch blades in the back of the rack.

For Kyber, Nvidia is now in the driver’s seat when it comes to IP and they have designed a proprietary connector spec named Voronoi, so it will no longer be the Amphenol Paladin connector. There are three vendors bidding for the project: FIT, Molex and Amphenol. FIT appears to be leading the market for these connectors, but Amphenol is reportedly also working together closely with FIT to manufacture the connectors. The design and implementation of Voronoi remains in flux, but both FIT and Amphenol will need to ramp significant production volume with the specification licensed from Nvidia.

The midplane, switch tray and compute tray all feature female side connectors which will require the use of a spring-loaded male part that protect the pins and interface between both sides. The density of these connectors will ultimately be much higher than Amphenol’s Paladin connectors.

More is available to our institutional subscribers sales@semianalysis.com.

#### Mid-board Optics – Nvidia’s War on Pluggables

Interestingly, the Kyber rack exhibited at the GTC 2026 show floor is missing OSFP cages for scale-out networking. Instead, we only see 4x MPO ports from each compute tray. This design has effectively taken key pluggable transceiver items (driver, TIA, etc.) other than the DSP and put them on a Midboard Optical Module (MBOM) which then connects to the PCB via a land grid array (LGA) socket. Two CX-9s share one MBOM, which then connects to the MPO faceplate via a short fiber connection. The MBOM provides two MPO ports at 2x800G each for 1.6T of total connectivity.

![](https://substackcdn.com/image/fetch/$s_!RazY!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F3445fbb8-93c3-458e-8937-a67192ef8276_4000x3000.jpeg)

*4 MPO ports on the left, rather than OSFP cages. Source: Nvidia, SemiAnalysis*

The use of MBOM would block the use of any form of pluggable transceiver or AEC, and naturally hyperscalers are saying “CP-Hell No” to that idea and are continuing to push for an OSFP cage so they can continue using pluggables.

It is important to point out that many aspects of the Kyber design are still in flux and there could still be a number of design changes before Kyber racks are actually deployed. After all – the change from the four canister design to a two compute tray canister + one switch blade bank is already a huge change.
