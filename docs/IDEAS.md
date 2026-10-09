# Idea backlog (beyond research/queue.yaml)

Not scheduled yet; promote to the queue (research) or docs/STATUS.md (build) when useful.

## Detection
- Per-family thresholds and per-family check weights (CV-chosen), instead of one global threshold.
- Temporal reasoning: extract an ordered event list (warning -> code read out -> refusal) so "a later
  refusal does not undo it" is explicit; check against criteria.
- Speaker-attributed facts: who expressed the trade wish / who disclosed (customer vs advisor) as a
  first-class fact in the fact sheet.
- Counterfactual explanation: "this would be an alarm if ..." generated from the policy table.
- Contrastive twin generation for every misclassified dev call (hard-negative mining with the LLM).
- Small fine-tuned classifier (e.g. multilingual DeBERTa NLI zero-shot) as a cheap extra check.
- Retrieval of similar past decided calls (case-based reasoning) shown to officers and to the judge.

## ASR / audio
- ROVER-style word voting across several ASR models before the LLM correction.
- Confidence-aware passages: flag passages whose decisive words had low ASR confidence ("may be misheard").
- Speaker-change-aware chunking for long calls; overlap handling.
- Real-voice robustness: the 8 human-recorded calls (ask organizers), our own recordings.

## Product / UX (25% design score)
- Evidence timeline per call (markers by check/family), "why not an alarm" panel.
- Review queue ordered by risk x uncertainty; officer workload estimate per day.
- Natural-language criteria editing with an instant what-if on the dev set ("this change flips 2 calls").
- Per-advisor dashboard (patterns), weekly digest to compliance lead.
- Audit export (PDF/JSON) per decision with provenance for the regulator.

## Operations
- Integration with the bank's call recorder: watch folder / S3 event / SIPREC metadata -> `callguard watch`.
- Model registry + signed configs, offline model mirror, no egress, RBAC, four-eyes on config changes.
- Monitoring: drift in score distributions, review rate, ASR confidence; canary configs.
