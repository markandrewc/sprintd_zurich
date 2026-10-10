# Two readers (Qwen2.5-7B + Kev-4B on one fact sheet): does agreement / disagreement beat the champion?

**Answer in one sentence:** No. Both pre-registered rules FAIL: R1 (label agreement) keeps the false-alarm rate
and ranks better (AUC 0.93), but it turns 6 clear alarms into reviews and costs 15 pp of 3-class accuracy (CI
excludes 0). R2 (fact agreement) loses every review call. The champion stays. (confidence: high for "does not
pass", low for any finer ranking at n = 48)

Pre-registration: `research/findings/two_readers_prereg.md` (commit 83ba310, 2026-10-10 12:00, before any
combined number). Full report with every CI, McNemar and flip list: `runs/experiments/two_readers/acceptance.md` (snapshot: `research/evidence/experiments/two_readers_acceptance.md`)
(regenerate: `uv run callguard agreement run`).

## Setup
- code: commit 7957d36 (fusion plugin `two_readers`, `src/callguard/agreement.py`, `callguard agreement`),
  profile `config/two-readers.yaml`, experiment `experiments/two_readers.yaml`
- data: no model ran. Each wording's two stored single-reader runs (`kev_vs_facts/*`) are joined into one source
  (`*_src`, reader B's facts -> check `facts_kev`) and re-fused with the standard experiment runner
  (`refuse_from`), so fixed / CV / CV@FAR20 rows and every statistic come from the same code as every other variant.
- sanity: re-fusing the joined sources with "reader A alone" / "reader B alone" reproduces all 8 stored runs
  exactly (0/48 calls differ, fixed and CV rows). Transcripts and keyword/pattern results are identical between
  the readers on all 48 calls (merge reports).
- split: dev, 48 calls / 24 dialogues (twin groups as bootstrap unit), 22 no_alert / 20 alarm / 6 review.
  Holdout untouched.

## Result (CV rows; AUC on the fixed-threshold scores; 95% CI, 2000 bootstrap replicates over twin groups)

| wording | system | flag AUC | CV flag F1 | CV FAR | CV miss | review recall | 3-class acc | reviews |
|---|---|---|---|---|---|---|---|---|
| tuned | champion (Qwen) | 0.87 [0.72, 0.99] | 0.86 [0.73, 0.96] | 14% [0, 35] | 15% [0, 36] | 67% (4/6) | 79% [63, 95] | 10 |
| tuned | Kev alone (kev_facts) | 0.86 [0.67, 0.98] | 0.82 [0.62, 0.95] | 0% [0, 0] | 31% [9, 56] | 0% (0/6) | 69% [48, 86] | 6 |
| tuned | **R1 labels** | 0.93 [0.82, 1.00] | 0.88 [0.78, 0.98] | 14% [0, 35] | 12% [0, 29] | 50% (3/6) | 65% [45, 83] | 16 |
| tuned | **R2 facts** | 0.84 [0.65, 0.98] | 0.82 [0.65, 0.94] | 14% [0, 35] | 23% [0, 47] | 0% (0/6) | 69% [50, 87] | 5 |
| para | Qwen | 0.72 [0.52, 0.88] | 0.68 | 23% | 38% | 0% | 67% [50, 83] | 1 |
| para | Kev | 0.90 [0.73, 1.00] | 0.87 | 0% | 23% | 0% | 71% [52, 86] | 7 |
| para | R1 | 0.86 [0.68, 0.97] | 0.78 | 23% | 23% | 17% | 56% [38, 74] | 16 |
| para | R2 | 0.80 [0.60, 0.94] | 0.70 | 18% | 38% | 0% | 67% [50, 82] | 2 |
| para2 | Qwen | 0.74 [0.54, 0.90] | 0.73 | 23% | 31% | 0% | 71% [56, 85] | 1 |
| para2 | Kev | 0.90 [0.71, 1.00] | 0.89 | 0% | 19% | 0% | 77% [57, 92] | 4 |
| para2 | R1 | 0.85 [0.68, 0.99] | 0.83 | 23% | 15% | 33% | 67% [50, 84] | 14 |
| para2 | R2 | 0.79 [0.59, 0.93] | 0.73 | 23% | 31% | 0% | 71% [56, 85] | 1 |
| blind | Qwen | 0.73 [0.53, 0.90] | 0.67 | 18% | 42% | 0% | 58% [39, 77] | 3 |
| blind | Kev | 0.85 [0.68, 1.00] | 0.83 | 5% | 27% | 33% | 65% [44, 83] | 12 |
| blind | R1 | 0.84 [0.71, 0.96] | 0.83 | 23% | 15% | 67% | 56% [38, 75] | 21 |
| blind | R2 | 0.75 [0.59, 0.90] | 0.71 | 23% | 35% | 0% | 58% [41, 74] | 6 |

Paired vs the champion (tuned, B - A): R1 d AUC +0.06 [-0.00, +0.16], d FAR +0 pp, d miss -4 pp [-12, +0],
d 3-class accuracy **-15 pp [-32, -2]** (McNemar label 7 vs 0 calls, p = 0.016; flag 0 vs 1, p = 1.0).
R2 d AUC -0.02 [-0.20, +0.12], d accuracy -10 pp [-28, +2], review recall -67 pp.
Paired vs Qwen on the same reworded table: R1 d AUC +0.14 / +0.12 / +0.12 (CIs exclude 0), d accuracy
-10 / -4 / -2 pp (CIs include 0). Kev alone is at least as good as R1 on every reworded AUC (0.90 / 0.90 / 0.85).

## Verdict per pre-registered criterion

| criterion | R1 labels | R2 facts |
|---|---|---|
| A1 CV FAR <= champion + 5 pp (<= 19%) | pass (14%) | pass (14%) |
| A2 review recall >= champion (4/6) | **FAIL** (3/6) | **FAIL** (0/6) |
| A3 3-class acc paired CI not entirely below 0 | **FAIL** (-15 pp [-32, -2]) | pass (-10 pp [-28, +2]) |
| A4 reworded: AUC >= Qwen + 0.10 AND acc >= Qwen + 5 pp, all three | **FAIL** (AUC ok 3/3, accuracy 0/3) | **FAIL** (0/3) |
| A5 re-recorded audio (informative) | not evaluable: `kev_perturbed/kev_facts` never ran | same |
| **overall** | **FAIL** | **FAIL** |

## Why (calls that flip, tuned table)
- **R1** puts 6 Stufe1 alarms (D05, D09, D10, both recordings each) into review: Qwen says alarm, Kev says
  no_alert (Kev alone misses 31% of flaggable calls). For "send it to a human" that changes nothing (flag-correct
  either way; flag F1 0.88 vs 0.86, CV@FAR20 recall 85% vs 81% at the same 14% FAR), but the case scores the exact
  label and these are clear alarms. It also needs ONE threshold for both readers: CV picks 0.35 in 3 of 4 folds
  (Qwen alone: 0.65, Kev alone: 0.2), which turns the review call C17-K4 into an alarm (3/6 instead of 4/6).
  It flags one call the champion missed: C09-K4 (expected alarm, Qwen no_alert, Kev alarm -> review; flag
  fixed, label still wrong).
- **R2** cannot produce reviews from Kev's answers: Kev's distribution has no "unknown" mass, so averaging it
  with Qwen's halves the "unclear" probability. Of 486 fact answers Qwen left unclear on the tuned table, 234
  become yes/no after averaging, so the table's "unclear -> review" rules stop firing; the 94 facts forced to
  unclear by a gap > 0.5 change only 2 family decisions. The C17 review calls end as alarms (table review score
  0.5 is above the CV threshold 0.35), the C18 review calls as no_alert.

## Exploratory (post hoc, NOT a candidate; numbers only to answer "was it the shared threshold?")
R1 on each reader's own out-of-fold CV label (two thresholds, computed from the stored CV rows): tuned review
recall back to 4/6, FAR 14%, but 3-class accuracy 67% (-12.5 pp vs champion, CI [-30, 0]), and reworded
accuracy 56 / 67 / 56% (still below Qwen + 5 pp). The shared threshold is not the main problem; Kev's misses
on Stufe1 alarms are.

## Recommendation
Keep the champion (`config/recommended.yaml`). Do not ship two readers as the default. If the jury pitch wants
"shows when unsure and escalates", the honest numbers are: R1 flags at least as well as the champion (same FAR,
miss 12% vs 15%, AUC 0.93 vs 0.87, differences within the noise) but labels 16 calls "review" instead of 10 and
gets the exact label right less often (65% vs 79%, a real loss). It is available as an opt-in profile
(`-c two-readers`) for a "strict second opinion" mode, like the hybrid fusion.

## Strongest counter-argument
Exact 3-class accuracy punishes "review" on a clear alarm as hard as a miss, though operationally a review still
reaches a human. If the bank valued flag recall at a fixed FAR above label exactness, R1 would be the better
operating point (flag F1 0.88 vs 0.86, miss 12% vs 15%), but that difference is 1 call in the flag McNemar and
not detectable at n = 48.

## What would change our mind
- A second reader that can say "unknown" (Kev `fact_answer: choice` scored 0% review recall alone, so not Kev
  as it is) or a second reader that does not miss the Stufe1 alarms.
- The re-recorded-audio pair (A5): run `kev_perturbed` stage 2 (`kev_facts`), then
  `uv run callguard agreement run --only perturbed` on the host with `data_perturbed/v1`.
- More review calls: 6 is too few to tell 3/6 from 4/6.
