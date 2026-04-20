There are two main ways to integrate lasers into CPO.

The first approach, on-chip lasers, integrates the laser and modulator on the same photonic chip, typically by bonding III‑V (InP) materials onto silicon. While on-chip lasers simplify design and reduce insertion loss, there can be a few challenges:

1. Lasers are known to be the one of the most failure prone components within the system – failures would have a high blast radius if integrated into the CPO engine as it would take down the whole chip; 2. Lasers are also sensitive to heat, placing them on a co-packaged OE would expose a laser to high heat as it would be very close to the hottest part of the system, the host silicon, which would only exacerbate the issue; 3. On-chip lasers typically struggle to deliver high enough power output.

The one approach where the industry has come to a consensus is to use an External Light Sources (ELS). The laser is in a separate module connected to the optical engine via fiber. Often times, this laser is in a pluggable form factor like OSFP. This setup simplifies field servicing in the fairly common case of laser failures.

The downside of the ELS is higher power consumption. As seen in the diagram below, in an ELS based system, output power is lost at multiple stages due to various factors like connector losses, fiber coupling losses and modulator inefficiencies. As such, each laser in this system must provide 24.5 dBm of optical power to compensate for losses and ensure reliable transmission. High-output lasers generate more heat and degrade faster under thermal stress, with lasers and thermo-electric coolers accounting for ~70% of ELS power consumption. While incremental improvements in laser design, packaging, and optical paths help, the issue of high power requirements of lasers has not been fully solved.

At this year’s VLSI conference, Nvidia highlighted several laser partners within its ecosystem: Lumentum for single high-power DFBs, Ayar Labs for DFB arrays, Innolume for quantum-dot mode-locked combs, and Xscape, Enlightra, and Iloomina for pumped nonlinear resonant combs.

Nvidia has also discussed exploring VCSEL arrays as a potential alternative laser solution. While the per-fiber data rate would be lower and there may be some thermal issues, VCSELs may offer power and cost efficiency and can be suitable for “wide-and-slow” applications. That said, we don’t see this as an immediate priority for Nvidia.

![](https://substack-post-media.s3.amazonaws.com/public/images/355713bf-ab91-4b4a-99e7-68c4a57b9313_1024x647.png)

Source: CPO status, challenges, and solutions

Wavelength Division Multiplexing (WDM) is when multiple different wavelengths, or lambdas, of light are transmitted over the same strand of fiber. The two common variants of WDM are Coarse WDM (CWDM) and Dense WDM (DWDM). CWDM typically carries fewer channels spaced relatively far apart (typically 20 nm spacing), while DWDM packs many lanes with very tight spacing (often <1nm spacing). CWDM’s wider channel spacing limits its capacity, while DWDM’s narrower spacing can accommodate 40, 80, or even more than 100 channels. WDM is important because most implementations of CPO proposed today are limited by the number fibers that can be attached to the optical engines. Limited fiber pairs means each fiber pair must be maximized.
