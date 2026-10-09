# Leaderboard

Generated 2026-10-10 01:25 by `callguard leaderboard` from runs/experiments/*/summary.json. Sorted by out-of-fold (CV) flag F1 (threshold chosen on the other dev folds). Brackets: 95% bootstrap CI over dialogues; overlapping CIs = no detectable difference. FAR above the 20% cap is marked (!). ORACLE rows read the reference scripts and are never submission candidates; DEGRADED rows had failed checks.

| # | experiment / variant | split | n | CV flag F1 [95% CI] | FAR | miss | review recall | alarm F1 | acc | check s/call | LLM calls/call | commit | tags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | smoke / **rules_only** | dev | 48 | 0.52 [0.24, 0.73] | 36% (!) | 54% | 0% | 0.53 | 50% | 0.0 | 0.0 | 8e00d1ef66* | ORACLE |
| 2 | smoke / **all** | dev | 48 | 0.48 [0.20, 0.72] | 27% (!) | 62% | 0% | 0.31 | 42% | 0.1 | 10.0 | 8e00d1ef66* | ORACLE |
| 3 | smoke / **all_t040** | dev | 48 | 0.48 [0.20, 0.72] | 27% (!) | 62% | 0% | 0.31 | 42% | 0.1 | 10.0 | 8e00d1ef66* | ORACLE, re-fusion of all |

`*` = uncommitted changes in the tree when the variant ran.
