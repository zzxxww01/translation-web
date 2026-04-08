Speculative decoding reduces the cost of autoregressive generation by using a small, inexpensive draft model to propose several tokens ahead. The large model then checks the proposed tokens in a single forward pass that resembles a prefill computation. For a given input sequence length, a single forward pass can take roughly the same time when the input has N more tokens. Speculative decoding uses this property to run inference on a smaller model to draft multiple tokens for the main model to verify with a single forward pass, producing at most N additional tokens in a similar time budget.

![](https://substackcdn.com/image/fetch/$s_!V6f0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fb2b2aa12-c308-4f4b-84f7-969228600ce5_2296x1126.png)

Source: [Brendan Bycroft](https://bbycroft.net/llm)

This assumption regarding additional token production with the same time budget is strongest for dense models because batched verification can reuse the same weight stream across multiple positions. For Mixture-of-Experts models, different tokens may route to different experts, so verifying multiple draft tokens can activate more experts than single-token decoding and force additional expert weights to be fetched from memory. As shown in the Mixtral 8x7B Instruct model results in the EAGLE paper, this extra memory traffic erodes bandwidth savings and can make verification notably comparable to a standard decoding step.

Multi-token prediction pursues similar benefits without requiring a separate draft model. Auxiliary prediction heads are added to the model architecture, so a single model can propose several future tokens from the same underlying representation. This improves distribution alignment because the proposals come from the same model that ultimately scores them. Multi-token prediction also avoids the operational complexity of serving an additional model while still enabling multi-token generation strategies but requires the MTP heads to be pretrained alongside the main model.

![](https://substackcdn.com/image/fetch/$s_!KL8_!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F27ee5a46-78b5-40dd-b76d-1f096e0ae06d_1755x1154.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Across all SKUs, enabling MTP results in performance gains. By making use of the typically unused logits to verify the extra tokens, minimal compute overhead is added, saving extra expensive weight loads during decode.

![](https://substackcdn.com/image/fetch/$s_!HkQ0!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Ffb5fc8fa-d129-475c-bb87-664e08bc6179_1773x1151.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

At large batch sizes, the inference regime is less memory-bandwidth bound compared to for low batch sizes. Since speculative decoding (including MTP) works by trading excess compute for fewer memory-bound decoding steps, this extra verification work from speculative tokens may not fit cleanly into slack, resulting in smaller improvements at high batch sizes.

In terms of cost, MTP can drive huge cost savings, in the below table, we see that DeepSeek-R1-0528 run on FP4 using Dynamo TRT costs $0.251 per million total tokens, but enabling MTP can push costs down dramatically to only $0.057 per million total tokens.

![](https://substackcdn.com/image/fetch/$s_!_ljZ!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fdcf44984-9cb9-49ae-b35a-aeb5b5d14244_1566x1778.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

In all configs, when all else is held equal, using MTP with DeepSeek R1 increases interactivity with no significant impact on model accuracy. This is in line with the DeepSeek V3 tech report findings.

![](https://substackcdn.com/image/fetch/$s_!MXVB!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F1143164c-b38f-4ca9-888a-e9e270d6ef48_1757x1187.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)

Regarding the validity of MTP performance numbers, one may argue that the distribution of a synthetic dataset may not resemble real data. However, comparing MTP acceptance behavior between MTBench and our 1k1k benchmark, we see a very similar distribution confirming that our InferenceX benchmark is a good proxy for real world production performance. That said, InferenceX is not perfect and we are always looking to improve. If you want to be part of the mission, [apply to join our special projects team here](https://app.dover.com/apply/semianalysis/2a9c8da5-6d59-4ac8-8302-3877345dbce1).

![](https://substackcdn.com/image/fetch/$s_!d8l8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F6c4a7c01-3d56-486d-b959-cb4b6468f56f_2408x1390.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)
