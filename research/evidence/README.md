# Evidence snapshot (copied 2026-10-10 06:10 from the gitignored `runs/` directory)

The reports cite `runs/experiments/<name>/summary.md`, `runs/asr_eval/<tag>/summary.md` and `runs/holdout_log.jsonl`.
`runs/` is never committed (large, machine-specific), so the summaries are copied here verbatim:

| cited path | copy in this folder |
|---|---|
| `runs/experiments/<name>/summary.md` | `experiments/<name>.md` |
| `runs/asr_eval/<tag>/summary.md` | `asr_eval/<tag>.md` |
| `runs/view_eval/<tag>/summary.md` | `view_eval_<tag>.md` |
| `runs/holdout_log.jsonl` (3 logged holdout looks) | `holdout_log.jsonl` |
| `runs/logs/e2e_new.log` (end-to-end test on new audio) | `e2e_new_audio.log` |
| `runs/evidence_eval/evidence.md` (`callguard evidence-eval`, 2026-10-10 12:14) | `evidence_eval.md` |

Note: the champion's holdout run wrote into the dev experiment folder; its holdout rows live in
`runs/experiments/champion_holdout/` on the GPU host and the metrics are in `holdout_log.jsonl`.
Regenerate everything on the GPU host with `uv run callguard experiment experiments/<name>.yaml --rescore`.
