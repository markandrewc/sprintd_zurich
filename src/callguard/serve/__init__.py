"""Running the models on another machine (the GPU PC, reached over Tailscale).

* :mod:`callguard.serve.asr_server`: stdlib HTTP front for the profile's ASR backend, the counterpart
  of ``asr: {type: remote}`` (:mod:`callguard.asr.remote`).
* :mod:`callguard.serve.doctor`: readiness probes behind ``callguard doctor`` (servers reachable,
  model files present, CUDA usable) that never load a model themselves.

The LLM needs no code here: vLLM / llama.cpp already speak the OpenAI API. See docs/REMOTE_GPU.md.
"""
