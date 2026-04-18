![](https://substackcdn.com/image/fetch/$s_!2aNW!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7d6415fa-2e4a-4565-af88-6db7a3c95dbc_1309x1267.jpeg)

*Microsoft D2D Test Vehicle Layout and Routing. Source: Microsoft, ISSCC 2026*

Microsoft also detailed their die-to-die (D2D) interconnect. Their test vehicle includes two dies and two pairs of D2D nodes for interconnection. A full mock-up of the power delivery network and routing were included to mimic clock gating and crosstalk.

![](https://substackcdn.com/image/fetch/$s_!3kjp!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1bc8b78e-9738-4558-a155-efbddcf0dbbe_472x677.jpeg)

*Microsoft D2D Interconnect Die Shot. Source: Microsoft, ISSCC 2026*

The interconnect on their test die occupied 532 µm of shoreline and had a depth of 1350 µm. The test vehicle was fabricated on TSMC’s N3P node, and the interconnect was tested at two data rates, 20 Gb/s at 0.65V, and 24 Gb/s at 0.75V.

![](https://substackcdn.com/image/fetch/$s_!i2ue!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fffed7179-ed8f-414b-8aeb-2ff273f25784_2880x1620.jpeg)

*Microsoft D2D Power Consumption Breakdown. Source: Microsoft, ISSCC 2026*

Microsoft reported two power consumption figures, one with both analog and digital system power, and one with only analog power. The latter is what most die-to-die interconnects report. At 24 Gb/s, the system power is 0.33 pJ/b and the analog power is 0.226 pJ/b, while at 20 Gb/s, the system power is 0.25 pJ/b and the analog power is 0.17 pJ/b. The power at idle state is 0.05 pJ/b.

![](https://substackcdn.com/image/fetch/$s_!qn-K!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F65fefab9-0819-4c73-8c7b-39b778230934_2880x1620.jpeg)

*Microsoft D2D vs. Other Die-to-Die Interconnects. Source: Microsoft, ISSCC 2026*

Microsoft also compared their interconnect to the same prior research as TSMC did for their Active LSI.

As we [explained in a previous article](https://newsletter.semianalysis.com/i/187132686/microsoft-cobalt-200), Microsoft’s Cobalt 200 CPU features two compute chiplets connected by a custom high-bandwidth interconnect. We believe that this presentation details that exact interconnect.
