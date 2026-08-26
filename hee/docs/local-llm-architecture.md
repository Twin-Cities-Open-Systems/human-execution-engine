# Thesis
Yes, running a local LLM for TCOS fits perfectly within an on-premises Proxmox Virtual Environment (PVE) setup. Because your architecture uses the LLM as a hard deterministic logical gate evaluating crisp binary predicates rather than generating verbose paragraphs, your processing and hardware footprints are exceptionally small. [1, 2, 3, 4] 

## 1. Hardware Specifications by Model Class
Depending on the complexity of your predicate evaluations, you can target two tiers of small local models:

## Tier A: Sub-4B Parameters (The Lightweight Target)

* Recommended Models (2026): Microsoft Phi-4 Mini (3.8B), Meta Llama 3.2 (3B), or Qwen (3B).
* Memory Footprint: A 4-bit quantized version (Q4_K_M) requires only \~3 GB of total RAM or VRAM.
* CPU-Only Execution: These models run directly on modern server CPUs without a dedicated GPU, utilizing 4 GB to 8 GB of assigned system memory. They yield between 15 and 70 tokens per second on CPU execution. Since a binary evaluation prompt requires only 1 to 2 output tokens ("0" or "1"), execution completes in under 50 to 100 milliseconds, satisfying real-world operational speeds. [3, 5, 6] 

## Tier B: 7B to 8B Parameters (The Standard Industrial Target)

* Recommended Models: Meta Llama 3.1 (8B) or Qwen (7B).
* Memory Footprint: Requires approximately 4.5 GB to 6 GB of memory for a 4-bit quantization.
* GPU Requirements: A consumer-grade or server GPU with a minimum of 8 GB VRAM is required to load the model completely into graphics memory. [5, 7, 8, 9, 10, 11, 12] 

------------------------------
## 2. Proxmox (PVE) Deployment Strategy
To run this on your PVE host with maximum hardware efficiency, avoid launching a full heavy Kernel-based Virtual Machine (KVM). Instead, implement a Linux Container (LXC) Architecture: [1, 4, 13] 

* LXC Sizing: Allocate an unprivileged LXC container (such as Ubuntu 24.04 or Debian 12) with 2 to 4 vCPU cores and 4 GB to 8 GB of RAM. The container acts as a tiny cgroup slice sharing the host's physical RAM, keeping idle overhead negligible. [13, 14, 15] 
* GPU Passthrough Pipeline: If you decide to add a physical graphics card to your PVE node (e.g., a low-cost RTX 3060 12GB or an RTX 3090 24GB):
1. Install the proprietary NVIDIA kernel drivers directly on the bare-metal Proxmox host.
   2. Bind-mount the raw GPU character devices (/dev/nvidia*) into the specific LXC container configuration file.
   3. Install the NVIDIA Container Toolkit inside the LXC container so local Docker daemons can directly access the CUDA runtime. [1, 4, 14, 15, 16] 
* The Serving Layer: Deploy a minimalist inference server like Ollama or raw llama.cpp inside the container. This provides a lightweight local HTTP/JSON API endpoint that your local automation loops or private thesis-engine can fetch from with near-zero latency. [2, 11, 16] 

If you would like to move forward with the installation, we can map out the exact LXC device pass-through configuration lines required for your Proxmox .conf file to mount the host card into the container. [11, 16] 

* [1] [https://medium.com](https://medium.com/@sahibgasimov/local-ai-with-ollama-on-proxmox-lxc-with-gpu-passthrough-244749e2487a)
* [2] [https://www.youtube.com](https://www.youtube.com/watch?v=y5-6qww8uKk&t=538)
* [3] [https://www.promptquorum.com](https://www.promptquorum.com/local-llms/small-local-llm-models)
* [4] [https://dev.to](https://dev.to/clintjosy/your-ai-your-rules-running-a-local-llm-with-gpu-acceleration-on-proxmox-1plh)
* [5] [https://www.sitepoint.com](https://www.sitepoint.com/local-llms-are-getting-easier-the-complete-guide-2026/)
* [6] [https://www.promptquorum.com](https://www.promptquorum.com/local-llms/fastest-local-llms-low-end-pcs)
* [7] [https://www.youtube.com](https://www.youtube.com/watch?v=-koMRSHFnuc)
* [8] [https://www.youtube.com](https://www.youtube.com/watch?v=9suHdD4AzuQ&t=279)
* [9] [https://www.youtube.com](https://www.youtube.com/watch?v=96iZUOu5fwc)
* [10] [https://www.promptquorum.com](https://www.promptquorum.com/local-llms/local-llm-hardware-guide-2026)
* [11] [https://www.promptquorum.com](https://www.promptquorum.com/local-llms/local-llm-hardware-guide-2026)
* [12] [https://deploybase.ai](https://deploybase.ai/articles/best-small-llm)
* [13] [https://medium.com](https://medium.com/@sahibgasimov/local-ai-with-ollama-on-proxmox-lxc-with-gpu-passthrough-244749e2487a)
* [14] [https://www.doroch.com](https://www.doroch.com/post/deploy-ollama-lxc-proxmox-nvidia-rtx3090-gpu-passthrough/)
* [15] [https://www.youtube.com](https://www.youtube.com/watch?v=T8v8Rxr8rMM)
* [16] [https://www.youtube.com](https://www.youtube.com/watch?v=lNGNRIJ708k&t=1642)


---

## Follow-up

Real four-question dissection (HEE#325's method) run against this thesis in [HEE#352](https://github.com/Twin-Cities-Open-Systems/human-execution-engine/issues/352), full writeup on that issue. Summary:

The thesis survives, but narrower than framed above. "A local LLM relieves Claude budget pressure" overstates the size of the win -- most of the real relief for tonight's actual problem came from deterministic tooling (`hee-quota`, a disk cache, `hee-sqz`) that needs *zero* inference, local or remote, and is strictly better than routing the same decision to a small model when it's available (100% deterministic vs. probably-right). The genuine niche for Ollama/llama.cpp here is narrower: the residual slice of decisions that are *fuzzy* (not reducible to a regex/threshold) but *simple* enough that a 3-8B quantized model's judgment is trustworthy for the stakes involved.

**Recommendation: don't build the LXC yet.** Standing up infra (LXC, optional GPU passthrough) before any concrete candidate call site is proven from real dogfooding is exactly the kind of premature infra this org's own doctrine argues against elsewhere. Revisit as a single centralized primitive (e.g. `hee-gate "<predicate prompt>"` -> 0/1, one Ollama endpoint, reused across tools) once a real, recurring fuzzy-but-simple gate actually shows up in practice -- not speculatively.

The timeless part of the thesis (route cheap, low-stakes judgment to an abundant-but-less-capable resource; reserve the scarce, expensive one for judgment that needs it) is real and predates any of this tech -- same shape as an apprentice handling routine measurements so a master craftsman's time goes to the hard calls. What doesn't port: throughput. This is a real but *modest* lever at the latency this org actually operates at, not the general-purpose budget fix the doc's framing implies.
