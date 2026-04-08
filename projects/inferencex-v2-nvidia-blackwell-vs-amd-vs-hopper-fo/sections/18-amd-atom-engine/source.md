AMD has launched a new inference engine called ATOM. Atom can deliver slightly better single node performance, but it is completely lacking on a lot of features that makes it unusable for real workloads. One such example is that it does not support NVMe or CPU KVCache offloading, tool parsing, wide expert parallelism, or disaggregated serving. This has led to zero customers using it in production. Unlike Nvidia’s TRTLLM which generates billions of tokens per hour globally at companies like TogetherAI, etc and [does support tool parsing and other features](https://nvidia.github.io/TensorRT-LLM/commands/trtllm-serve/trtllm-serve.html#cmdoption-trtllm-serve-serve-tool_parser), there are no token factories currently using ATOM due to the lack of the aforementioned features.

Furthermore, maintainers of open-source inference engines like vLLM are disappointed in AMD due to a lack of engineering and GPU resources provided by AMD. For example, Simon Mo, lead vLLM maintainer, states in this GitHub RFC that there is still no working MI355X that he can add to vLLM CI, hence the poor user experience. There are currently zero Mi355X tests on vLLM, while NVIDIA’s B200 has many tests on vLLM. Similarly, there are still not enough MI300X CI machines on vLLM. Upstream vLLM needs at least 20 more MI300 machines, 20 more MI325 machines and 20 more MI355X machines to reach the same level of usability as CUDA.

We at SemiAnalysis have been trying to get AMD to contribute more compute to vLLM and have had some success on that within the couple weeks. vLLM will start to get a couple of MI355X machines such that they can bring their CI test parity from 0% to non-0%. We will talk more about AMD’s previous lackluster contribution towards vLLM, SGLang, PyTorch CI machine situation & how Anush started to fix it in our upcoming State of AMD article. At SemiAnalysis, we will have internal dashboard to track the # of tests & quality of tests that AMD & NVIDIA runs on vLLM, SGLang, PyTorch, & JAX.

Moreover, the vLLM maintainers say that they cannot support day 0 vLLM support for ROCm due to this issue of lack of machine resources. This huge disparity in time to market continues to lead to ROCm lagging behind and leaving a huge opening for Nvidia to continue to charge an insane 75% gross margin (4x markup on cost of goods).

![](https://substackcdn.com/image/fetch/$s_!1hBL!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F96fd0617-347d-49a1-a971-19e42faeab25_1435x1289.png)

Source: [Github](https://github.com/vllm-project/vllm/issues/33478#issuecomment-3844103561)

Lastly, AMD has not had enough committers “who demonstrated sustained upstream engagement through feature shepherding and code ownership” and has a lack of reviewers that can review their own code. This is why the pace of development on ROCm vLLM has been much slower than for CUDA vLLM.

There are many talented 10x engineers at AMD that work on ATOM and we would encourage AMD management to think about re-deploying these 10x engineers towards working on libraries and frameworks that people actually use, such as vLLM and SGLang.

As we mentioned earlier, AMD also needs to prioritize addressing composability issues with FP4, wideEP and disaggregated serving as opposed to overly focusing on optimizing FP4 for a single node.

![](https://substackcdn.com/image/fetch/$s_!XDqu!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fda3b4a10-0f65-403d-a9f6-093b86753c02_2120x1258.png)

Source: [SemiAnalysis InferenceX](https://inferencemax.semianalysis.com/?i_seq=8k%2F1k&g_model=DeepSeek-R1-0528&g_rundate=2026-02-12&g_runid=21928999802&i_metric=y_outputTputPerGpu#inference)
