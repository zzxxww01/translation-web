![](https://substackcdn.com/image/fetch/$s_!S6Ri!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5ae89ead-c1e7-409c-912f-bf86d659e2c0_2880x1620.png)

*Traditional Temperature Sensor Tradeoffs. Source: Samsung, ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!2aBs!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F66a71ead-cde8-4e94-9ea5-ddf5caebf775_2880x1620.png)

*Samsung SF2 Metal Resistor-Based Temperature Sensor Tradeoffs. Source: Samsung, ISSCC 2026*

Samsung presented a compact temperature sensor on SF2, replacing the traditional bipolar junction transistor (BJT) approach with a BEOL metal resistor. This may not be as flashy as the next generation of memory or processors, but it is essential to making chips work.

The metal resistor offers 518× higher sheet resistance than an equivalent routing metal, requiring roughly 1% of the area for the same resistance. As it sits in the upper metal layers, it leaves plenty of room for any circuitry underneath and eliminates FEOL area overhead. Although it has a low resolution, the benefits more than make up for it.

![](https://substackcdn.com/image/fetch/$s_!J1CI!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F22987230-7e2a-4317-b244-f4e76930494b_2880x1620.png)

*Samsung SF2 Temperature Sensor Stacked Implementation. Source: Samsung, ISSCC 2026*

The sensor uses a fully stacked capacitor-resistor-circuit structure with a total area of just 625 μm². As a characterized PDK element, its behavior is modeled by the foundry and validated. It is more suitable for mass production, where process variation must be tightly controlled. Even on a single chip, thousands of these sensors may be used near hotspots.

As mentioned earlier, the metal resistors have a lower temperature coefficient of resistance (TCR), just 0.2× that of routing metal — which limits sensing resolution. Samsung compensates for this by increasing the base resistance. However, this slows sensing time as the RC time constant grows. To address this, Samsung uses a time-offset compression technique: a low-resistance (0.1R) fast-charge path rapidly charges the RC filter, then the circuit switches to the full resistance for the temperature-sensitive portion of the waveform.

For the time-to-digital conversion (TDC), they replaced the large linear delay generator used in prior work with a compact ring oscillator-based (RO) TDC, cutting delay generator area by 99.1%. The RO also doubles as the system clock, with phase-interleaved counting preventing non-monotonicity.

![](https://substackcdn.com/image/fetch/$s_!f54k!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F2cd264f4-0a79-4823-8ab5-1cbfd4627f9f_2880x1620.png)

*Samsung SF2 Temperature Sensor Conversion Time and Accuracy Comparisons. Source: Samsung, ISSCC 2026*

![](https://substackcdn.com/image/fetch/$s_!nCIv!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F0d4c4094-3c4e-42fc-a4d5-6087d122c98a_2880x1620.png)

*Samsung SF2 Temperature Sensor vs. Prior Work Comparison Table. Source: Samsung, ISSCC 2026*

The new temperature sensor has an accuracy figure of merit (FoM) of 0.017 nJ·%², improving upon prior work on Samsung 5LPE, TSMC N3E and Intel 4 (JSSC 2025). Prior temperature sensors could only optimize for one of these: area or speed. The sensor on N3E was small, at 900 μm² but took 1 ms, while the sensor on Samsung 5LPE was fast, at 12 μs but huge, at 6356 μm².
