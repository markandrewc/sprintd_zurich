# Dual-reader facts: pre-registration (2026-10-10 ~15:50, before any dual-reader fact result exists)

**Design.** Qwen2.5-7B (check `facts`) and Kev-4B (check `facts_kev`) both answer every fact of the active table
(v3) for the 60 case calls (runs/dual-facts) and the 100 test50 calls (runs/test50/dual-facts). A fact's value
(ja / nein / unklar) is resolved per reader, then combined; the officer's rules (unchanged, table v3) decide.

**Fixed defaults (chosen a priori, not tuned):**
- Qwen: three-way as today (ja if p(ja) >= 0.5, nein if p(nein) >= 0.5, else unklar).
- Kev: band on p(yes): ja if >= 0.7, nein if <= 0.3, else unklar.
- Combination "Einigkeit": both ja -> ja; both nein -> nein; anything else -> unklar (so the review rules fire).
**Read-outs:** dev (48 calls, CV threshold as usual) and test50 (100 calls, fixed threshold, one look, never
pooled with dev): flag AUC, false alarms, misses, 3-class accuracy, review recall; vs champion v3 (Qwen alone).
A small grid of bands / combination modes is reported on DEV ONLY, for the officer UI; the default above stays
unless the team decides otherwise, and test50 is evaluated only for the defaults (look logged in test50_prereg.md).
