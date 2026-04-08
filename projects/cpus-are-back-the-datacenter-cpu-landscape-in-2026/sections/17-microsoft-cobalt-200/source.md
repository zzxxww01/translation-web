![](https://substackcdn.com/image/fetch/$s_!VLAl!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F9634fe8d-37d6-4a92-87a5-1b371d9a6a4f_1920x1080.png)

*Microsoft Cobalt 200 Server. Source: Microsoft*

![](https://substackcdn.com/image/fetch/$s_!nG1L!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F80839a8f-c1e0-44fe-ab4e-310b4427ccd1_2608x1427.png)

*Cobalt 200 SoC Layout. Source: Microsoft*

* [Microsoft Infrastructure - AI & CPU Custom Silicon Maia 100, Athena, Cobalt 100](https://newsletter.semianalysis.com/p/microsoft-infrastructure-ai-and-cpu) - Dylan Patel and Myron Xie · November 15, 2023

Following on from Microsoft’s first Cobalt 100 CPU in 2023 which we covered above, Cobalt 200 was launched in late 2025 with several upgrades. While core count did not increase much, going from 128 to 132, each core is now much more powerful with the Neoverse V3 design compared to the Neoverse N2 in the prior generation. Each core has a very large 3MB L2 cache, and are connected with the standard ARM Neoverse CMN S3 mesh network across two TSMC 3nm compute dies with a custom high-bandwidth interconnect between dies. From the diagram, each die has an 8x8 mesh with 6 DDR5 channels and 64 lanes of PCIe6 lanes with CXL support. 2 cores share each mesh stop, totaling 72 cores printed on each die with 66 enabled for yield. 192MB of shared L3 cache is also spread across the mesh. With these upgrades, Cobalt 200 achieves a 50% speedup over Cobalt 100.

Unlike Graviton5, Cobalt 200 will only be featured in Azure’s general purpose CPU compute services and will not be used as AI head nodes. Microsoft’s Maia 200 rackscale system deploys Intel’s Granite Rapids CPUs instead.
