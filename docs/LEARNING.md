# Learning from officer decisions

Every time an officer checks an alarm or a review, that judgement is a label. This document describes how
callguard captures those labels, what it does with them today (threshold calibration with a four-eyes
approval) and what it will do once there are enough of them (fine-tuning, behind a shadow test).

Code: `src/callguard/feedback.py` (capture, store), `src/callguard/learning/` (records, hygiene, export,
insights, recalibrate, proposals, demo), `src/callguard/commands/learn.py` (CLI), UI: panel *Rückmeldung*
(`ui/panels/feedback.py`), pages *Feedback & Tuning* (`ui/views/feedback.py`) and *Lernen*
(`ui/views/learning.py`). Fine-tuning contract and skeleton scripts: `finetune/`. Tests: `tests/test_learning.py`.

## 1. Capture (call detail, panel "Rückmeldung")

One form per call, saved with one click:

| what | options | stored as (`feedback.jsonl`, schema 2) |
|---|---|---|
| verdict on the call | Verstoss bestätigt / Kein Verstoss / Unklar | `violation` / `no_violation` / `unclear` -> label alarm / no_alert / review |
| each shown passage | Trifft zu / Trifft nicht zu | `applies` / `not_applies` + passage snapshot (family, start, end, text) |
| each fact of the facts check (families that fired, shown passages, top family) | stimmt / stimmt nicht / unklar, each naming the value it records ("stimmt nicht (nein)") | `fact` + `check`, `family`, `fact`, `question`, `answer`, `model_value`, `agrees` |
| übersehene Kategorie | any family the system did not show | `missed_family` + `family` |
| comment, officer name | free text | on every item; `user` |

Answers in the panel **Offene Fakten** (audit event `fact_answer`) are per-fact labels too and are read
from the audit log (`source: open_facts`; a later `fact_answer_reset` drops them); the feedback form does
not ask them twice.

Every schema-2 item carries `provenance`: config name + hash, code version, tuning-overlay hash,
policy-table path + hash, model id per check, ASR backend per view, a hash of the transcript the checks
read, and the decision shown (label, score, threshold, top family). A label given under policy table
`1d7f…` with Qwen2.5-7B stays interpretable after the table or the model changes. Items of one submission
share a `batch` id. The file is append-only; per call / passage / fact the latest judgement wins.

**Compatibility.** Schema-1 lines (`confirmed` / `false_alarm` / `missed` / `should_review` / `not_review`,
optional `passage_index`) load unchanged (`schema_version` 1) and keep their meaning in
`labels_from_feedback`, so `callguard feedback suggest/apply` and old stores keep working. No migration
is needed.

## 2. Split hygiene (enforced, tested)

`callguard.learning.hygiene.use_of(call)`:

| call | use | may train a model | may tune the threshold |
|---|---|---|---|
| case dialogue in a dev fold | `eval_case_dev` | **never** | yes (dev folds, CV) |
| case dialogue in the holdout (or a case-style id missing from `splits.yaml`) | `eval_case_holdout` | **never** | **never** |
| new call, twin unit hashed into the 80 % side | `train` | yes | yes |
| new call, twin unit hashed into the 20 % side | `shadow_test` | no (unseen test set for retrained models) | yes |
| anything from the simulated demo store | `demo_only` | **never** | demo proposals only, marked |

The unit is the twin group of `config/splits.yaml`, else the dialogue (`-K1`/`-K2` of one conversation
share it), so clean and noisy recordings are always on the same side. The hash is stable, so a call never
changes sides as labels accumulate. `hygiene.check` / `enforce` run on every export; the export fails
instead of leaking.

## 3. Export: `callguard learn export [-c profile] [--demo] [--out dir]`

Writes to `runs/<profile>/learning/export/`:

* `calls.jsonl` (b): officer label, system label + score + per-family scores, use, provenance: input for
  threshold / calibration fits.
* `passages.jsonl` (c): applies / not applies per shown passage: localisation.
* `facts.jsonl` (a): every per-fact label (all uses) as a flat row.
* `kev_noul.{train,shadow_test,eval_dev}.jsonl`, `kev_choice.*`, `qwen_sft.*` (a): model-ready fact
  records. Kev: one request per call with all its labelled facts as questions (Kev answers many questions
  about one state in one pass), instruction = `Topic: <family label> [<id>]\n<question>` exactly as
  `KevLLM` sends it, state = transcript as the facts check renders it. Qwen: the facts check's own chat
  prompt + the one-word answer. Formats in `finetune/README.md`.
