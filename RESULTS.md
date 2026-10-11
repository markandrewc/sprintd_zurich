# RESULTS

Everything on this page was produced by this branch from the case `.wav` files with the commands in
[`GUIDE.md`](GUIDE.md). Two runs: **all 60 case calls** (2026-10-11 night, the main result) and an earlier
10-call rehearsal. Raw outputs: [`results/overnight-60/`](results/overnight-60/) and
[`results/cleanroom-10/`](results/cleanroom-10/) (one `result.json` per call, the Qwen-only fallback results, stage
timings, the scores; audio is not included).

## Main run: all 60 case calls, batches of 10, two GPUs

**Setup.** The 60 recordings were shuffled with a fixed seed into 6 batches of 10 and copied under neutral names
`n01.wav` … `n60.wav` (`mapping.json`, used only afterwards). Fresh checkout and Python environment on both GPU hosts,
one empty cache per host, `paths.data_dir` pointing at an empty folder. **During the whole run every folder with case
scripts, labels or annotations on both hosts was made unreadable (`chmod 000`)**, so any attempt to read them would have
crashed the run; it did not. Each host ran `scripts/run_batches.sh` (batches back to back, each a normal
`run_testset.sh`: models loaded once per batch): RTX 4070 SUPER 12 GB 3 batches, RTX A5000 24 GB 3 batches.

**What actually ran, per call (read from all 60 `result.json`):** Whisper large-v3 Swiss German on 60/60; 2 speakers
found on 60/60; advisor/customer by Qwen3.8 on 60/60 (no fallback to "first speaker"); reader A Qwen3.8-27B 3-bit and
reader B Kev-4B on 60/60 (no reader failed); Kev masking passages for 199 fired facts (26 more had no single place,
see the Kev section of GUIDE §1); every flagged call has passages, each with a reason and an audio snippet file; Swiss
German display view on 60/60.

