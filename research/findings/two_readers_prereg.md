# Pre-registration: "two readers" (Qwen2.5-7B + Kev-4B read the same fact sheet)

Written 2026-10-10T11:59+02:00 on top of commit b1763f0, BEFORE any combined number was computed. Committed
on its own before the code that computes the numbers. Nothing in this file may be changed after the first
combined run; later thoughts go into a dated "Amendments" section at the end and are labelled exploratory.

## What was known when this was written (single readers, dev, 48 calls / 24 dialogues, twin-group bootstrap)

| variant | flag AUC | CV FAR | CV review recall | CV 3-class acc |
|---|---|---|---|---|
| champion (Qwen2.5-7B facts, tuned table + light kw/pat) | 0.87 | 14% | 67% (4/6) | 79% |
| kev_facts (Kev-4B facts, tuned table + light kw/pat) | 0.86 | 0% | 0% | 69% |
| qwen_facts_para / para2 / blind | 0.72 / 0.74 / 0.73 | 23 / 23 / 18% | 0 / 0 / 0% | 67 / 71 / 58% |
| kev_facts_para / para2 / blind | 0.90 / 0.90 / 0.85 | 0 / 0 / 5% | 0 / 0 / 33% | 71 / 77 / 65% |

Dev labels: 22 no_alert, 20 alarm, 6 review. The holdout is spent and is NOT used here.

## Idea

Two independent model families answer the same atomic fact questions. Where they agree, their answer stands;
where they disagree, the call (or the fact) is escalated to a human. This is uncertainty from disagreement,
not from a tuned threshold: the only constant (0.5 gap in R2) is fixed here, before looking.

## Rules (fixed; no other variant is a candidate)

Reader A = Qwen2.5-7B-AWQ (the champion's facts backend, log-probs over yes/no/unknown, with evidence).
Reader B = Kev-4B (`fact_answer: noul`, p(yes) / 1 - p(yes), no evidence). Both read the same large-v3
transcript with the same cached roles, the same policy table and the same light keywords (0.15) + patterns (0.1).

**R1 - label agreement.** Each reader's call is decided by the champion's weighted fusion (threshold,
review band 0.15, uncertainty escalation 0.35, keywords/patterns at their weights) with its own facts check.
Then: both alarm -> alarm; both no_alert -> no_alert; anything else (any review, or alarm vs no_alert) ->
review. Call score (for AUC and the threshold sweep) = mean of the two readers' fused scores. ONE threshold
serves both readers (live there is one slider); in CV it is chosen per fold on the other folds by the
standard policies (max-F1 for "CV", recall@FAR<=20% for "CV@FAR20"), exactly like every other variant.

**R2 - fact-level agreement.** Per call, per family, per fact of the policy table (every fact; facts no rule
mentions cannot change the outcome): gap = |p_A(yes) - p_B(yes)|. Mean distribution m = mean of the two
yes/no/unclear distributions (Kev's has unclear = 0). If gap > 0.5 the fact's value is forced to `unclear`
(so the table's "unclear -> review" rules can fire); else value = discretize(m) with the champion's
decide_at 0.5 (yes if m(yes) >= 0.5, no if m(no) >= 0.5, else unclear). The policy table (first matching
rule) is then re-evaluated on these values with the soft score computed on m (the facts check's
decide_family with its default scoring constants). Evidence segments / findings are reader A's (B has none).
The combined facts result replaces both readers' facts results in the champion's weighted fusion.

**Missing reader** (both rules): if a reader's facts result is missing or errored for a call, R1 sends the
call to review; R2 treats the missing reader's distribution for the affected facts as {unclear: 1}
(so gap = the other reader's p(yes) and m = half the other reader's distribution + half unclear).
Expected count on the stored runs: 0; reported either way.

## Pairs evaluated (all dev, same 48 calls, paired over twin groups)

| pair | reader A (Qwen) | reader B (Kev) | role |
|---|---|---|---|
| tuned | kev_vs_facts/champion | kev_vs_facts/kev_facts | the candidate (acceptance A1-A3) |
| para | kev_vs_facts/qwen_facts_para | kev_vs_facts/kev_facts_para | generalisation proxy (A4) |
| para2 | kev_vs_facts/qwen_facts_para2 | kev_vs_facts/kev_facts_para2 | generalisation proxy (A4) |
| blind | kev_vs_facts/qwen_facts_blind | kev_vs_facts/kev_facts_blind | generalisation proxy (A4) |
| perturbed | kev_perturbed/perturbed | kev_perturbed/kev_facts | audio robustness (A5), only if both runs exist |

Sanity check before any number is read: re-fusing the merged results with the plain weighted fusion and
only reader A's (resp. B's) facts must reproduce the stored champion (resp. kev_facts) rows exactly.

## Acceptance (per rule, R1 and R2 judged separately; basis = out-of-fold CV unless stated)

- **A1 false alarms:** CV FAR(rule, tuned) <= CV FAR(champion) + 5 pp (point estimate; champion 14% -> <= 19%).
- **A2 review recall:** CV review recall(rule, tuned) >= champion's (>= 4 of the 6 expected-review calls).
- **A3 3-class accuracy:** the paired 95% CI of CV accuracy(rule, tuned) - champion does not lie entirely
  below 0 (not detectably worse), reported with the point difference.
- **A4 generalisation:** for EACH of para, para2, blind: flag AUC(rule on the pair) >= Qwen's flag AUC on the
  same wording + 0.10 AND CV 3-class accuracy(rule on the pair) >= Qwen's CV 3-class accuracy on the same
  wording + 5 pp. (Qwen alone: 0.72/0.74/0.73 and 67/71/58%.)
- **A5 audio robustness (informative, not part of pass/fail):** same rule on the perturbed pair vs the
  perturbed champion; reported only if kev_perturbed/kev_facts exists.

A rule PASSES only if A1, A2, A3 and A4 all hold. If both pass, the recommendation is the one with the higher
tuned CV 3-class accuracy; tie -> R1 (simpler to explain). If neither passes, the champion stays.

Reported for every pair and rule, with 95% CIs (2000 bootstrap replicates over twin groups, seed 13): flag
AUC, CV flag F1, FAR, miss rate, review recall, 3-class accuracy, CV@FAR20 FAR/recall, workload (number of
reviews), paired differences vs champion, McNemar (flag and label) and the flip list.

## Honesty limits stated in advance

- n = 48 calls / 24 dialogues / 6 expected-review calls: one review call = 17 pp of review recall. A pass on
  A2 can be one or two calls; it will be said that way.
- The reworded pairs are a proxy for unseen data, not unseen data. Both tables were written by us.
- R1 escalates every disagreement, so it trades false alarms (reviews on harmless calls) for review recall;
  A1 is the guard against "flag more = look better".
- No tuning after seeing results: no other gap than 0.5, no other combination rule, no per-family switches.
  Anything tried afterwards is exploratory and labelled so.
