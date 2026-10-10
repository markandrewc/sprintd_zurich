"""Learning from what the officers decide (docs/LEARNING.md).

Every officer judgement (call verdict, passage, fact, missed category; ``callguard.feedback``) is a
label. This package turns the stored labels into something the system can learn from, safely:

* :mod:`~callguard.learning.hygiene`   which call may be used for what (case calls: evaluation only;
  new calls: train / shadow test by twin group), enforced and checked on every export.
* :mod:`~callguard.learning.records`   labels per call, per passage and per fact (officer feedback plus
  the answers given in the "Offene Fakten" panel), latest judgement wins.
* :mod:`~callguard.learning.export`    ``callguard learn export``: Kev / Qwen-LoRA fact records, call
  labels for calibration, passage labels for localisation, with a manifest.
* :mod:`~callguard.learning.insights`  counts, officer-vs-system confusion, most-corrected facts / rules,
  readiness of each learning step (honest thresholds).
* :mod:`~callguard.learning.recalibrate`  the one learning step that works now: the decision threshold,
  re-fitted with dialogue-fold cross-validation, effect as a paired bootstrap CI.
* :mod:`~callguard.learning.proposals`  propose -> four-eyes approve / reject -> rollback, audit-logged;
  nothing is ever applied automatically.
* :mod:`~callguard.learning.demo`      simulated officer feedback for the dev calls (demo store only).

Nothing here trains or runs a model: fine-tuning is a roadmap step with a shadow-evaluation contract
(``finetune/README.md``).
"""
