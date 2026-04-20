So, if CPO is the solution, why is Nvidia not pursuing it for Rubin Ultra and only for their scale out switches at first? This goes back to supply chain immaturity, manufacturing challenges, and customer hesitation around deployment. The Quantum and Spectrum CPO switches have been introduced to help ramp up the supply chain and get more real world data on reliability and serviceability in the datacenter.

**In the interim, Meta’s CPO reliability data published around ECOC provides some helpful information.** Meta collaborated with Broadcom for this study, with Broadcom [publishing some useful slides](https://www.ecocexhibition.com/wp-content/uploads/Tues-1300-R.Pancholy-R1.1.pdf) as well. In this study, Meta carried out a reasonably sized test run spanning up to 1,049k 400G port device hours across 15 Bailly 51.2T CPO Switches and published the maximum non-zero KP4 forward error correction (FEC) bin:

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_011.png)

Source: Meta

The paper also explained how during the test period, there were no failures or uncorrectable codewords (UCWs) observed in the links, citing only one instance of FEC bin > 10 being observed across the entire testing period up to 1,049k 400G port device hours.

Meta did not stop there, however. In the talk at ECOC presenting the same paper, they presented expanded results for up to 15M 400G port-device hours. These results showed that there were no UCWs for the first 4M 400G port device hours, and they also showed a 0.5-1M device hour mean time before failure (MTBF) for 400G 2xFR4 transceivers (550k for 2xFR4 globally) vs 2.6M device hour MTBF for CPO.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_012.jpeg)

Source: Meta

While 15M port device hours might sound like a large number, this is in units of 400G port hours. So – one 51.2T switch operated for one hour would mean 128 400G port hours. 15M 400G Port hours across 15 51.2T switches would mean 7,812 wall-clock hours or about 325 days. Indeed, this 15M hour number is often cited as simply “hours” or “device hours” with the “port” part left out. While the zero failure and zero UCW statistic up to 4M port device hours is very helpful – the industry needs far more than just 15 CPO switches tested for 11 months in a lab setting before it pivots towards CPO scale-out switching and commits billions of dollars to this technology.

Operating thousands of scale-out switches in a dynamic field environment is entirely different challenge and it remains to be seen how these switches will perform in a production environment. Temperature variation could be higher in a production environment vs a lab, leading to unanticipated variation in component performance or endurance. [Meta’s own Llama 3 paper cited 1-2% temperature variations in the datacenter](https://arxiv.org/pdf/2407.21783) adversely affecting power consumption fluctuations – could such fluctuations affect an entire network fabric in ways that are hard to anticipate?

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_013.png)

Source: [Meta](https://arxiv.org/pdf/2407.21783)

Even mundane sounding problems like dust in a datacenter are the bane of support technicians who can spend considerable time cleaning fiber ends – of course, CPO switches have either an LC or MPO type front pluggable connector, but what about dust inside of the CPO switch chassis? The 0.06% unserviceable failure rate sounds attractive, but such failures have a blast radius of 64 800G ports. This paper is also focused on FR optics based CPO switches, though the next generation of CPO switches will be based on DR optics. These are just a few known unknowns, and there are potentially more unknown unknowns that could come up in field testing.

Indeed, these results have been impactful in terms of convincing those in the industry by delivering tangible reliability data. Our point here is not to create fear, uncertainty or doubt (FUD) but rather to call for even larger scale field testing so that the industry can quickly understand and solve unforeseen problems thereby paving the way for broader CPO adoption, particularly for scale-up networking.

At the end of the day, Nvidia’s scale-out CPO product launch is serving as a practice run and pipe-cleaner for the real high-volume deployment. We think deployment will be far more sizable and impactful for scale up given the much more compelling TCO and Performance/TCO benefit for scale-up vs scale-out.

Moreover - when it comes to scale-out CPO, Rubin Ultra is targeting a launch in 2027 (we think that ends up being late 2027) and the supply chain won’t be ready to ship tens of millions of these CPO endpoints to support GPU demand. Even this timeline is too ambitious for Nvidia. This is why the Feynman generation appears to be the focal point for CPO injection into the Nvidia ecosystem.

Now let’s talk in depth about what CPO is about, the technical considerations, challenges, and state of the ecosystem today.
