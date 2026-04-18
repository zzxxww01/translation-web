![](https://substackcdn.com/image/fetch/$s_!02R2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F75df5c4b-d65e-4d6e-ad17-46db43d1c124_2880x1620.jpeg)

*SK Hynix 1c GDDR7 Specifications and Die Shot. Source: SK Hynix, ISSCC 2026*

While the LPDDR6 is a generational leap with new memory technology, SK Hynix’s GDDR7 on their 1c process shows an even greater improvement, clocking up to 48 Gb/s at 1.2V/1.2V. Even at only 1.05V/0.9V, it can clock up to 30.3 Gb/s, higher than the 30 Gb/s memory in the RTX 5080.

![](https://substackcdn.com/image/fetch/$s_!M7-j!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb54fd8fd-325c-495b-bd98-4187c051138b_2880x1620.jpeg)

*Samsung 1z GDDR7 Shmoo Plot and Die Shot. Source: Samsung, ISSCC 2024*

![](https://substackcdn.com/image/fetch/$s_!zcG2!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F5fcf00cd-4001-4a32-8220-0846b9baa526_2880x1620.jpeg)

*Samsung 1b GDDR7 Specifications and Die Shot. Source: Samsung, ISSCC 2025*

The bit density achieved is 0.412 Gb/mm², compared to 0.309 Gb/mm² on Samsung’s 1b process, and 0.192 Gb/mm² on Samsung’s older 1z process.

![](https://substackcdn.com/image/fetch/$s_!tQdH!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fa8119950-b6d0-424a-af28-90305882aae1_1731x703.png)

*LPDDR5X vs. GDDR7 Density Comparison Across Vendors. Source: SemiAnalysis*

GDDR7 has lower bit density than LPDDR5X, usually around 70% of the latter. Although it has much higher data rates, this comes at a cost, both in terms of power and area.

GDDR7’s lower density is a result of the significantly higher periphery area for high access speeds. The actual memory arrays thus make up a smaller percentage of die area. This more complex logic control circuit is required for the PAM3 and QDR (4 symbols per clock cycle) signaling used in GDDR7.

GDDR7 is mainly used in gaming GPU applications that require high memory bandwidth at lower cost and capacity compared to HBM. NVIDIA had announced the Rubin CPX large-context AI processor in 2025 with 128GB of GDDR7, but this has all but vanished from the 2026 roadmaps as NVIDIA focuses on rolling out their Groq LPX solutions instead.

We have [detailed wafer volumes, yields, density, COGS, and more in our memory model for HBM, DDR, and LPDDR across various nodes](https://semianalysis.com/memory-model/).
