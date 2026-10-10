# RQ1: Which transcript view detects best?

**Answer in one sentence:** keep the Standard German view (`de`, from the Swiss German Whisper model): an English
translation of it adds an LLM pass and detects no better (flag AUC 0.82 vs 0.84, same 7B, CIs overlap), and even a
perfect dialect transcript (ORACLE) is not better for the 7B model (0.76) and only slightly better for the 14B
(0.90 vs 0.85-0.87, CIs overlap). (confidence: medium. The direction holds across both models, but no pairwise
difference clears the noise at n = 24 dialogues.)

## Setup
- experiments/llm_models.yaml, summary commit `1fd19e7` (dirty), variants `qwen25_7b__facts_only` (de, turbo),
  `qwen25_7b_facts_en` (en_from_de), `qwen25_7b_facts_l3` / `qwen25_14b_facts_l3` (de, large-v3),
  `qwen25_*_facts_oracle` (ORACLE: dialect reference scripts `ref_gsw`, no ASR), `qwen25_14b_facts` (de, turbo).
- The check is `facts` (fact questions + tuned policy table) in every row. Only the text it reads changes.
- Dev split: 24 dialogues / 48 calls / 18 resampling units (twin pairs together). Bootstrap 2000x, seed 13. Holdout untouched.
- ASR: turbo = `nebi` Swiss German turbo int8 (default). large-v3 = `gcoli` Swiss German large-v3, MIT, fp16.
  Translation for `en_from_de`: the same Qwen2.5-7B-AWQ, from the turbo `de` transcript.

## Result
| view (text the check reads) | LLM | flag AUC [95% CI] | CV flag F1 [95% CI] | CV FAR [CI] | CV miss [CI] | review recall (CV) | 3-class acc |
|---|---|---|---|---|---|---|---|
| de (turbo ASR) | 7B | 0.84 [0.70, 0.95] | 0.78 [0.63, 0.90] | 18% [0, 44] | 27% [8, 46] | 33% | 73% |
| en_from_de (turbo ASR + LLM translation) | 7B | 0.82 [0.68, 0.95] | 0.75 [0.52, 0.91] | 18% [0, 40] | 31% [8, 58] | 0% | 71% |
| **de (large-v3 ASR)** | 7B | **0.89 [0.77, 0.99]** | **0.86 [0.73, 0.96]** | 14% [0, 35] | 15% [0, 36] | 67% | 79% |
| gsw ORACLE (perfect dialect script) | 7B | 0.76 [0.56, 0.92] | 0.64 [0.38, 0.83] | 18% [0, 45] | 46% [18, 73] | 0% | 62% |
| de (turbo ASR) | 14B | 0.87 [0.76, 0.96] | 0.82 [0.70, 0.92] | 14% [0, 36] | 23% [7, 42] | 0% | 75% |
| de (large-v3 ASR) | 14B | 0.85 [0.73, 0.96] | 0.80 [0.67, 0.91] | 18% [0, 40] | 23% [4, 44] | 0% | 65% |
| gsw ORACLE (perfect dialect script) | 14B | 0.90 [0.79, 1.00] | 0.87 [0.70, 1.00] | 0% [0, 0] | 23% [0, 47] | 67% | 88% |

Paired differences between views were **not computed** (the summary compares every variant with the v1 baseline only).
The marginal CIs overlap almost completely, so: **no detectable difference at n = 24 dialogues** between de and
en_from_de, or between de and the dialect ORACLE.

Cost: the English view adds a translation stage of 16.5 s per call (7B, stage time in this run) before the checks.

## Calls that flip (de -> en_from_de, 7B, turbo, CV rows)
10 calls change label. For the flag decision 3 get better and 4 get worse.

| call | expected | de | en_from_de |
|---|---|---|---|
| Stufe1_D05-K2 | alarm | no_alert | alarm |
| Stufe2_C06-K4 | alarm | no_alert | alarm |
| Stufe2_C14-K3 | no_alert | alarm | no_alert |
| Stufe1_D08-K1 | no_alert | no_alert | alarm |
| Stufe2_C13-K3 / K4 | alarm | alarm | no_alert |
| Stufe3_C18-K4 | review | alarm | no_alert |
| Stufe2_C07-K3 | alarm | review | alarm |
| Stufe3_C17-K3 / K4 | review | review | alarm |

The changes go both ways and cancel out. Translation moves single calls around but does not make the system better.

## Not run, and why
- **en_speech** (Whisper's own speech-to-English translation): this needs the vanilla multilingual large-v3. The
  Swiss German fine-tunes only write German. Vanilla large-v3 fp16 next to vLLM runs out of memory on 12 GB (OOM seen at
  bring-up), so it would have needed its own GPU slot. en_from_de had already shown no gain, so that GPU time went to
  the LLM sweep (journal 04:06).
- **de_from_gsw / en_from_gsw** need a dialect-output ASR, and no public one exists (see RQ3).
- **ref_de / ref_en ORACLE rows and the multi-view ensemble**: not measured. The only multi-hypothesis view we tried is
  the `de_fused` correction view, on 4 calls and only for ASR quality (see RQ8).

## Recommendation
Ship the `de` view from the large-v3 MIT model. Use English only as an on-demand display translation for officers,
not as detection input.

## Strongest counter-argument
The English view was built from the weaker turbo transcript and judged with German-tuned fact questions. Its review
recall of 0% is partly a CV threshold artefact (see RQ9). English criteria, a bigger LLM, or a translation of the
large-v3 transcript might do better. None of that was tested.

## What would change our mind
en_from_de (or en_speech) on large-v3 transcripts beating `de` with a paired CI that excludes 0. Or test calls in
mixed languages, where a common English pivot could help.
