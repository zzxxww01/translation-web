![](https://substackcdn.com/image/fetch/$s_!iUhJ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F05f65e22-af68-4a66-8471-20eb13de627b_3005x1594.png)

*Axion C4A Wafer and Package. Source: Hajime Oguri, Google Cloud Next ’24*

![](https://substackcdn.com/image/fetch/$s_!8nFB!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F7cca6b00-0503-42dd-b09d-15a595e864d9_1844x1814.png)

*Axion N4A CPU. Source: Google*

Announced in 2024 and generally available in 2025, The Axion line signaled Google’s entry into custom silicon CPUs for their GCP cloud services. Axion C4A instances have up to 72 Neoverse V2 cores on a standard mesh network, with 8 channels of DDR5 and PCIe5 connectivity on a large monolithic 5nm die. Based on close-up images of the Axion wafer presented at Google Cloud Next 2024, the die appears to have 81 cores printed in a 9x9 mesh, leaving room for 9 cores to be disabled for yield. Therefore, we believe a new 3nm die was designed for the 96-core C4A bare metal instances that went into preview late in 2025.

For more cost-effective scale-out web and microservices, Google’s Axion N4A instances are now in preview, coming with 64 lower performance Neoverse N3 cores on a much smaller die, allowing significant volume ramps through 2026. The Axion N4A silicon is a full custom design made by Google on TSMC’s 3nm process. As Google transitions their internal infrastructure over to ARM, Gmail, YouTube, Google Play and other services will run on Axion alongside x86. In the future, Google will design Axion CPUs for use as head nodes in their TPU clusters powering Gemini.
