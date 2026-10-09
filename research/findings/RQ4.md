# RQ4: Which checks carry the decision?

**Answer in one sentence (round 1, Qwen2.5-7B):** the LLM judge is the only check that finds the context cases
(Stufe2/3) and is required for recall (removing it: miss rate +46 pp [+23, +68], real), but with the 7B model it also
causes most false alarms; keywords/patterns add little on top of the LLM checks, and plain G-Eval is nearly constant.
(confidence: medium; will be re-run with the winning LLM)

## Setup
- experiments/checks_ablation.yaml, base `gpu-12gb` (Swiss German turbo int8 ASR, sherpa diarization + LLM roles,
  Qwen2.5-7B-Instruct-AWQ on vLLM), dev split (48 calls / 24 dialogues / 18 resampling units, Stufe2 twins grouped),
  `all` computed once, every other variant = re-fusion of the same check results (exactly paired). commit e1954e9.

## Result (out-of-fold CV: threshold picked on the other dev folds)
| variant | flag F1 [95% CI] | FAR [CI] | miss [CI] | alarm F1 | review recall |
|---|---|---|---|---|---|
| all (kw+pat+judge+geval) | 0.67 [0.46, 0.83] | 45% [18, 72] | 31% [9, 54] | 0.55 | 67% |
| keywords only | 0.47 [0.20, 0.71] | 32% | 62% | 0.50 | 0% |
| kw + patterns | 0.37 [0.07, 0.61] | 23% | 73% | 0.34 | 0% |
| kw + pat + judge | 0.69 [0.53, 0.81] | 91% | 8% | 0.44 | 83% |
| kw + pat + geval | 0.36 [0.09, 0.62] | 5% | 77% | 0.33 | 0% |
| llm only (judge + geval) | 0.70 [0.54, 0.83] | 68% | 15% | 0.70 | 33% |

Per level (all, CV flag F1 / FAR / miss): Stufe1 0.86 / 25% / 10%, **Stufe2 0.43 / 57% / 50%**, Stufe3 0.80 / - / 33%.
At the configured threshold 0.55 the fused system flags 91% of harmless calls (CV picks 0.65-0.90 instead).

## Diagnosis (scripts/research/diagnose.py checks_ablation all)
- **G-Eval collapses to "3/5"** (the scale middle, labelled "undetermined") for nearly every call and family, ~99% of
  the probability mass, even when its own evidence reason describes the misconduct (e.g. Stufe2_C12-K3 disclosure).
  It only separates the obvious Stufe1 alarms (0.85-0.99). -> new check `geval_cot` (analysis first, no middle anchor).
- **llm_judge (7B) over-triggers on `documentation`** ("Relevante Angabe verschweigen"): 0.95+ on harmless calls
  (D01-K2, D08-K1, C05-K3, C08-K4, C11-K3, C14-K3, C18). That family is the top source of false alarms.
- Stufe2 true alarms and Stufe2 harmless twins get the same fused score (~0.70): judge 0.97 + geval 0.50 on both.

## Recommendation (provisional)
Keep keywords + patterns (cheap, traceable, the officer-editable part) but the decision quality is set by the LLM
check. Fix the LLM layer first (bigger LLM, G-Eval scale, documentation criteria), then re-run this ablation.

## Strongest counter-argument
With a stronger LLM the picture may change (keywords may then mostly add false alarms on harmless keyword calls like
D03, where the LLM alone is right). The ablation is conditional on the 7B model.
