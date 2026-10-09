# Research questions

Each question gets `research/findings/RQ<n>.md` (template `findings/_TEMPLATE.md`). Protocol and
statistics: `research/AGENT.md`. Queue items that feed each question: `research/queue.yaml` (`rq:`).

| RQ | question | how to answer (dev folds, CIs) | why the team cares |
|---|---|---|---|
| RQ1 | Which **transcript view** detects best: `gsw`, `de`, `de_from_gsw`, `en_from_de`, `en_from_gsw`, `en_speech`, multi-view ensemble? | same checks + LLM, only `check_view` varies (`experiments/views.yaml`); oracle row `ref_gsw/ref_de/ref_en` as ceiling | core architecture choice; "Swiss German vs High German vs English" debate |
| RQ2 | Do Swiss German Whisper fine-tunes beat vanilla Whisper, and which one? | `callguard asr-eval` (WER/CER vs scripts / pseudo-refs, **keyword-spot recall**) + detection F1 per ASR model (`asr_models.yaml`) | which model to ship; is fine-tuning worth it |
| RQ3 | Does dialect-text output need less fine-tuning / work better for detection than Standard German output? | RQ1 + RQ2 combined: gsw-output vs de-output models, keyword-spot recall with gsw vs de keyword forms | the "transcribe in dialect vs translate" question |
| RQ4 | Which **checks** carry the decision? | ablation both ways: add each check to keywords-only, remove each from the champion (`checks_ablation.yaml`) | simplest system that works; defend each component |
| RQ5 | Fact sheet + policy table vs free LLM judge vs G-Eval | same view/LLM, swap the LLM check; also review recall + traceability (officer-readable facts) | traceability for auditors; officer-editable rules |
| RQ6 | What matters more: **LLM size** or prompt/criteria language? | 7B vs 8B vs 12-14B (transcripts cached -> LLM can use most VRAM); criteria de vs en | which model to run on Sunday's GPUs |
| RQ7 | Does `keyword_context` fix harmless keyword calls (D03 and the level-2 harmless twins) without losing level-1 alarms? | per-call flips on keyword-heavy calls; FAR change | demo item 3 (borderline case) |
| RQ8 | How big is the clean vs noisy gap, and does denoising / beam size / prompt biasing close it? | per-variant clean/noisy breakdown, keyword-spot recall | robustness claim |
| RQ9 | How well does the system **know when it is unsure**? | review recall, error rate on decided calls, coverage; uncertainty escalation vs calibrated/conformal abstention | 25% criterion includes "escalates instead of guessing" |
| RQ10 | Do **synthetic calls** help (few-shot pools, learned fusion, prompt dev)? | train/few-shot on synthetic only, evaluate on case dev folds | data strategy; scaling story |
| RQ11 | Does a **LoRA fine-tune** of Whisper on dev-fold case audio help on held-out folds? | `finetune/` with fold-aware training; asr-eval + detection on the held-out fold | fine-tuning investment for Sunday |
| RQ12 | **Cost**: GPU seconds per call minute per configuration; what hardware does a bank need for N call minutes/day? | timings from all runs; cascade (A2) vs full | feasibility (10%) and operating concept |
