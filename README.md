# callguard

Checks Swiss German bank phone calls for compliance problems: insider trading, disclosing access codes,
disclosure to third parties, concealing documentation, and splitting payments to evade controls.

For every call it

1. transcribes the audio (Swiss German speech -> Standard German text, with word timestamps),
2. separates the speakers and decides who is the advisor and who is the customer,
3. runs several independent, pluggable checks (keywords, number patterns, atomic fact questions with an
   officer-editable policy table, an LLM judge, G-Eval, ...),
4. fuses their scores into **alarm / review / no_alert** with an adjustable threshold,
5. cuts audio snippets of the suspicious passages, each with timestamp and reason,
6. and says when it is unsure: disagreeing or low-confidence checks send the call to **review**
   (a human listens) instead of guessing.

Everything is configured in YAML profiles. Laptop (CPU) and event GPU differ only in config.

## Quickstart

### Recommended profile (GPU host; the config for Sunday)

[`config/recommended.yaml`](config/recommended.yaml), frozen by the overnight research (evidence:
[research/MORNING_REPORT.md](research/MORNING_REPORT.md)): Whisper large-v3 Swiss German
(`gcoli/whisper-large-v3-swiss-german-mit`, MIT, fp16, beam 1) to Standard German text, Qwen2.5-7B-Instruct-AWQ
on vLLM, and the `facts` check deciding (yes/no/unknown fact questions scored by logprob plus the officer-editable
[`config/policy_table.yaml`](config/policy_table.yaml)). Keywords (weight 0.15) and patterns (0.1) stay visible.
Threshold 0.55.

```bash
uv run callguard ui -c recommended          # officer UI on the stored results in runs/recommended/ (no GPU or vLLM needed)
uv run callguard batch -c recommended       # the case calls (transcripts and fact answers are cached)
scripts/run_staged.sh recommended           # new audio on ONE 12 GB GPU: stop vLLM, ASR for all calls, restart vLLM, checks
uv run callguard doctor -c recommended      # check servers, models and CUDA before a long run
```

