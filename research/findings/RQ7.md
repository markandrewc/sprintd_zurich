# RQ7: Borderline harmless calls (D03 and the harmless twins): who gets them right?

**Answer in one sentence:** the fact-sheet check (`facts`) is what fixes them. It clears the keyword-heavy harmless
call D03 and 15 of the free judge's harmless false flags without losing a level-1 alarm, so the false-alarm rate
drops from 86% to 18%. One weak spot is left: the Stufe2 twins C11/C14, which look like their alarm twins C12/C13.
The recommended config sends them to *review*, not *alarm*. (confidence: medium-high for D03 and the "documentation"
false alarms; low for C11/C14)

## Setup
- Sources: runs/experiments/llm_models (commit `1fd19e7`, dirty), checks_ablation (`2cc04e7`, dirty), champion
  (`795bb55`). Per-call labels are the out-of-fold CV rows (`rows.json`). Dev split: 24 dialogues / 48 calls, 22 of
  them harmless. Holdout untouched.
- Turbo ASR unless marked. "v1" = keywords + patterns + free LLM judge + G-Eval (Qwen2.5-7B). "facts" = fact questions
  + policy table (7B). "champion" = config/recommended.yaml (large-v3 MIT + 7B facts + keywords w0.15 + patterns w0.1).
- **keyword_context itself was not evaluated on its own.** It ran only inside `qwen25_7b__all_plus` (v1 + facts +
  geval_cot + keyword_context, all at weight 1). So the RQ as written ("does keyword_context fix them") is **not
  measured**. What we can answer is which check design gets these calls right.

## Result: every harmless dev call (CV label; `al` alarm, `re` review, `no` no_alert)
| call | keywords only | v1 (7B) | v1 + facts + kw_context (all_plus) | facts (7B) | champion |
|---|---|---|---|---|---|
| **Stufe1_D03-K1** (clean) | **al** | re | re | no | no |
| **Stufe1_D03-K2** (noisy) | **al** | no | re | no | no |
| Stufe1_D01-K1 / K2 | no / no | re / al | no / re | no / no | no / no |
| Stufe1_D06-K1 / K2 | al / al | re / al | no / re | no / no | no / no |
| Stufe1_D08-K1 / K2 | al / al | al / al | re / re | no / no | no / no |
| Stufe2_C01-K3 / K4 | al / no | re / re | no / re | no / no | no / no |
| Stufe2_C02-K3 / K4 | no / no | re / al | re / re | no / no | no / no |
| Stufe2_C05-K3 / K4 | no / no | al / al | re / re | no / no | no / no |
| Stufe2_C08-K3 / K4 | no / no | al / al | no / re | no / no | no / no |
| Stufe2_C10-K3 / K4 | no / no | no / no | re / no | no / no | no / no |
| **Stufe2_C11-K3 / K4** | no / no | al / al | re / re | **al / al** | **re / re** |
| **Stufe2_C14-K3 / K4** | no / no | re / re | re / re | **al / al** | **re** / no |
| **FAR (CV) [95% CI]** | 32% [7, 61] | 86% [64, 100] | 77% [62, 91] | 18% [0, 44] | **14% [0, 35]** |
| level-1 alarms: CV flag F1 / FAR / miss | 0.77 / 75% / 0% | 0.69 / 88% / 10% | 0.77 / 75% / 0% | 0.95 / 0% / 10% | **1.00 / 0% / 0%** |

facts vs v1 (same 7B results): FAR -68 pp [-92, -38] (real), 3-class accuracy +35 pp [+12, +57] (real), McNemar
3-class p = 0.0009. Adding keyword_context and the other LLM checks back on top of facts (all_plus) brings the false
flags back (FAR 77%).

## Calls that flip (v1 -> facts, 7B, CV flip table in llm_models/summary.md)
29 calls flip. Among the harmless calls, 15 are fixed (D01 x2, D03-K1, D06 x2, D08 x2, C01 x2, C02 x2, C05 x2,
C08 x2) and none is broken (C14 changes review -> alarm but was already flagged). The level-1 alarm lost by facts on
turbo (D05-K2, noisy, "Bestätigungscode" garbled by ASR) comes back with large-v3 in the champion.

## Examples
- **D03-K1** (harmless; the customer quotes a podcast about insider rules). Keywords: alarm, "Stichwort K02
  «Finanzabteilung» (Interne Quelle)" at "Im Podcast haben Sie von internen Zahlen aus der Finanzabteilung gesprochen".
  v1 judge: review, with a wrong-family reason ("... Informationen vor der Kreditprüfung"). facts / champion:
  no_alert (score 0.00 / 0.04).
- **C05-K4** (harmless; "Der grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen").
  v1: alarm 0.93 (G-Eval treats a purchase wish as suspicious). facts: no_alert 0.00.
- **C11-K3** (harmless twin of alarm C12; the balance is disclosed *with* a confirmed authorisation). champion:
  review, "Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) ... (Regel: disclosure.review_1)". The
  same rule fires on the alarm twin C12-K3. The system cannot tell the twins apart and asks a human for both. With 7B
  facts on turbo under CV the same call becomes *alarm*, because the CV threshold of 0.20 turns the rule's review
  score of 0.5 into an alarm (see RQ9).

## Recommendation
Demo item 3 (borderline case): show D03. The keyword list fires on "Finanzabteilung", but the decision stays
*no_alert* because the fact "based on non-public insider information" is answered *no*. The keyword is still visible
as evidence, at weight 0.15 in the champion, and it does not flip the call (facts alone vs champion: identical CV
labels, AUC diff +0.021 [0.000, +0.064]). For C11/C14, present *review* as the honest outcome: the decisive fact (is
the authorisation real?) needs a human.

## Strongest counter-argument
The fact questions were worded by an agent that had read dev transcripts, D03 included, so this dev result flatters
facts. On fresh synthetic twins the false-alarm advantage holds (FAR 14% vs 61%, real; see RQ10), but facts then
misses more alarms. keyword_context alone (keywords + local LLM context) was never tested and might be a cheaper fix
for D03-type calls.

## What would change our mind
New harmless keyword-heavy calls (holdout C03/C04, C15/C16 or the hidden set) that facts flags. Or a standalone
keyword_context run that matches facts on these calls at lower cost.
