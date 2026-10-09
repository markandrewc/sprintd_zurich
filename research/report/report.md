# callguard research report

Generated 2026-10-10 01:25 by `callguard report` from 1 experiment(s). Primary numbers are out-of-fold (CV) on the dev split; whiskers and brackets are 95% bootstrap CIs over dialogues (clean+noisy resampled together). With ~24 dev dialogues, differences inside the CIs are noise.

## Top variants

| # | experiment / variant | split | n | CV flag F1 [95% CI] | FAR | miss | review recall | alarm F1 | acc | check s/call | LLM calls/call | commit | tags |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | smoke / **rules_only** | dev | 48 | 0.52 [0.24, 0.73] | 36% (!) | 54% | 0% | 0.53 | 50% | 0.0 | 0.0 | 8e00d1ef66* | ORACLE |
| 2 | smoke / **all** | dev | 48 | 0.48 [0.20, 0.72] | 27% (!) | 62% | 0% | 0.31 | 42% | 0.1 | 10.0 | 8e00d1ef66* | ORACLE |
| 3 | smoke / **all_t040** | dev | 48 | 0.48 [0.20, 0.72] | 27% (!) | 62% | 0% | 0.31 | 42% | 0.1 | 10.0 | 8e00d1ef66* | ORACLE, re-fusion of all |

`*` = uncommitted changes in the tree when the variant ran.

## smoke

Plumbing check on demo-offline (reference scripts + fake LLM); numbers are meaningless.

RQ: - · split dev · baseline `all` · details: `runs/experiments/smoke/summary.md`

![chart_metrics](smoke/metrics.png)

![chart_cost](smoke/cost_vs_f1.png)

![chart_noise](smoke/clean_vs_noisy.png)

![chart_levels](smoke/levels.png)

![chart_thresholds](smoke/thresholds.png)

- `rules_only` vs `all`: flag F1 +0.05 [+0.00, +0.16] (no detectable difference); FAR +9pp; McNemar p=1.0; 12 calls flip
- `all_t040` vs `all`: flag F1 +0.00 [+0.00, +0.00] (no detectable difference); FAR +0pp; McNemar p=1.0; 0 calls flip