Whisper large-v3 fp16 (~4 GB) and vLLM with the 7B (~8-9 GB) do not fit on the 12 GB card together, so
`scripts/run_staged.sh [profile] [llm-model] [batch args]` runs in stages. Stage 1 transcribes every call under the
profile's `paths.data_dir` with `scripts/research/asr_sweep.py`. Stage 2 serves the LLM alone and runs
`callguard batch`. Extra args reach stage 2 only, so set a different data dir in the profile, not with `--set`.
A 14B model id (e.g. `Qwen/Qwen2.5-14B-Instruct-AWQ`) gets the 12 GB settings automatically: util 0.90, 6k context,
fp8 KV cache. The demo script is [research/DEMO.md](research/DEMO.md). GPU host setup: [GPU host setup](#gpu-host-setup).

### Laptop (CPU; plumbing only, the 1.5B LLM cannot judge)

```bash
uv sync --all-extras                # faster-whisper, sherpa-onnx, streamlit, llama-cpp-python (CPU wheel), pytest
scripts/download_models.sh local    # ~2 GB into models/ (ASR, diarization, LLM)
scripts/serve_llm_local.sh          # Qwen2.5-1.5B on :8001, own terminal, leave it running
uv run callguard plugins            # what is installed and what the profile uses

A=data_upstream/inventx-case-study/data/Audio      # the case data (paths.data_dir)
uv run callguard run $A/Stufe1_D02-K1.wav          # one call end to end, local profile
uv run callguard batch --clean-only                # 30 clean case calls -> runs/local/<call>/result.json
uv run callguard eval -c fast --split dev          # metrics in seconds once transcripts are cached (dev dialogues)
uv run callguard ui                                # compliance-officer UI on http://localhost:8501
```

No models and no server needed (for UI work): `uv run callguard batch -c demo-offline`, then
`uv run callguard ui -c demo-offline`. Alert links `http://localhost:8501/?call=<call_id>&t=<seconds>`
open a call at that moment.

The UI speaks German to the officer: **Eingang** (inbox; the sidebar threshold re-labels every call
instantly, filters by status / family / level), **Anruf** (evidence timeline: click a marker and the
recording jumps there; per passage the family, the matched criterion from `criteria.yaml`, the supporting
checks with scores, reasons, every view's text side by side and the snippet; "Warum Prüfen?" and
"Warum kein Alarm?" explanations; transcript tab per view), **Stichwörter & Kriterien** (edit, then
re-run the keyword check on all calls in seconds), **Qualität** (dev split with 95% bootstrap CIs,
threshold curve, logged holdout runs), **Experimente** (`runs/experiments/*/summary.json`: variants with
CIs, paired comparisons, flipped calls, report charts). The sidebar **Quelle** switches between profile
runs and experiment variants (`?src=exp:<experiment>/<variant>`, read-only). New pages / detail panels:
one line in `src/callguard/ui/pages_registry.py` / `src/callguard/ui/panels/__init__.py`.

Every command takes `-c <profile|file.yaml>`, repeatable `--set key=value`, `--no-cache` and `-v`.
Other commands: `transcribe AUDIO` (print the diarized transcript) and `watch DIR` (process every new
recording in a folder exactly once).

## How it works

```
 call.wav
    |
    v
 [asr]  faster_whisper | hf_whisper | reference           -> Transcript: segments, words, timestamps,
    |                                                         confidence          cache: .cache/asr
    v
 [diarizer]  sherpa_onnx | none                           -> speaker + advisor/customer role per segment,
    |                                                         segments split at speaker changes
    |                                                                             cache: .cache/diarize
    v
 [check] x N  keywords | patterns | llm_judge | geval | <your module:Class>
    |     each: per family score 0..1, confidence, verdict, findings (segments + reason)
    |     llm_judge, geval and LLM roles call  [llm]  openai_compat | llama_cpp | fake
    |                                                                             cache: .cache/check/<name>
    v
 [fusion]  weighted   -> Decision: alarm | review | no_alert, score, uncertainty, German reasons,
    |                    passages        (never cached; pure, so UI sliders rerun only this step)
    v
 snippets  runs/<profile>/<call>/snippets/NN_<family>_<start>s.wav   (passage +- snippets.pad seconds)
    |
    v
 [sink] x N  json_dir (runs/<profile>/<call>/result.json) | outcept_trigger (POST to the case's trigger API)
```

The words in brackets are the plugin kinds. Every box is picked by `type:` in the profile. The data
model is in `src/callguard/types.py`, the base classes in `src/callguard/plugins.py`, and the chain in
`src/callguard/pipeline.py`. Misconduct "families" come from `config/keywords.json` (the case keyword
list) merged with `config/criteria.yaml` (policy, alarm_when, not_alarm_when, review_when, in German).
The officer edits both files in the UI. Ground truth (`Skript_mit_Sollbewertung`) is read only by the
evaluation and the UI's Quality page, never by the pipeline.

## Profiles

| profile | ASR | diarization / roles | checks | LLM | for |
|---|---|---|---|---|---|
| **`recommended`** | faster-whisper large-v3 Swiss German (gcoli, MIT), fp16, beam 1, CUDA | sherpa-onnx, roles by LLM | facts (w 1.0) + keywords (0.15) + patterns (0.1), `abstain_on_empty`, threshold 0.55 | Qwen2.5-7B-Instruct-AWQ, vLLM :8000 | **the Sunday config** (frozen 2026-10-10 04:09); new audio via `scripts/run_staged.sh` |
| `gpu-12gb` | faster-whisper turbo Swiss German, int8_float16, CUDA | sherpa-onnx, roles by LLM | keywords, patterns, llm_judge, geval (= v1) | Qwen2.5-7B-Instruct-AWQ, vLLM :8000 | v1 baseline on the RTX 4070 host; base of the GPU profiles below |
| `llm-sweep` | as `gpu-12gb` | roles pinned to the cached Qwen2.5-7B decisions | v1 set + geval_cot, facts, anchored, facts_blind (the last four at weight 0, for re-fusion) | whatever vLLM serves (`judge`) | RQ6 LLM comparison; `llm-sweep-oracle` (reference scripts) and `llm-sweep-views` (de + en_from_de) extend it |
| `oracle-gpu` | reference scripts | none | as `gpu-12gb` | vLLM :8000 | ORACLE ceiling on the GPU host; `oracle-views-gpu` adds views ref_gsw / ref_de / ref_en. Never the submission |
| `gpu-views` | views de (turbo), de_large (large-v3 MIT), de_vanilla (vanilla turbo), de_fused (LLM repair of the three), en_from_de, en_speech | sherpa-onnx | as `gpu-12gb` on `de` + weight-0 keyword checks per view | vLLM :8000 | view experiments (RQ1/RQ8). Views do not all fit in VRAM at once: fill the caches in passes (file header). en_speech never ran |
| `synth-oracle` | reference text of `data_synth/v1` | none | v1 set + facts, facts_blind (weight 0) | vLLM :8000 | synthetic out-of-sample stress test (RQ10), split `external` |
| `remote` (**untested**) | remote Whisper server on the GPU host | sherpa-onnx | keywords, patterns, llm_judge, geval | vLLM on the GPU host over Tailscale | laptop app with the models on the GPU host |
| `local` (default) | faster-whisper turbo Swiss German, int8, CPU | sherpa-onnx, roles by LLM | keywords, patterns, llm_judge, geval | Qwen2.5-1.5B Q4, llama.cpp on :8001 | laptop demo |
| `gpu` (**untested**) | faster-whisper large-v3 Swiss German (MIT), fp16, beam 5 | sherpa-onnx, roles by LLM | same; judge with 5 samples at T=0.7 | vLLM on :8000 (Qwen3-30B-A3B) | event GPUs |
| `oracle` | reference scripts (Swiss German text) | none: roles from the script | all four | local LLM | ceiling study: misses from ASR or from the checks? Never for the submission |
| `fast` | local ASR (shares its cache) | none | keywords, patterns | - | whole-dataset eval in seconds, tuning keywords and fusion |
| `demo-offline` | reference scripts | none | all four | `fake` (cue words, deterministic) | UI and plumbing work with zero models (`demo-views` adds an identity "en" view) |

Policy table variants for the `facts` check (`--set checks.2.policy_table=config/<file>`, research only):
`policy_table_blind.yaml` (written from the criteria only, R4), `policy_table_para*.yaml` (reworded questions, R3),
`policy_table_v2.yaml` (stricter access review rule, rejected for the default), `policy_table_v3.yaml` (explicit
"open fact" review questions: an option for a stricter review policy, never run on the holdout).

Profiles `extends:` another file. Dicts merge deeply, lists (such as `checks`) are replaced, and a
plugin block whose `type` changes is replaced whole. `--set` applies after merging:

```bash
--set fusion.threshold=0.45          # THE knob
--set checks.2.samples=3             # list items by index (llm_judge in local.yaml)
--set llms.default.type=fake         # any profile without an LLM server
--set asr.cpu_threads=8              # speed only: not part of the cache key
--set name=fast-oracle               # results go to runs/<name>/ instead of runs/<profile>/
-c fast --set asr.type=reference --set name=fast-oracle   # rule checks on the reference scripts
```

(A type switched by `--set` keeps the old block's keys; the built-in ASR and diarizer plugins ignore
the keys of their sibling types and still raise on real typos.)

## Adding a plugin (3 steps, no registry edit)

1. **Subclass** a base class from `callguard/plugins.py`: `ASRBackend.transcribe`, `Diarizer.diarize`,
   `Check.run`, `Fusion.decide`, `LLM.chat` (+ `choice_probs`), `Sink.emit`. The constructor is
   `__init__(self, ctx, <explicit keyword params>)`. Pass every param to `super().__init__`, so
   `cache_params()` (the cache key) sees them and a typo in the YAML raises.
2. **Put the file on the import path**: the repo root with `PYTHONPATH=.`, or anywhere under `src/`.
3. **Reference it** from a profile as `type: module:Class`. For a short name, add it to
   `registry.BUILTINS` or decorate the class with `@register("check", "pressure")`.

A complete check, `examples/pressure_check.py` (tested in `tests/test_core.py`), flags urgency and
secrecy phrases as weak evidence for chosen families:

```python
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from callguard.plugins import Check
from callguard.types import CheckResult, Family, FamilyScore, Finding, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

CUES = ["sofort", "dringend", "heute noch", "so schnell wie möglich", "niemandem sagen", "unter uns"]


class PressureCheck(Check):
    def __init__(self, ctx: Context, cues: list[str] | None = None, families: list[str] | None = None,
                 per_hit: float = 0.2, confidence: float = 0.3, *, name: str | None = None,
                 weight: float = 1.0, enabled: bool = True):
        super().__init__(ctx, name=name, weight=weight, enabled=enabled, cues=cues, families=families,
                         per_hit=per_hit, confidence=confidence)
        self.patterns = [re.compile(rf"\b{re.escape(c)}\b", re.I) for c in (cues or CUES)]
        self.families = families
        self.per_hit = per_hit
        self.confidence = confidence

    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult:
        hits = [(seg, m.group(0)) for seg in transcript.segments for p in self.patterns
                if (m := p.search(seg.text))]
        result = CheckResult(check=self.name, type=self.plugin_type, meta={"hits": len(hits)})
        for fam in families:
            if not fam.can_alarm or (self.families and fam.id not in self.families):
                continue
            score = 1 - (1 - self.per_hit) ** len(hits)  # noisy-OR: more cues, more pressure
            result.family_scores[fam.id] = FamilyScore(
                score=round(score, 4), confidence=self.confidence,
                reason=f"{len(hits)} Druck-/Geheimhaltungssignal(e)" if hits else "Kein Druck erkennbar",
                segment_ids=[seg.id for seg, _ in hits])
            result.findings += [
                Finding(check=self.name, family=fam.id, score=self.per_hit, segment_ids=[seg.id],
                        start=seg.start, end=seg.end, reason=f"Druck: «{cue}»", detail={"cue": cue})
                for seg, cue in hits]
        return result
```

```yaml
# config/pressure.yaml
extends: local.yaml
checks:                     # lists are replaced: restate the checks you keep
  - {name: keywords, type: keywords, weight: 0.35, fuzzy: 90}
  - {name: patterns, type: patterns, weight: 0.2}
  - {name: llm_judge, type: llm_judge, max_transcript_chars: 16000, weight: 1.0}
  - {name: geval, type: geval, max_transcript_chars: 16000, weight: 1.0}
  - name: pressure
    type: examples.pressure_check:PressureCheck
    weight: 0.2
    families: [trade, splitting]
```

`PYTHONPATH=. uv run callguard run call.wav -c config/pressure.yaml`. The fusion picks the new check
up by name (weight from the YAML, slider in the UI), its findings become passages, and its results
are cached under `.cache/check/pressure`. To develop a check without audio, build a `Transcript`
and call `Pipeline(cfg).process_transcript(t)`. LLM-based checks get their model through
`self.ctx.llm("default")` and should key their cache on criteria + LLM, not on the keyword list (see
`checks/llm_judge.py:LLMCheck`).

## Caching

Each expensive stage is content-addressed (`src/callguard/cache.py`). A stage reruns only when its
own inputs change:

| namespace | key | reruns when |
|---|---|---|
| `.cache/asr` | audio file hash + `asr.cache_params()` | model, language, beam, VAD, prompt change (not thread count) |
| `.cache/diarize` | transcript + audio hash + `diarizer.cache_params()` (incl. the role LLM's model) | ASR output or diarizer/LLM settings change |
| `.cache/check/<name>` | transcript + `check.cache_key(families)` | rule checks: params or keyword list. LLM checks: params, LLM type+model, criteria, `PROMPT_VERSION` (keyword edits do not rerun them) |
| `.cache/geval_steps` | family criteria + LLM | G-Eval evaluation steps, generated once per family |

Fusion and snippets are never cached. Degraded results are not stored, so they are recomputed next
time instead of being served forever: ASR that fell back to plain decoding (`meta.degraded`),
diarization with `meta.diarization.error` (model missing, LLM down), and checks with failed families
(`meta.errors`) or a total failure.

To invalidate: `--no-cache` recomputes everything for one run (no reads, no writes). Delete
`.cache/<namespace>` to rerun one stage. Bump `PROMPT_VERSION` in `checks/prompts.py` (or a plugin
param) after changing a prompt.

## How the label is decided (`fusion: weighted`)

For each family, over the checks that scored it (check weight `w`, the check's own `confidence`):

```
effective weight  e = w * max(confidence, 0.05)
family score        = sum(e * score) / sum(e)
disagreement        = min(1, 2 * weighted std of the scores)
uncertainty         = 0.5 * disagreement + 0.5 * (1 - w-weighted mean confidence)
```

The call score is the highest family that may alarm (`can_alarm: false`, e.g. `numbers`, only
annotates). The rules are checked in this order:

1. score >= `threshold` (0.55) -> **alarm**, or **review** if uncertainty > `max_uncertainty` (0.35)
2. score in [`threshold - review_band`, `threshold`) (band 0.15) -> **review** ("knapp unter Schwelle")
3. a check with weight >= 0.5 says `undetermined` for a family scoring >= `min_score_for_review`
   (0.25) -> **review** ("offener Sachverhalt")
4. uncertainty > `max_uncertainty` and score >= `min_score_for_review` -> **review**
5. otherwise **no_alert**. If every check failed, the label is **review**, never a silent no_alert.

Every rule that fires writes a German sentence with its numbers into `decision.reasons`. Passages are
the findings of families scoring above min(threshold - band, min_score_for_review), merged when
closer than `merge_gap` (3 s). The families that drive the label come first, and at most
`max_passages` (5) are kept. A passage longer than `max_passage_seconds` (60) is cut to a window
around the strongest short evidence inside it (e.g. a keyword hit), with a note naming the full
cited span. Small LLMs sometimes cite minutes of a call. The UI sliders override threshold,
band, max uncertainty, per-check weights and families for the session only. `callguard eval`
suggests a threshold.

## Evaluation

```bash
uv run callguard eval -c fast --split dev                         # rule checks on cached ASR transcripts
uv run callguard eval -c fast --split dev --set asr.type=reference --set name=fast-oracle   # same on the scripts
uv run callguard eval -c oracle --split dev --clean-only           # LLM checks on the scripts (slow on CPU)
uv run callguard eval -c local --split dev --calls Stufe1_D02-K1,Stufe1_D03-K1 # real chain on chosen calls
uv run callguard eval -c <final> --split holdout                   # ONCE per final candidate, logged
```

Comparing variants (what the overnight research used; all cached, so re-runs are cheap):

```bash
uv run callguard splits                                        # the locked holdout + dev folds
uv run callguard experiment experiments/champion.yaml          # every variant on the dev folds, CV thresholds,
                                                               # paired bootstrap CIs + McNemar vs the baseline
uv run callguard experiment experiments/<name>.yaml --dry-run  # what would be computed, which caches exist
uv run callguard leaderboard                                   # all variants (FAR-cap compliant first) -> research/leaderboard.md
uv run callguard report                                        # charts + report.md
uv run callguard asr-eval -c recommended --cached-only         # WER/CER + keyword-spot recall per ASR setup
uv run callguard fusion-cv --kind calibrated -e <exp> --variant <v>   # nested CV for a fitted fusion (built, not run on real results)
```

* `--split` defaults to `dev` (the dev dialogues of the locked `config/splits.yaml`) for `eval`,
  `experiment` and `asr-eval`. `holdout` and `all` include the holdout dialogues, and every such run is
  appended to `runs/holdout_log.jsonl`. Under `all` the threshold suggestion and the CV thresholds are still
  fitted on dev dialogues only. Do not tune on its numbers. Overnight the holdout was looked at twice, both
  logged: the frozen champion and the v1 baseline as a reference.
* Primary metric for comparing systems (research/DECISIONS.md D0): threshold-free **flag AUC** plus the
  cross-validated operating point at false-alarm rate <= 20%. Flag F1 is secondary only, because flagging
  every dev call already scores flag F1 0.70.

* 60 calls = 30 dialogues x (clean, noisy). `data.split_dialogues` assigns **dialogues** to 5 folds,
  stratified by expected label, so the clean and noisy recording of a dialogue are never split.
  `--folds 0,1` evaluates only those folds.
* Headline metrics: "flagged" = alarm or review (a human listens).
  **False-alarm rate** = harmless calls flagged / harmless calls.
  **Miss rate** = calls that should be flagged but came out no_alert / calls that should be flagged.
  Also reported: strict alarm precision/recall/F1, 3-class accuracy, the confusion matrix, a breakdown
  by level and by clean/noisy, whether the top family matches the expected family, and how expected
  review calls were handled.
* Threshold sweep: reruns only the fusion over 0.20..0.90. The suggestion maximises flag-F1 (ties:
  recall, then fewer false alarms) and skips thresholds that flag every call or none.
* `--cv` (on by default): for each fold, the threshold is suggested on the *other* folds and applied to
  the held-out fold. These out-of-fold numbers are the honest ones; 30 dialogues are few.
* Report: `runs/<profile>/eval/report.md` + `report.json`, plus a `result.json` per call for the UI
  (`--no-write-results` skips those). Calls on which a check failed (e.g. LLM server down) are named
  at the top of the report and marked in the per-call table.

## Measured so far

### Overnight on the GPU host (2026-10-10, RTX 4070 12 GB)

Numbers are copied from [research/MORNING_REPORT.md](research/MORNING_REPORT.md). Details are in
`research/journal.md`, `research/findings/RQ*.md` and `research/leaderboard.md`, and runs in
`runs/experiments/*/summary.md`. CIs are 95% paired bootstrap over twin groups. With 24 dev dialogues, small
differences are noise.

**Dev split** (48 calls / 24 dialogues, cross-validated thresholds):

| system | ASR | LLM | flag AUC [95% CI] | CV FAR | CV miss | 3-class acc |
|---|---|---|---|---|---|---|
| v1: kw + patterns + free judge + G-Eval | turbo | 7B | 0.68 [0.53, 0.84] | 86% | 15% | 38% |
| facts (tuned) | turbo | 7B | 0.84 [0.70, 0.95] | 18% | 27% | 73% |
| facts (tuned) | turbo | 14B | 0.87 [0.76, 0.96] | 14% | 23% | 75% |
| facts (blind table, R4) | large-v3 | 14B | 0.85 [0.72, 0.96] | 27% | 12% | 58% |
| **champion = facts + light kw/patterns (`recommended`)** | **large-v3** | **7B** | **0.87 [0.72, 0.99]** | **14%** | **15%** | **79%** |
| facts ORACLE (dialect reference scripts) | none | 14B | 0.90 [0.79, 1.00] | 0% | 23% | 88% |

The champion also has flag F1 0.86, alarm F1 0.86 and review recall 67%. Its labels are identical anywhere
from threshold 0.45 to 0.65.

**Holdout** (run once on the frozen config, 12 calls / 6 dialogues, logged in `runs/holdout_log.jsonl`):

- Champion: **0 false alarms** (6/6 harmless correct), both disclosure alarms caught, alarm F1 0.67, 3-class
  accuracy 67%. It missed the splitting alarm C16 (one version only went to review) and the open
  documentation case C19.
- v1 on the same 12 calls sends *everything* to review: 100% false alarms, 3-class accuracy 17%.
- n = 6 dialogues, so this is a sanity check, not a measurement.

**What drove the gain:**

- Check design matters far more than model size. Facts beat the free judge by +0.16 AUC (real). Qwen2.5-7B,
  Qwen3-8B and Qwen2.5-14B are within ±0.1 of each other, which is not detectable.
- Better ASR helps once the checks are good: 7B facts went from 0.84 to 0.89 with large-v3. Perfect transcripts
  (ORACLE) add only ~0.03.
- ASR keyword-spot recall: large-v3 MIT 84%, Flix 76%, vanilla turbo ~76%, default turbo 71%.
- The 7B reads Standard German ASR output better than perfect dialect text (0.89 vs 0.76).
- No gain from an English view, denoising or 3-way LLM transcript repair. Hybrid check sets add false alarms.

**Caveats:**

- The fact wording was written while reading dev transcripts.
- A table written blind from the criteria only scores 0.77-0.85.
- **Paraphrase test (R3):** rewording the fact questions (same meaning) drops dev AUC from 0.87 to 0.72. The
  drop is real (-0.15 [-0.31, -0.03]) and flips 11/48 labels. The tuned wording is fragile. A realistic
  unseen-call AUC is ~0.72-0.79. A paraphrase ensemble (each fact averaged over several wordings) is being
  tested as the fix.
- Synthetic out-of-sample test (74 fresh twin scripts, mostly written by the judging 14B itself, so there is a
  circularity risk): facts keeps its large false-alarm advantage (14% vs 61%) but misses more (33%), mostly in
  access.
- Open review cases (Stufe3) and the splitting family are the weakest spots everywhere.

### Before the GPU session (2026-10-09, laptop CPU)

Everything in this subsection comes from the artifacts in `runs/` (2026-10-09), before anything ran on a GPU.

**Real chain on the laptop CPU (`local`)**: faster-whisper Swiss German turbo int8, sherpa-onnx
diarization, Qwen2.5-1.5B Q4 via llama.cpp for roles, `llm_judge` and `geval`. The run was stopped by
hand after four calls. Seconds are wall clock, from `transcript.meta` (ASR, diarization) and
`checks[*].meta.seconds` in each `runs/local/<call>/result.json`:

| call (length) | expected | predicted | score / unc. | top family | passages | ASR s (RTF) | diarization s (of it role LLM) | llm_judge s | geval s |
|---|---|---|---|---|---|---|---|---|---|
| Stufe1_D02-K1 (2:33) | alarm, trade | review | 0.89 / 0.43 | trade | 5 | 110 (0.72) | 93 (70) | 165 | 411 |
| Stufe1_D03-K1 (4:50) | no_alert, trade | review | 0.91 / 0.40 | trade | 5 | 289 (0.99) | 58 (35) | 461 | 281 |
| Stufe2_C06-K3 (9:34) | alarm, trade | review | 0.88 / 0.49 | splitting | 5 | 2078 (3.62)¹ | 79 (37) | 206 | 468 |
| Stufe2_C05-K3 (9:33) | no_alert, trade | no_alert² | 0.00 / 0.38 | - | 0 | 408 (0.71) | 101 (47) | failed² | failed² |
| Stufe3_C17-K3 (2:27) | review, access | not finished | | | | 182 (1.24) | | | |

¹ Outlier, probably CPU contention; the other calls ran at 0.7-1.2x realtime.
² In progress when the run was stopped: the LLM server was already down, so both LLM checks failed and
the label rests on keywords and patterns alone. The Inbox and the call page flag this.

Keywords and patterns take under 0.2 s per call. End to end the three finished calls took 13, 18 and 47
minutes (3.8-5.1x their length). Apart from the ASR outlier, most of that is the two LLM checks: about
10-12 minutes per call together, one prompt per family and check.

* **The plumbing works end to end on real audio.** ASR, speaker turns, four checks, fusion, snippets
  with timestamps and German reasons, `result.json`, and the UI (Inbox, Call detail incl. the deep link
  `?call=Stufe1_D02-K1&t=60`, Quality) all run on these results. The D02 keyword passages sit on the
  right moments despite ASR errors: 00:41 «Finanzabteilung … nicht publiziert» (with «Quantalszahlen»
  fuzzy-matched) and 01:30 «vor der Meldung».
* **This is not a quality measurement.** The 1.5B model answered `present` with confidence 1.0 for all
  five families in all three finished calls, with partly invented reasons, and G-Eval scored every
  family 0.40-0.68. So every family fuses to 0.86-0.91 whatever the call says. The calls became review
  only because the keyword check disagrees (uncertainty above 0.35). D03, the harmless twin of D02,
  scored higher than D02. The role answers were rejected in all four calls (they follow the speaker
  labels), so the diarizer fell back to "first speaker is the advisor". Quality numbers come from the
  GPU host (see the overnight results above).

**Rule checks only (`fast`: keywords + patterns, no LLM)**, all 60 calls on the reference scripts
(historical numbers from before the holdout lock; today that run needs `--split all` and is logged as a
holdout look; 5 s and no models with
`callguard eval -c fast --split dev --set asr.type=reference --set name=fast-oracle` on the dev dialogues):

| | false alarms | misses | flagged P / R / F1 | 3-class accuracy |
|---|---|---|---|---|
| threshold 0.55 (default) | 7% (2/28) | 75% (24/32) | 80% / 25% / 0.38 | 53% |
| threshold 0.25 (suggested, in-sample) | 29% (8/28) | 56% (18/32) | 64% / 44% / 0.52 | 53% |
| out-of-fold (5 dialogue folds, threshold chosen per fold) | 29% (8/28) | 62% (20/32) | 60% / 38% / 0.46 | 50% |

At 0.55 the keywords flag 8 of the 12 level-1 calls that should be flagged, none of the 12 on level 2
and none of the 8 level-3 review calls. The two false alarms are both recordings of D03. Clean and noisy
score the same here by construction (one script per dialogue). This is the floor the LLM checks must
beat. On real ASR transcripts only the five calls above exist (`runs/fast/eval/report.md`). Their labels
equal the script-based ones: D02 alarm (right), D03 false alarm, C05 right, C06 and C17 missed.

`runs/oracle/eval` (five calls) is **not** an LLM measurement. The LLM server was already stopped, so
both LLM checks failed on every call. Its report says so at the top; ignore it.

## GPU host setup

The overnight session ran everything on one RTX 4070 (12 GB, driver 535 / CUDA 12.2, Debian 12) inside this repo.
`docs/REMOTE_GPU.md` was never written. These are the facts that made it work (`research/journal.md`, 01:15):

* **vLLM 0.10.1.1 in its own venv `.venv-vllm`** (torch 2.7.1 cu126, transformers 4.55.4; 4.56+ breaks the
  Qwen2 tokenizer in this vLLM). The newest vLLM needs CUDA 13, which driver 535 cannot run. Install:
  `uv venv .venv-vllm --python 3.12 && uv pip install --python .venv-vllm vllm==0.10.1.1 transformers==4.55.4`.
* **cuBLAS 12 + cuDNN 9 for CTranslate2 (faster-whisper) in `.cuda-libs`**, outside `.venv`, because `uv sync`
  would remove them: `uv pip install --target .cuda-libs nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"`. Run
  `source scripts/remote/cuda_env.sh` (sets `LD_LIBRARY_PATH`) before any GPU ASR. `run_staged.sh` does this itself.
* **Models:** `scripts/download_models.sh gpu` puts large-v3 MIT into `models/asr/whisper-large-v3-gsw-ct2`.
  `local` fetches the turbo int8 + diarization models, and `denoise` fetches the optional denoiser.
* **Serving:** `scripts/remote/serve_llm.sh [hf-model-id]` starts vLLM in the background on :8000, always served
  as `callguard-llm`. Env: `GPU_UTIL` (0.70), `MAX_LEN` (16384), `PORT`, `EXTRA`. Logs go to
  `runs/logs/vllm_<model>.log`, and `runs/logs/vllm.log` links the latest. `scripts/remote/swap_llm.sh <hf-model-id>
  [util] [max_len]` stops the running model, starts the new one and waits until it answers. Check caches key on
  the real model id, not the alias. Stop with `kill $(cat runs/logs/vllm.pid)` (by PID, never `pkill -f`).
* **VRAM:** the 7B AWQ at util 0.80 and Whisper large-v3 fp16 do not fit together, so ASR and LLM run in stages
  (`scripts/run_staged.sh`). A 14B AWQ only fits alone and only for `facts` (util 0.90, 6k context, fp8 KV,
  2 sequences). Qwen3-14B does not fit.
* **Speed:** ASR takes 1-2.5 GPU-s per audio minute (turbo: all 60 calls in ~3 min). `facts` with the 7B takes
  ~2-8 s per call, and the 14B ~25 s. Sizing: `docs/OPERATING_CONCEPT.md` §8.
* The laptop-over-Tailscale profile `config/remote.yaml` is **untested**. Its header refers to
  `scripts/remote/serve_models.sh` / `tunnel.sh`, which do not exist. Serve the LLM with `serve_llm.sh` and the
  ASR with `uv run python -m callguard.serve.asr_server -c <profile> --port 8010` (not started overnight).

## Roadmap: where the next ideas plug in

* **Synthetic phone calls.** Generate scripts with an LLM per family, each with a harmless twin (the
  case pairs them, e.g. D02 insider purchase vs. D03 the same terms only explained, C06 vs. C05),
  then TTS, then telephone augmentation (8 kHz band limit, codec, noise). Write them in the case
  layout (`Audio/`, `Transkript/`, `Skript_mit_Sollbewertung/`, parsed by `callguard.data`) and
  point `paths.data_dir` at them; `eval` works unchanged. For check development, skip audio: build a
  `Transcript` from the script and call `Pipeline.process_transcript(t)` (what the oracle path does).
* **Swiss German ASR fine-tuning.** `data.load_calls()` yields each call's audio and reference turns.
  Note that the scripts are dialect text, while the ASR models output Standard German. Public corpora:
  SPC, SDS-200, STT4SG-350, SwissDial (SwissDial is CC BY-NC). Register the checkpoint
  either as `asr: {type: hf_whisper, model: <dir or repo>}` (**untested**, needs
  `uv pip install transformers torch accelerate`) or convert it with `ct2-transformers-converter
  --model <dir> --output_dir models/asr/<name> --quantization int8 --copy_files tokenizer.json
  preprocessor_config.json` for `faster_whisper`. Compare with `callguard eval --split dev` against the
  `oracle` ceiling.
* **Learned fusion.** Write a `Fusion` plugin (`type: my_module:LearnedFusion`) whose `decide()` maps
  per-check family scores and confidences to a label. Fit it on cached `CheckResult`s
  (`eval.load_results(runs/<profile>)` or `eval.evaluate(...)`) with `data.split_dialogues` folds.
  With 30 dialogues keep it small (per-check weights, Platt scaling) and compare out-of-fold against
  `weighted` with `--cv`.
* **GPU profile.** `scripts/download_models.sh gpu`, `scripts/serve_vllm.sh` (model choice by GPU
  memory in its comments), then `-c gpu`. **Not run yet**: expect to adjust `llms.default.model`
  to the served name and check that `json_mode: json_schema` and logprobs work on the vLLM version.
  The LLM prompts put the transcript first, so vLLM prefix caching shares it across all family calls
  (llama.cpp already reuses it on the laptop). For a 12 GB card see [GPU host setup](#gpu-host-setup).

## Development

```bash
uv run pytest -q -m "not slow"     # offline suite, ~30 s
uv run pytest -q -m slow           # needs models, case audio and the live LLM server (minutes)
```

Code map: `src/callguard/{types,plugins,registry,config,context,pipeline,cache,audio,families,data}.py`
(core), `asr/`, `diarization/`, `checks/`, `llm/`, `fusion/`, `sinks/`, `eval.py`, `cli.py`, `ui/`.
Scripts: `scripts/download_models.sh`, `scripts/serve_llm_local.sh`, `scripts/serve_vllm.sh`,
`scripts/run_staged.sh`, `scripts/remote/{cuda_env,serve_llm,swap_llm}.sh`, `scripts/research/` (overnight helpers).

## Known limits

* The local Qwen2.5-1.5B cannot judge these calls: it says `present` for every family, its G-Eval
  distributions are nearly flat, and its role answers get rejected (the diarizer then falls back to
  "first speaker is the advisor", right for all case calls). See [Measured so far](#measured-so-far).
  The laptop validates the plumbing only.
* A check that fails (e.g. LLM server down) is left out of the fusion with a note. The call is still
  decided on the remaining checks and can come out no_alert. The Inbox, the call page and the eval
  report name such calls; process them again once the check works.
* `hf_whisper`, the `gpu` profile (30B-class LLM for event GPUs) and `remote` are untested. `gpu-12gb`,
  `recommended` and the research profiles ran on the RTX 4070 host.
* Licences: the local ASR's tokenizer comes from a CC-BY-NC fine-tune (Flurin17). The `gpu` ASR model
  is MIT (see `scripts/download_models.sh`).
* `oracle` and `demo-offline` read the reference scripts as the transcript. They exist for ceiling
  studies and UI work. The case forbids feeding scripts or labels into the audio pipeline, and the
  audio profiles never do.
