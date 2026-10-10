# callguard_results: snapshot of every result we computed (2026-10-10)

Merged from the laptop, the 4070 host (deben) and the A5000 box. No audio, models or caches.
Layout = our `runs/` trees:
- `experiments/<experiment>/summary.{md,json}`, `spec.yaml`; `<variant>/rows.json` (per call: expected, predicted,
  score, CV), `metrics.json`, `meta.json` (config, model ids, cache keys), `results.jsonl.gz` (full per-call results).
- `perturbed/` re-recorded case audio (same calls, paired with the case dev results).
- `test50/` the external held-out set from `data/test50` on main. **Never pool** with the case numbers.
- `recommended/<call>/result.json` the 60 stored case calls as the demo shows them (policy table v3).
- `contrib/`, `candidates/` the factor analysis and the candidate matrix; `evidence_eval/` passage hit rates.
Start with `../docs/FOR_TEAMMATES.md`.
