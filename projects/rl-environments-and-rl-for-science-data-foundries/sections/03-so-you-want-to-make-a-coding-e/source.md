Demand for coding environments is so high that we believe defunct startups are getting acquired specifically for the value of another private GitHub repo to make environments out of. Understanding why these repos are so valuable requires understanding how coding environments are actually constructed. The process is more involved than it might seem.

SWE-rebench is a benchmark that aggregates thousands of Python tasks from GitHub and showcases how these environments are constructed. The process it employs is also automated, which is what we expect the labs to be doing.

The pipeline starts with downloading the GitHub Archive, containing 30k repos and 450k PRs with permissive licenses. This dataset is then filtered for several categories: PRs have to be resolved, merged to the main branch, have sufficient descriptions of the problem, impact more than one file, etc. PRs must introduce or modify test files as that is what is used for grading. For example, if a model’s patch causes previously failing tests to pass (without breaking others), the task is marked as solved.

To automate environment configuration, an LLM generates installation instructions for each task. The model reads relevant files in the repository (README, setup.py, requirements.txt, Docker files), then synthesizes a structured JSON “recipe” specifying the Python version, dependency installation commands, and test execution commands.

![](https://substackcdn.com/image/fetch/$s_!Y6RD!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2F997762d1-a8cc-47ab-b1b5-494566767783_1460x779.png)

Source: [Badertdinov, Golubev et al.](https://arxiv.org/pdf/2505.20411)

Each candidate task then undergoes execution-based verification. The environment is instantiated in a container, and tests from the PR’s test patch are executed. A task is considered valid only if at least one test fails before applying the solution patch, all initially failing tests pass after the patch is applied, and any tests that passed before continue to pass. After all the filtering, we end up with 21,336 tasks from the 450k we started.

But most PRs do not meet the strict criteria, which is why the yield is low. SWE-smith demonstrates this by having an LLM install repositories at their latest commit, then synthesizing bugs through four methods: prompting a model to introduce subtle errors into working functions, applying deterministic AST transformations like flipping if/else blocks or removing loops, using an LLM to semantically reverse real PRs against the current codebase, and combining validated single-function bugs into harder multi-file tasks. Every candidate is validated by checking if it breaks at least one existing test.

Importantly, these approaches aren't mutually exclusive. PR mining captures realistic bug patterns from actual development history and synthetic generation provides volume and coverage across the entire codebase. A lab with access to private repositories could run both pipelines against the same environments, first mining PRs then improving them with synthetic bugs. This combined approach is likely a strong approximation for how frontier labs are constructing RL environments for code.

At scale, these pipelines produce tasks in the tens of thousands. DeepSeek ended up using 24,667 coding tasks extracted from GitHub for the training of V3.2. We know, from other labs like Kimi, that the infrastructure developed can support the instantiation of 10,000+ instances simultaneously. Generally speaking, the more difficult the task the more rollouts are needed during training. This is due to the problem being harder to solve, and the more rollouts, the more “shots on goal” the model has. However, this comes at the expense of each rollout being slower as throughput comes at the expense of speed.

![](https://substackcdn.com/image/fetch/$s_!7Ln8!,w_1456,c_limit,f_auto,q_auto:good,fl_progressive:steep/https%3A%2F%2Fsubstack-post-media.s3.amazonaws.com%2Fpublic%2Fimages%2Fe8df58ac-7c11-491d-9233-53f934d71a74_1536x1011.png)

Source: SemiAnalysis
