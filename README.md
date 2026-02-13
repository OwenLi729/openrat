# openrat
Your personal AI lab rat. Research-first agent designed to run, debug, chain, schedule, and report experiments. 

Openrat is built for researchers and research institutions, and it is privacy-first. Under a FFOS license, you can rest assured that any proprietary data, code, or experiments you run remain solely on your local device. You can use also Openrat as an extension in VSCode, as well as any other IDE or text editor convenient to you. While running Openrat, you can use models locally, on the cloud, or choose to use API credits. 

Openrat is designed to automate computational experiments. It is not necessarily meant to code experiments, but can be used to help debug and add to existing code. After you give it instructions (.json, .txt, .md, or prompt the UI), Openrat will run, debug, and report the result of your experiments to you (if you give it access to your email). We specifically try to integrate with lightweight open-source models and use SOTA techniques to decrease computational cost efficiently to save you tokens and electricity, but you can also use heavier closed-source models. 

While Openrat runs pre-specified experiments, you can go about your day and wait for it to report results. Openrat reports a comprehensive diagnostic which shows the result of the experiment, reasoning chains and debugging processes, as well as token expenditure. If you want to stay out for longer, you can chain and branch experiments with Openrat using natural language (or if you want more reliability, add additional details to the instruction file). Openrat will ask questions before running experiments as well as notify you with any updates if it requires additional informations or encounters errors/bugs while running. It is designed to ask for help and maintain a human in the loop as necessary.

Chaining experiments just means running experiments in sequence (or in parallel if necessary), and you can create branches with consecutive experiments based on the result of one. So for example, you can create a branch which runs experiment X only if result Y is encountered in the previous experiment, or have it modify the experiment when you encounter a specific result. Openrat tries to maintain interpretability and so the agent has a predetermined specific set of actions it can take following each result (?) as in you can't tell it to like code a SaaS app if the experiment fails but you can tell it to change a variable.

Openrat generates artifacts such as diagnostic reports that can include text summaries and graphs post-run. 

It is a research‑first experiment runner that can inspect, diagnose, and propose code changes, but it does not autonomously rewrite large portions of your codebase.

Openrat’s code interaction is constrained, explicit, and auditable:

It can make small, scoped modifications (e.g. hyperparameters, config values, flags)
It can apply surgical fixes for runtime errors only with user approval
It can suggest patches without applying them
It never refactors or expands a project unless explicitly instructed
The goal is to protect research intent and reproducibility, not replace the researcher. For more substantial changes, Openrat provides suggested patches and explanations rather than applying them automatically.

Capability-scoped autonomy (4 levels).