* `manifest.json`: counts per file and use, trainable fact labels, sources, policy-table / config hashes seen.

Holdout calls appear only in `calls.jsonl` / `facts.jsonl` (marked); demo labels never in a model file.

## 4. Lernen page

* KPIs: labels, labelled calls, fact labels, officer = system (Wilson 95 % CI).
* Confusion: rows officer, columns system; false alarms and misses counted.
* Labels per family and per fact question.
* Most-corrected fact questions: correction rate with CI and direction (`unclear->yes`); >= 30 % of >= 3
  labels -> "Frage X wird in 40 % der Fälle korrigiert -> Formulierung prüfen" with a link to the rule book
  (strong once n >= 5, otherwise flagged as a hint). Rules whose outcome officers change.
* Readiness per learning step, counting only labels that may be used for it:

| step | needs | why that number | status today |
|---|---|---|---|
| threshold (global) / per family | 10 calls / ~30 per family | 2-parameter fits; dev has 4-14 calls per family | global: now (with CV); per family: not yet |
| few-shot examples from confirmed cases | ~5 per fact | | **measured as not helpful**: S2 fold-aware few-shot AUC 0.80 (tuned) / 0.70 (paraphrased) vs 0.87; stays off |
| LoRA of the fact reader (Kev / Qwen) | ~1,000 trainable fact labels | Kev upstream: 1,000 records for a measurable +5 points, 400 = noise | roadmap; case calls never count |
| Whisper fine-tune | real recordings with corrected transcripts | ORACLE: perfect transcripts only +0.03-0.05 AUC | roadmap |

* Export button, shadow-evaluation contract, pitch sentence.

## 5. The step that works now: threshold re-fit with four eyes

`callguard.learning.recalibrate.propose_threshold` (page *Feedback & Tuning*, CLI `callguard learn propose`):

1. Labels = officer call labels; holdout calls dropped.
2. Fitted threshold = `eval.suggest_threshold` on the labelled calls (fusion only, on stored check results).
   If the current threshold is tied with the best, the verdict is **keep** (nothing to change).
3. Expected effect, honestly: dialogue-fold CV (dev folds of `splits.yaml`; new calls hashed by twin unit)
   chooses the threshold on the other folds and decides the held-out fold; compared with the current
   threshold on the same calls by a paired bootstrap over twin units: flag F1, false-alarm rate, miss rate,
   accuracy with 95 % CIs. Verdict `better` only if the F1 CI excludes 0 upward and false alarms do not rise.
4. A *proposal* is filed (`runs/<profile>/learning/proposals.jsonl`, audit `proposal_proposed`) with the
   evidence. **Never auto-applied.**
5. A **different person** approves (or rejects): the change goes into `config/tuning.yaml` via
   `feedback.apply_tuning` (audit `tuning_save` with file hashes + `proposal_approved`). Same person ->
   `FourEyesError` (names compared case- and space-insensitively).
6. **Rollback** restores the overlay entry from before the approval exactly (`feedback.restore_tuning`,
   audit `proposal_rolled_back`). A newer approval of the same profile marks the older one `superseded`.

`callguard feedback apply` (CLI, admin) still writes the overlay directly; the UI only offers proposals.

## 6. Demo data

`callguard learn demo-seed -c <profile>` (or the button on *Lernen*) simulates officer feedback for the
**dev** calls only, from the expected labels: call verdict (alarm -> Verstoss bestätigt, review -> unklar,
no_alert -> kein Verstoss), passages (trifft zu if of the expected family and the call should be flagged),
missed category, and per family of the facts check the smallest change of fact values (one fact, else two;
least confident first) that makes the policy table give the expected label (otherwise the facts of the
fired rule are confirmed). Stored in `feedback_demo.jsonl` (`source: demo`, user `Demo (simuliert)`,
comment "Demo-Feedback (simuliert aus Sollbewertung)"), never mixed with real feedback (the store API
refuses), never trainable (`demo_only`). The pages show a warning banner whenever the demo store is selected.

## 7. Fine-tuning later

See `finetune/README.md`: data only from `*.train.jsonl`, unseen `*.shadow_test.jsonl` calls, >= ~1,000
trainable fact labels, a pre-registered paired-bootstrap rule (CI excludes 0, no rise in false alarms),
activation only through a four-eyes approved config change with rollback.
