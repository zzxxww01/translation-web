Once there is no longer a requirement to drive electrical signals to relatively long distances, we can escape serialized interfaces altogether by using wide interfaces that offer much better shoreline density over short distances.

One such example is with UCIe interface. UCIe-A can offer up to ~10 Tbit/s/mm of shoreline density, which is designed for advanced packages (ie. chiplets interfacing via an interposer with sub-2mm reach). On a long edge of a reticle sized chip this is up to 330 Tbit/s (41TByte/s) of off-package bandwidth. This is 660 Tbit/s of bi-directional bandwidth off of both edges. This compares to Blackwell which only has 23.6 Tbit/s of off-package BW, equivalent to around 0.4 Tbit/s/mm of shoreline density, which is a big difference.

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_029.png)

Source: SemiAnalysis

![](./Co_Packaged_Optics_(CPO)_–_Scaling_with_Light_for_the_Next_Wave_of_Interconnect_images/img_030.png)

Source: SemiAnalysis

Of course – this is not a like-for-like comparison as these off-package PHYs are needed to drive a long distance. If anything, this is the very point that is being illustrated: with CPO, reach is no longer a consideration as signals are not being driven long distances electrically. At bandwidth densities of 10 Tbit/s/mm, the bottleneck is no longer on the electrical interface but at other parts of the link, namely how much bandwidth can escape on the fibers on the other side.

Getting to this constraint is an end state very far away from today’s reality and the OE will have to share an interposer with the host. Integrating CPO on the interposer itself is even farther off on the roadmap than reliably integrating OEs on the substrate. PHY performance on the substrate is of course inferior with UCIe-S offering about 1.8Tbit/s/mm of shoreline density. This is still a significant uplift over what we believe 224G SerDes offers at ~0.4Tbit/s/mm.

However, Broadcom and Nvidia are persisting with electrical SerDes on their roadmap despite the advantages a wide interface offers. The primary reason is they believe they can still scale SerDes and that they need to design for copper especially as adoption for optics is slow. It also appears more likely that hybrid co-packaged copper and co-packaged optics solutions will be here to stay, requiring them to optimize for both. This approach is taken so as to eliminate the need for multiple tape-outs for different solutions.