**Decisions** (expected = the case's assessment of the original recording, read only for scoring):

| | Sherlock (production) | Qwen3.8 alone (fallback) |
|---|---|---|
| exact (Alarm / Prüfen / Kein Alarm) | **49 / 60 (82%)** | 48 / 60 (80%) |
| false alarms (expected Kein Alarm, flagged) | **0 of 28** | 0 of 28 |
| misses (expected Alarm or Prüfen, Kein Alarm) | 8 of 32 (25%) | 10 of 32 (31%) |
| review cases caught as Prüfen | 5 of 8 | 2 of 8 |
| by level: Stufe 1 / 2 / 3 | 18/20 · 26/32 · 5/8 | |

All 11 wrong calls (Sherlock), with the original recording:

| recording | expected | Sherlock | Qwen alone |
|---|---|---|---|
| Stufe1_D05-K1 / K2 | Alarm | Kein Alarm / Kein Alarm | Prüfen / Prüfen |
| Stufe2_C07-K3 / K4 | Alarm | Kein Alarm / Prüfen | Alarm / Alarm |
| Stufe2_C09-K3 / K4 | Alarm | Kein Alarm / Kein Alarm | Kein Alarm / Kein Alarm |
| Stufe2_C13-K3 / K4 | Alarm | Prüfen / Prüfen | Kein Alarm / Kein Alarm |
| Stufe3_C18-K4 | Prüfen | Kein Alarm | Kein Alarm |
| Stufe3_C19-K3 / K4 | Prüfen | Kein Alarm / Kein Alarm | Kein Alarm / Kein Alarm |

The system never raised a false alarm; its errors are misses, and 3 of the 11 are Alarm calls it sent to Prüfen (a
human still looks at them). «Einigkeit» (a fact counts only when both readers agree) is what makes it cautious: it wins
the Stufe 3 review cases C20 and C18-K3 against Qwen alone, and loses C07 (Qwen alone: Alarm, right) and D05 (Qwen
alone: at least Prüfen), where Kev disagreed.

**Reader combination, what-if on the same 60 stored answers (in-sample; the dashboard's «Advanced» page offers
exactly these settings):**

| fact policy | exact | false alarms | misses | review cases caught |
|---|---|---|---|---|
| **production: both readers band 0.4/0.6, «Einigkeit»** | 82% | 0% | 25% | 5 of 8 |
| Qwen only (same band) | 82% | 0% | 28% | 3 of 8 |
| Kev only | 65% | 7% | 47% | 2 of 8 |
| Qwen decides, Kev as control («Qwen, Kev als Kontrolle») | 87% | 0% | 16% | 6 of 8 |

**Time.** GPU stages of all 60 calls (279.5 min of audio): **3441 s wall clock = 57 s per call** on the two GPUs
(4070: 30 calls in 2581 s; A5000: 30 calls in 3441 s, its Qwen stage is ~1.7x slower than the 4070's). Per batch of 10
on one GPU: 701-951 s on the 4070, 1011-1258 s on the A5000; stages per batch in `timings_*.tsv`. The CPU-only Swiss
German view is meant to overlap the next batch; a PATH bug in `run_batches.sh` (fixed, commit 0bf0e78) skipped it during
the run, so it was run afterwards (430 s / 609 s per host for 30 calls). With the fix, only the last batch's view adds
to the wall clock (~3-4 min), so the whole toolchain is about 1 min per call. A hidden set of 10 calls on both GPUs:
~10-12 min.

**Limits.** In-sample for the rules (README «Honest limits»): this run shows what the code does on the case material
from audio alone, not how it generalises. The fact-policy settings above were compared on the same 60 calls.

## Earlier rehearsal: 10 calls

### Setup

- **Calls:** 10 of the 60 case recordings, drawn with `random.Random(20261011).sample(...)` before anything ran.
  Copied under neutral names `c01.wav` … `c10.wav` (mapping in `results/cleanroom-10/mapping.json`, used only
  afterwards for scoring). 41.6 min of audio.
- **Clean environment:** fresh checkout of this branch on each GPU host, fresh Python environment (`uv sync`), an empty
  cache (`CACHE_DIR`), and no case data next to the code: `paths.data_dir` points at an empty folder in every stage,
  so no label, script or "Sollbewertung" was reachable. Only model files and tool installs (llama.cpp, the Kev environment, Hugging Face cache) were shared with earlier work.
- **Two GPU hosts, started in the same second:** RTX 4070 SUPER 12 GB ("deben") and RTX A5000 24 GB, the calls split
  by audio length weighted with each host's measured speed (`scripts/split_wavs.py --speeds 23.2 34.8`: deben 6 calls /
  24.3 min, A5000 4 calls / 17.3 min).
  Each host ran `scripts/run_testset.sh` (profile `sherlock`, all stages, one model on the GPU at a time).
- **Scoring:** `scripts/score_results.py <run>/sherlock labels.csv` after the run; the labels are the case's expected
  assessments of the original files.

**This was the second run.** A first run (same 10 calls, split 5/5 by equal audio, same clean setup) also decided
10/10 (Qwen alone 8/10) and took 749 s, but it showed a bug in the Kev passages: when a fact is said several times,
masking one window changes nothing and the code then picked the first window of the call ("sinkt von 1.00 auf
1.00"). We fixed that (no Kev passage when no window matters, commit c5212ae) and reran everything from scratch with
the speed-weighted split. `mapping.json` still lists the first run's 5/5 groups; `r2_groups.json` is this run's split.

### Decisions

| | Sherlock (both readers) | Qwen3.8 alone (fallback) |
|---|---|---|
| exact (Alarm / Prüfen / Kein Alarm) | **10 / 10** | 8 / 10 |
| false alarms (flagged but expected Kein Alarm) | 0 of 2 | 0 of 2 |
| misses (expected Alarm or Prüfen, not flagged) | 0 of 8 | 2 of 8 |
| review cases caught as Prüfen | 3 of 3 | 1 of 3 |

| call | original recording | host | audio min | expected | Sherlock | Qwen alone | passages |
|---|---|---|---|---|---|---|---|
| c01 | Stufe1_D02-K2 | 4070 | 2.6 | Alarm | Alarm | Alarm | 3 |
| c02 | Stufe3_C20-K4 | 4070 | 2.6 | Prüfen | Prüfen | Kein Alarm | 5 |
| c03 | Stufe1_D02-K1 | 4070 | 2.6 | Alarm | Alarm | Alarm | 3 |
| c04 | Stufe3_C17-K4 | A5000 | 2.5 | Prüfen | Prüfen | Prüfen | 2 |
| c05 | Stufe2_C06-K4 | 4070 | 9.6 | Alarm | Alarm | Alarm | 4 |
| c06 | Stufe3_C20-K3 | A5000 | 2.6 | Prüfen | Prüfen | Kein Alarm | 4 |
| c07 | Stufe1_D09-K2 | 4070 | 4.2 | Alarm | Alarm | Alarm | 2 |
| c08 | Stufe2_C02-K3 | A5000 | 2.7 | Kein Alarm | Kein Alarm | Kein Alarm | 0 |
| c09 | Stufe2_C01-K4 | 4070 | 2.7 | Kein Alarm | Kein Alarm | Kein Alarm | 0 |
| c10 | Stufe2_C06-K3 | A5000 | 9.6 | Alarm | Alarm | Alarm | 2 |

(K1/K3 = clean recording, K2/K4 = with background noise.)

**Read this with the limits below.** 10 calls are few. The draw hit both recordings of D02, C06 and C20, so these are
7 different dialogues. And the rules were written by the team while reading the case scripts (README «Honest
limits»), so every case call is in-sample for the rules; this run shows that the code reproduces the intended
decisions from audio alone, end to end, not how it does on new calls. The hidden test set is the real test.

### Passages

Every flagged call got passages with a reason; passages of the same moment from both readers are merged.
Qwen3.8 points to segments and writes a German reason; Kev-4B finds a window by masking ("ohne diese Stelle sinkt p(ja)
von X auf Y"); keyword hits are added as light cues. Top passage per flagged call, read by us against the call:

| call | top passage | on the point? |
|---|---|---|
| c01 | 88-99 s, customer: wants the shares before "everyone sees the quarterly figures on Friday" | yes |
| c02 | 0-30 s, opening: two amounts to the same supplier, "receipts not compared yet" | yes (the open question) |
| c03 | 37-52 s, customer: sister in the finance department, unpublished quarterly figures | yes |
| c04 | 20-24 s, customer: "not sure what of this still belongs to the current process" | yes (the open question) |
| c05 | 45-47 s, customer: "it is about CRM systems" | weak: context, not the tip itself (later passages of the call carry it) |
| c06 | 0-38 s, as c02 (same dialogue, clean recording) | yes |
| c07 | 153-183 s, customer: "please do not record that I have to repay the 20,000 francs" | yes |
| c10 | 40-88 s, customer: report about the big order, advisor asks where it was seen | yes |

Passages are 1.7-48.6 s long (median 12.2 s). The transcript is machine-made and has errors (e.g. names and rare words).

### Time

Wall clock from the first `.wav` to the last result, both hosts in parallel, fresh cache: **635 s (10.6 min) for 10 calls
/ 41.6 min of audio.**

| stage (seconds) | RTX 4070 SUPER, 6 calls / 24.3 min | RTX A5000, 4 calls / 17.3 min |
|---|---|---|
| 1 Whisper transcripts | 52 | 52 |
| 2 Qwen3.8 load + roles, reader A, pointing | 5 + 185 | 11 + 212 |
| 3 Kev load + reader B + masking passages | 9 + 307 | 15 + 185 |
| 4 Swiss German display view (CPU) | 73 | 80 |
| total | 634 | 558 |

- The masking passages dominate stage 3 and grow faster than linearly with call length (a 9.6 min call: 130-200 s).
- Projection for the hidden set (~18 calls, ~85 min of audio, same two hosts): about 20-22 min. Faster options, in
  order of cost: `NO_GSW=1` (the Swiss German view is display only, −1.5 min), Kev passages by `evidence_method: anchor`
  (one Kev request per fact instead of one per window), or Qwen's pointing alone (`NO_KEV=1`, which also drops reader
  B: 8/10 instead of 10/10 above).

### Reproduce

```bash
# on each GPU host, after GUIDE.md §3
CACHE_DIR=$PWD/runs/fresh_cache scripts/run_testset.sh /path/to/half NAME
# merge the two run folders' sherlock/ and qwen/sherlock-qwen/ call folders, then
uv run python scripts/score_results.py runs/<merged>/sherlock results/cleanroom-10/labels.csv
```
