# Kev-4B vs our tuned facts (experiments/kev_vs_facts.yaml)

**Question.** Do Kev-4B and/or general questions written without test data generalise better than our tuned facts?
Our fact questions were tuned while reading dev transcripts, and blind paraphrases drop dev AUC from 0.87 to 0.72
(research/findings/RQ10.md). The teammate's prototype (`sprintd_zurich` @ 47c4ffd) works differently: it asks
Kev-4B 15 general, law-based questions and alerts when max p(yes) >= 0.7.

**What is measured.** Everything runs on the dev split, on our large-v3 transcripts and cached roles. The variants
cross the backend (Qwen2.5-7B logprobs vs Kev), the question set (tuned facts vs general) and the text (de vs an
English translation). Kev was trained on English only. There is one ORACLE run (dialect reference scripts), plus
wording probes: blind and paraphrased tables, and paraphrased general questions. The variant list and its reading
guide are at the top of `experiments/kev_vs_facts.yaml`.

## Pieces
| file | what |
|---|---|
| `scripts/remote/serve_kev.py` | Kev as `POST /v1/systemone` + `GET /health` (:8003). Runs in the teammate's venv and reuses their `fraud_analysis.runtime.Kev`. Their own API only has `/analyze`. |
| `src/callguard/llm/kev.py` | HTTP client, LLM type `kev`, no torch. `noul_batch` for the questions check; `choice_probs` makes Kev the probability backend of the unchanged `facts` check. |
| `src/callguard/checks/questions.py` | Check type `questions`. p(yes) per question, family score = max over its questions, so the call score is the max over all questions. On Kev: one request per call plus optional passages by window. On other LLMs: one prompt per question, the same prompt as facts. |
| `src/callguard/llm/pinned.py` | LLM type `pinned`. An offline stand-in with the identity of the vLLM model that made the cached roles and translations, so Kev profiles find them while vLLM is stopped. It refuses every request. |
| `config/general_questions.yaml` (+ `_para`) | The teammate's 15 questions, verbatim, and a blind paraphrase of them. |
| `config/kev.yaml`, `kev-views.yaml`, `kev-oracle.yaml`, `kev-perturbed.yaml`, `recommended-views.yaml` | The profiles. |

**12 GB GPU rule:** Kev (bf16, ~8 GB) and vLLM never run at the same time. ASR transcripts are already cached, so
the work runs in stages:
1. vLLM: translations for the English view.
2. Kev: all `kev_*` variants.
3. vLLM: all `qwen_*` variants and the champion.

## Commands on the GPU host
```bash
cd ~/repos/sprintd && git pull                 # the branch with this work
uv run pytest -q tests/test_kev.py             # offline, ~15 s
uv run callguard experiment experiments/kev_vs_facts.yaml --dry-run
```

### Stage 1: vLLM (Qwen2.5-7B-AWQ) up
```bash
scripts/remote/swap_llm.sh Qwen/Qwen2.5-7B-Instruct-AWQ 0.80 16384      # skip if it already serves this model
# The pinned identity in config/kev.yaml must equal the live one, or cached roles/translations are not found:
uv run python - <<'EOF'
from callguard.config import load_config
from callguard.context import Context
live = Context(load_config("recommended")).llm("default").cache_params()
pin = Context(load_config("kev")).llm("default").cache_params()
print("OK: Kev profiles will find the cached roles and translations" if live == pin else f"MISMATCH\n live {live}\n pin  {pin}")
EOF
# English view of the large-v3 de transcripts (the RQ1 translations came from turbo, so they cannot be reused),
# plus the Qwen English control. ~15 s per call, 48 calls:
uv run callguard experiment experiments/kev_vs_facts.yaml -j 4 --variants qwen_general_en,qwen_general_en_alone
```
On a MISMATCH, set `identity.model` in `config/kev.yaml` to the printed live model.

### Stage 2: Kev up (vLLM stopped)
```bash
kill $(cat runs/logs/vllm.pid); sleep 10; nvidia-smi --query-gpu=memory.used --format=csv   # expect < 1 GB
(cd ~/repos/sprintd_zurich && KEV_DTYPE=bf16 nohup .venv-kev/bin/python ~/repos/sprintd/scripts/remote/serve_kev.py \
   --port 8003 > ~/repos/sprintd/runs/logs/kev.log 2>&1 & echo $! > ~/repos/sprintd/runs/logs/kev.pid)
until curl -sf localhost:8003/health; do sleep 5; done; echo     # first start downloads jaredpalmer/kev-4b (~8 GB)
# smoke test: 2 calls. The log must say "diarize ... (cached)" (and "translate ... (cached)" for _en)
uv run callguard experiment experiments/kev_vs_facts.yaml -v --limit 2 --variants kev_general,kev_general_en 2>&1 \
   | grep -E "diarize|translate|ERROR|Identity" | head
# first look, in this order:
uv run callguard experiment experiments/kev_vs_facts.yaml -j 4 --variants \
   kev_general,kev_general_alone,kev_general_en,kev_general_en_alone,kev_facts,kev_facts_alone,kev_general_oracle,kev_general_oracle_alone
# backend variants + wording robustness on Kev:
uv run callguard experiment experiments/kev_vs_facts.yaml -j 4 --variants \
   kev_facts_choice,kev_facts_band,kev_facts_blind,kev_facts_para,kev_facts_para2,kev_general_para,kev_general_para_alone
# re-recorded audio (only if data_perturbed/v1 exists and experiments/perturbed.yaml ran there):
uv run callguard experiment experiments/kev_perturbed.yaml -j 4 --variants kev_general,kev_general_alone,kev_facts,kev_facts_alone
kill $(cat runs/logs/kev.pid)
```

