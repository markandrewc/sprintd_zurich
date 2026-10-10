# RQ9: Does the system know when it is unsure?

**Answer in one sentence:** partly. The recommended config routes 10 of 48 dev calls to *review* (7 of them really
needed a human), finds 4 of the 6 open cases (review recall 67%), and is wrong on only 4 of the 38 calls it decides
itself. But that comes from named policy-table review rules, not from a calibrated sense of uncertainty. The generic
uncertainty escalation of v1 set a false-alarm floor that no threshold could lower (audit F1), and every extra
escalation we tried (judge "undetermined", blind-table second opinion, stricter access rule) buys review recall only
by breaking the 20% FAR cap. (confidence: medium-low. Dev has only 3 review dialogues, 6 calls, so one dialogue moves
review recall by 33 pp.)

## Setup
- Sources: runs/experiments/fusion (v1 checks, turbo, 7B; commit `2cc04e7`, dirty), llm_models (`1fd19e7`, dirty),
  champion (`795bb55`), synth_stress (`1fd19e7`). Dev split: 24 dialogues / 48 calls / 18 units. Holdout untouched.
- CV@FAR20 = per fold, the threshold with the highest recall at FAR <= 20% on the other folds. *FAR floor* = FAR at
  threshold 1.0, i.e. what the review rules alone flag. Above 20%, no threshold can meet the cap.
- Not measured: fitted abstention (calibrated / conformal / learned fusion via `callguard fusion-cv`). The commands
  exist in experiments/fusion.yaml but were not run.

## Result 1: uncertainty escalation sets a FAR floor (audit F1; v1 checks, 7B, turbo)
| fusion variant | FAR floor | folds where the cap is reachable | CV@FAR20 flag F1 [95% CI] | FAR [CI] | miss [CI] | review recall |
|---|---|---|---|---|---|---|
| base (escalate if uncertainty > 0.35, review band 0.15) | 36% (!) | 1/4 | 0.67 [0.45, 0.84] | 36% [10, 62] | 35% [12, 57] | 67% |
| unc025 (escalate more) | 91% (!) | 0/4 | 0.69 [0.55, 0.82] | 95% [85, 100] | 4% [0, 12] | 100% |
| noesc (no escalation) | 18% | 3/4 | 0.46 [0.21, 0.68] | 18% [0, 35] | 65% [42, 87] | 0% |
| noesc_noband (no escalation, no band) | 14% | 4/4 | 0.42 [0.18, 0.64] | 18% [0, 35] | 69% [50, 88] | 0% |

On v1 the escalation did the detection work. Switch it off and the cap becomes reachable, but two thirds of the
flaggable calls are then missed. Escalation on top of a weak signal amounts to flagging everything.
On the champion the escalation does nothing: `noesc` and `band025` give the same CV labels (FAR floor 14% in both),
because facts scores are nearly discrete (labels identical for thresholds 0.45-0.65).

## Result 2: operating points at the FAR cap (CV@FAR20)
| system | flag F1 [95% CI] | FAR [CI] | miss [CI] | review recall | FAR floor | cap met |
|---|---|---|---|---|---|---|
| v1: kw + pat + judge + G-Eval (7B, turbo) | 0.64 [0.46, 0.79] | 55% [25, 83] | 31% [12, 50] | 50% | 41% (!) | no |
| facts (7B, turbo) | 0.78 [0.63, 0.90] | 18% [0, 44] | 27% [8, 46] | 50% | 14% | yes |
| hybrid: facts + judge "undetermined" -> review (7B, turbo) | 0.72 [0.56, 0.85] | 27% [0, 50] | 31% [12, 50] | 50% | 23% (!) | no |
| facts (14B, turbo) | 0.82 [0.70, 0.92] | 14% [0, 36] | 23% [7, 42] | 17% | 14% | yes |
| facts + blind table as review-only second opinion (14B) | 0.79 [0.67, 0.90] | 36% [11, 62] | 15% [0, 33] | 50% | 36% (!) | no |
| **champion** (large-v3 + 7B facts + light kw/pat) | **0.84 [0.70, 0.95]** | **14% [0, 35]** | 19% [0, 40] | **67%** | 14% | **yes** |
| champion + access.review_2 (`table_v2`) | 0.81 [0.64, 0.94] | 36% [6, 67] | 12% [0, 30] | 67% | 36% (!) | no |

