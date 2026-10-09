# Leaderboard

Generated 2026-10-10 01:46 by `callguard leaderboard` from runs/experiments/*/summary.json. Sorted by out-of-fold (CV) flag F1 (threshold chosen on the other dev folds). Brackets: 95% bootstrap CI over dialogues; overlapping CIs = no detectable difference. FAR above the 20% cap is marked (!). ORACLE rows read the reference scripts and are never submission candidates; DEGRADED rows had failed checks.

| # | experiment / variant | split | n | CV flag F1 [95% CI] | FAR | miss | review recall | alarm F1 | acc | check s/call | LLM calls/call | commit | tags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | checks_ablation / **llm_only** | dev | 48 | 0.70 [0.54, 0.83] | 68% (!) | 15% | 33% | 0.70 | 50% | 31.8 | 10.0 | e1954e9ab6* | re-fusion of all |
| 2 | checks_ablation / **all_minus_keywords** | dev | 48 | 0.69 [0.54, 0.81] | 73% (!) | 15% | 33% | 0.64 | 46% | 31.8 | 10.0 | e1954e9ab6* | re-fusion of all |
| 3 | checks_ablation / **kw_pat_judge** | dev | 48 | 0.69 [0.53, 0.81] | 91% (!) | 8% | 83% | 0.44 | 27% | 15.6 | 5.0 | e1954e9ab6* | re-fusion of all |
| 4 | checks_ablation / **all_minus_geval** | dev | 48 | 0.69 [0.53, 0.81] | 91% (!) | 8% | 83% | 0.44 | 27% | 15.6 | 5.0 | e1954e9ab6* | re-fusion of all |
| 5 | checks_ablation / **all** | dev | 48 | 0.67 [0.46, 0.83] | 45% (!) | 31% | 67% | 0.55 | 50% | 31.8 | 10.0 | e1954e9ab6* |  |
| 6 | checks_ablation / **all_minus_patterns** | dev | 48 | 0.66 [0.48, 0.80] | 68% (!) | 23% | 33% | 0.63 | 44% | 31.8 | 10.0 | e1954e9ab6* | re-fusion of all |
| 7 | smoke / **rules_only** | dev | 48 | 0.52 [0.24, 0.73] | 36% (!) | 54% | 0% | 0.53 | 50% | 0.0 | 0.0 | 8e00d1ef66* | ORACLE |
| 8 | smoke / **all** | dev | 48 | 0.48 [0.20, 0.72] | 27% (!) | 62% | 0% | 0.31 | 42% | 0.1 | 10.0 | 8e00d1ef66* | ORACLE |
| 9 | smoke / **all_t040** | dev | 48 | 0.48 [0.20, 0.72] | 27% (!) | 62% | 0% | 0.31 | 42% | 0.1 | 10.0 | 8e00d1ef66* | ORACLE, re-fusion of all |
| 10 | checks_ablation / **keywords** | dev | 48 | 0.47 [0.20, 0.71] | 32% (!) | 62% | 0% | 0.50 | 50% | 0.0 | 0.0 | e1954e9ab6* | re-fusion of all |
| 11 | checks_ablation / **kw_patterns** | dev | 48 | 0.37 [0.07, 0.61] | 23% (!) | 73% | 0% | 0.34 | 46% | 0.0 | 0.0 | e1954e9ab6* | re-fusion of all |
| 12 | checks_ablation / **kw_pat_geval** | dev | 48 | 0.36 [0.09, 0.62] | 5% | 77% | 0% | 0.33 | 52% | 16.3 | 5.0 | e1954e9ab6* | re-fusion of all |
| 13 | checks_ablation / **all_minus_llm_judge** | dev | 48 | 0.36 [0.09, 0.62] | 5% | 77% | 0% | 0.33 | 52% | 16.3 | 5.0 | e1954e9ab6* | re-fusion of all |

`*` = uncommitted changes in the tree when the variant ran.