### Stage 3: vLLM up again
```bash
scripts/remote/swap_llm.sh Qwen/Qwen2.5-7B-Instruct-AWQ 0.80 16384
uv run callguard experiment experiments/kev_vs_facts.yaml -j 6 --variants \
   qwen_general,qwen_general_alone,champion,facts_only,qwen_facts_blind,qwen_facts_para,qwen_facts_para2,qwen_general_para,qwen_general_para_alone
uv run callguard experiment experiments/kev_perturbed.yaml -j 6 --variants perturbed,perturbed_facts_only,qwen_general,qwen_general_alone
```

### Stage 4: tables
```bash
uv run callguard experiment experiments/kev_vs_facts.yaml --rescore     # summary over all variants on disk
uv run callguard leaderboard && uv run callguard report --experiments kev_vs_facts
uv run callguard experiment experiments/kev_perturbed.yaml --rescore    # its runs live under runs/perturbed/
uv run callguard leaderboard --runs-dir runs/perturbed --out research/leaderboard_perturbed.md
```
Results go to `runs/experiments/kev_vs_facts/summary.md`. Commit snapshots to `research/evidence/` and the reading
to a finding (branch `overnight`).

## Reading the results honestly
- **Which to compare.** Use the `*_alone` rows for "which backend / question set". Use the full rows (with the
  keyword and pattern cues) for "what we would ship".
- **Generalisation proxy.** The wording gap per backend: `champion -> qwen_facts_para/para2/blind` vs
  `kev_facts -> kev_facts_para/para2/blind`, and `*_general -> *_general_para`. The general questions avoid the
  tuning problem by construction; their open question is the absolute level.
- **Sample size.** n = 48 calls (24 dialogues, twin groups). Differences of 1-2 calls are noise: quote the CIs.
- **Oracle.** `kev_general_oracle` reads the reference scripts. It is a ceiling and a bridge to the teammate's own
  numbers, never a candidate.
- **Thresholds.** The calibration temperature is one monotone transform for all questions, so it does not change
  AUC. CV thresholds are fitted per fold. The 0.7 / 0.55 thresholds only set the fixed-threshold row.
- **No "unknown" from noul.** `kev_facts` (noul) has no "unknown" mass, so `= unclear` rules only fire in
  `kev_facts_choice` (Kev choice over yes / no / unknown) and `kev_facts_band`.
- **No reasons from Kev.** Kev cannot write text, so the facts evidence step is off for Kev. Its passages and
  reasons come from fact labels only. `kev_general` passages come from the best 8-segment window.
- **Failures.** A dead Kev service or HTTP error never scores 0. The check fails, the call is decided without it
  and the variant shows **DEGRADED**. Experiments abort at start if `GET /health` does not answer or serves another
  model or dtype.

## New calls with Kev (outside the experiment)
Run in stages:
1. `callguard transcribe <wav> -c recommended --no-diarize`, with the GPU free.
2. `callguard run <wavs> -c recommended`, with vLLM up. This caches roles and the champion result.
3. `callguard run <wavs> -c kev`, with Kev up and vLLM stopped.

Without step 2 the pinned stand-in refuses the role request, roles fall back to "first speaker = advisor", the
fallback is flagged as `role_error` and it is not cached.

## Two readers (Qwen + Kev on one fact sheet)
Pre-registered in `research/findings/two_readers_prereg.md`; result in `research/findings/two_readers.md`
(both rules FAIL the acceptance criteria, the champion stays). Fusion plugin `two_readers`
(`src/callguard/fusion/two_readers.py`): rule `labels` (R1, each reader's label, disagreement -> review) or
`facts` (R2, per fact |p_A(yes) - p_B(yes)| > 0.5 -> unclear), plus `a` / `b` (one reader alone).
- Stored runs, no model: `uv run callguard agreement run` joins the finished `kev_vs_facts` variants per wording,
  re-fuses them (`experiments/two_readers.yaml`) and writes `runs/experiments/two_readers/acceptance.md`.
  Re-recorded audio once `kev_perturbed/kev_facts` exists: `uv run callguard agreement run --only perturbed`.
- New calls, one 24 GB card (A5000 / 3090 / 4090): vLLM Qwen2.5-7B-AWQ (~6 GB weights; keep
  `--gpu-memory-utilization` near 0.4 so the KV cache leaves room), Kev bf16 via serve_kev.py (~8 GB) and
  large-v3 fp16 (~4 GB) fit together, so `uv run callguard run <wavs> -c two-readers` runs both readers in one
  pass. Not tested on hardware yet (no 24 GB run so far).
- 12 GB card (4070): Kev and vLLM do not fit together. Run `recommended` (vLLM) and the `kev_facts`-style Kev
  pass in stages, then join the two result sets with `uv run callguard agreement merge <A dir> <B dir> <out dir>`
  and re-fuse with `-c two-readers`-based experiment variants; the profile itself expects both servers up.