## Result 3: coverage and error on decided calls (CV rows; counted from rows.json, no CI)
| system | decided itself (alarm / no_alert) | wrong among decided | sent to review | of those, needed a human |
|---|---|---|---|---|
| v1 (7B, turbo) | 28/48 | 15 | 20 | 12 |
| facts (7B, turbo) | 45/48 | 12 | 3 | 3 |
| facts (14B, turbo) | 48/48 | 12 | 0 | 0 |
| facts + blind review (14B) | 41/48 | 10 | 7 | 2 |
| **champion** | **38/48** | **4** (C09 x2 alarm missed, C20 x2 open case missed) | 10 | 7 (C12-K3, C13 x2, C17 x2, C18 x2) |

## Calls that flip
- **hybrid vs facts (7B, CV):** 2 calls, both harmless and sent to review (C01-K3, C02-K4). The judge's
  "undetermined" never fell on an expected-review call. On the synthetic set, hybrid review recall was 5% (CV) and
  62% at the fixed threshold, vs 0% / 57% for facts alone, with FAR 25% vs 14%. Rejected.
- **blind second opinion vs facts (14B, CV):** 7 calls. 2 open cases recovered (C17-K4, C18-K3 -> review) against 5
  harmless calls newly sent to review (C01-K4, C02-K3, C05 x2, C11-K4). At the fixed threshold: review recall
  50% -> 83%, miss 23% -> 15%, FAR 14% -> 36% (journal 03:17).
- **table_v2 vs champion (CV):** 9 calls. C09 x2 alarm -> review (fixed), but the harmless "4242..." test card numbers
  C01 x2 / C02 x2 -> alarm, C10-K3 -> review, and C17 x2 review -> alarm. FAR +23 pp [+0, +54] (not detectable),
  3-class McNemar p = 0.0156 in favour of the champion.

## The two known gaps
1. **Open act (C20, splitting).** Every splitting rule needs `split_request = yes`. In C20 the act itself stays open
   ("ich kann nicht sagen, ob sie nach der Rechnung gegangen ist"), so all facts are unknown and the call ends as
   no_alert. No fact asks "is the purpose explicitly unknown?" (ideas_round2 W1). Still missed by the champion.
2. **Access: code spoken, validity unknown.** On dev, C09 reads out "acht, drei, sechs, eins, sieben, vier" with
   `spoken = ja (1.00)`, but `current` stays unclear and no rule covers spoken = yes & current = unclear -> no_alert.
   On the synthetic set, facts flags only 3 of 12 access-type positives (blind table 10/12; see RQ10). The fix
   (table_v2) costs FAR because it also catches test card numbers.

Earlier artefact, now fixed: facts review recall of 33% under CV (vs 50% fixed) came from CV picking threshold 0.20,
which turns every rule review (score 0.5) into an alarm. The champion pins threshold 0.55 / band 0.15.

## Recommendation
Ship the champion. Every review names its rule ("Regel: disclosure.review_2"), so an officer can see *why* the system
is unsure, and the FAR cap holds. Keep "failed check -> review". Offer two officer-selectable stricter policies with
their measured cost: **strict review** (blind-table second opinion: fewer misses, FAR ~36%) and **strict access**
(table_v2: C09-type calls go to review, FAR ~36%). Next fixes: "purpose open" facts for splitting and access validity.

## Strongest counter-argument
Six review calls cannot carry a reliability claim. The review rules were partly written after looking at dev errors.
Out of sample (synthetic twins), facts finds no review case at all under CV (0%; fixed threshold 57%), while
judge + facts reaches 71% (see RQ10). In compliance a miss costs more than an extra review, so a jury may prefer the
strict mode, and its FAR of ~36% is still far below v1's 55-86%.

## What would change our mind
The organisers scoring *review* as heavily as *alarm*. The holdout review case (C19) being missed. Or a conformal /
calibrated abstention that keeps FAR <= 20% with higher review recall on dev CV.
