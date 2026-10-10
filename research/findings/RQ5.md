# RQ5: Fact sheet + policy table vs free LLM judge vs G-Eval

**Answer in one sentence:** with the same 7B LLM, asking atomic yes/no/unknown fact questions (scored by
log-probability) and deciding with an officer-editable policy table separates "needs a human" from harmless calls far
better than the free LLM judge: flag AUC 0.84 vs 0.68 (diff +0.16 [+0.05, +0.28], real), false-alarm rate 18% vs 86%,
3-class accuracy 73% vs 38% (McNemar p = 0.0009) — but it finds the open Stufe3 review cases worse (review recall 33% vs 83%).
(confidence: medium-high for "better than the judge", low for the exact size: prompt wording was written on dev calls)

## Setup
- experiments/llm_models.yaml, variant `qwen25_7b` (profile llm-sweep: default turbo ASR, roles pinned, Qwen2.5-7B-AWQ)
  computes all checks once; `qwen25_7b__*` variants re-fuse the same results (exactly paired). Dev split, 48 calls,
  18 resampling units (twins together). commit f012763.
- `facts`: config/policy_table.yaml, 3-5 facts per family (act / context / exculpatory / authorization), answers
  yes/no/unknown read from next-token logprobs, rules "alarm if act=yes and context=yes and exculpatory!=yes", etc.

## Result
| variant (same 7B results) | flag AUC [95% CI] | alarm AUC | CV flag F1 | FAR | miss | review recall | 3-class acc |
|---|---|---|---|---|---|---|---|
| kw + pat + judge + geval (v1) | 0.68 [0.53, 0.84] | 0.79 | 0.66 | 86% | 15% | 83% | 38% |
| **facts only** | **0.84 [0.70, 0.95]** | 0.89 | 0.78 | **18%** | 27% | 33% | **73%** |
| kw + pat + facts | 0.79 [0.63, 0.92] | 0.87 | 0.78 | 18% | 27% | 50% | 58% |
| kw + pat + judge + facts | 0.76 [0.62, 0.90] | 0.84 | 0.74 | 45% | 19% | 67% | 33% |
| kw + pat + judge + geval_cot | 0.65 [0.46, 0.84] | 0.76 | 0.66 | 68% | 23% | 67% | 23% |
| everything (+facts, anchored, geval_cot) | 0.75 [0.58, 0.92] | 0.85 | 0.67 | 64% | 23% | 67% | 40% |
(CV = threshold chosen on the other dev folds.) Adding anything to `facts` makes it worse at this LLM size: the
other LLM checks mostly add false alarms.

## Calls that flip (facts only vs v1), 29 calls: 21 fixed, 6 broken
- fixed: all the `documentation` false alarms of the free judge (D01-K2, D06, D08, C02-K4, C05, C08), the harmless
  card-number calls C01/C02 ("4242..." test numbers), D03 (harmless keyword twin), and D02-K2/D04-K2/D05-K1/C07-K4/C13
  alarms that the v1 fusion left at review/no_alert.
- broken: D05-K2 (TAN read out on noisy audio: ASR garbled "Bestätigungscode" -> fact "code read out" = no),
  C06-K4 (trade alarm, noisy ASR), C18 and C20 (Stufe3 open cases -> facts says no_alert instead of review),
  C14 (harmless correction of an old address -> documentation alarm).

## Examples
- D06-K2 (harmless: expired sample code on a help document). v1 judge: "Der Kunde möchte, dass eine relevante
  Tatsache ... vor der Kreditstelle verborgen bleibt" (alarm, wrong family). facts: no_alert (code_is_sample = yes).
- D02-K2 (insider trade, noisy). v1: no_alert. facts: alarm, "Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.93)".

## Recommendation
Make `facts` the decision core (it is also the most traceable: every alarm names the facts and the policy rule an
officer can edit). Fix its review side (Stufe3): add explicit "decisive fact open" questions / let an `unknown` answer on
an act-fact trigger review, or combine with the judge's `undetermined` verdict for review only.

## Strongest counter-argument
The fact questions were worded by an agent that read dev-call ASR transcripts (dev only), so these dev numbers are
optimistic for `facts`; the free judge's prompt was written without looking at calls. The single holdout run of the
final config is the honest test. Also: the hidden test set may contain misconduct phrased in ways the fixed fact list
does not ask about (the free judge is more open-ended). Mitigation: keep the judge as a review-only signal.

## What would change our mind
A holdout result where facts loses its FAR advantage, or a bigger LLM where the free judge catches up (LLM sweep running).
