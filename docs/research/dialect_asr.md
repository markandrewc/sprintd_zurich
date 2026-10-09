# Dialect ASR, Swiss German fine-tunes, local LLMs, embeddings, audio LLMs, denoisers

Research note, 2026-10-10. Hardware: RTX 4070 12 GB, driver 535 (CUDA 12.2). Inference stacks: vLLM 0.10.1.1
(torch 2.7.1 cu126, transformers 4.55) in its own venv; app env has faster-whisper 1.2.1, ctranslate2 4.8.2,
sherpa-onnx 1.13.8, numpy 2.x and **no torch**. No HF token, so gated repos are out (`gated: auto` is out too:
it still needs a logged-in token).

**What "verified" means here:** the repo was queried today via the HF API or page (it exists, is not gated,
licence, file list, sizes). For vLLM support, the architecture was looked up in the `registry.py` of the
`v0.10.1.1` tag. Nothing below was run on our audio. Quality numbers are the authors' own claims. VRAM figures
are estimates: weights from file sizes, KV cache = 2 x layers x kv_heads x head_dim x 2 bytes per token, from
each `config.json`.

---

## TL;DR

- **No public model outputs Swiss German dialect spelling.** Every Swiss German Whisper fine-tune on HF
  writes Standard German. The `gsw` view needs our own fine-tune (see `whisper_finetune_12gb.md` 6.1). One
  untested fallback: a character-level CTC model (Omnilingual ASR) that writes roughly what it hears.
- Best Standard German candidates: `gcoli/whisper-large-v3-swiss-german-mit` (already downloaded, CT2 in
  `ct2/`) and `malaxy/flix-swissgerman-ct2` (Flix full fine-tune, CT2 conversion, ready for faster-whisper).
- **Bug in our local model folder:** `models/asr/turbo-gsw-ct2-fp16` (the jayr23 conversion) has no
  `preprocessor_config.json` and no `tokenizer.json`. faster-whisper then falls back to 80 mel bins (turbo needs
  128) and fetches the `openai/whisper-tiny` tokenizer from the Hub. In large-v3 the special-token ids are
  shifted by one (`<|yue|>`). Fix: copy both files from `models/asr/vanilla-turbo-ct2/`, or use
  `OSTswiss/whisper-large-v3-turbo-swiss-german-ct2` instead (same weights, complete files).
- Turbo models cannot translate (OpenAI says so). For `en_speech`, use stock large-v3
  (`models/asr/vanilla-large-v3-ct2` = `Systran/faster-whisper-large-v3`) with `task="translate", language="de"`.
- LLM judge: `Qwen/Qwen2.5-7B-Instruct-AWQ` (already cached) is the safe default.
  `Qwen/Qwen3-8B-AWQ` with thinking off is the main challenger. `Qwen/Qwen3-4B-Instruct-2507-FP8` is the one
  that runs next to Whisper. **Apertus does not load in vLLM 0.10.1.1** (support was added in 0.10.2).
- Denoiser: use **sherpa-onnx, already installed**. `OfflineSpeechDenoiser` takes DPDFNet (a DeepFilterNet2
  derivative, 16 kHz) or GTCRN ONNX models, with no torch. The `deepfilternet` pip package needs numpy<2 and old
  torchaudio APIs, so skip it. Its Rust `deep-filter` binary is a no-dependency alternative.

---

## 1. ASR that outputs Swiss German dialect text

Searched the HF API (`swiss-german`, `swissgerman`, `swiss_german`, `schweizerdeutsch`, `swissdial`, `stt4sg`,
`gsw`, `archimob`, `alemannic`, the i4ds / ZurichNLP / FHNW / ZHAW authors) and the web. Two web searches
turned up no released model with dialect-orthography output. The Flix paper (arXiv 2606.07608) also says
earlier SOTA Swiss German models were never released or were withdrawn. STT4SG-350 and SPC only have Standard
German targets. SwissDial has dialect text, but no model trained on it to *output dialect* is public.

| id | output | arch | licence | verified | notes |
|---|---|---|---|---|---|
| (none found) | dialect | - | - | yes (negative) | Train our own: `whisper_finetune_12gb.md` 6.1 (separate LoRA + CT2 folder, score with CER). |
| `kuma-rtin/whisper_swissdial-spc` | Standard German | whisper-base + qLoRA adapter (5 MB) | Apache-2.0 | yes | Trained on SwissDial + SPC but as gsw->de **translation**. BLEU 40 SPC / 31 ASGD-ZH. Tiny base model, not useful. |
| `matildecs/whisper-large-stt4sg` | Standard German (STT4SG targets are de) | whisper-large-v2, transformers fp32 6.2 GB | Apache-2.0 tag (STT4SG data licence is restrictive) | yes | Card claims WER 15.5 on an unnamed eval set. No CT2 version. Low priority. |
| `Vgillioz/wav2vec2-xls-r-1b-swissdial`, `leuef3/*archimob*`, `scasutt/wav2vec2-large-xlsr-52_Swiss_German` | ? | wav2vec2 | - | yes | Empty repos or WER 1.0 / toy runs. Ignore. |
| Omnilingual ASR `omniASR_CTC_1B_v2` (Meta) | characters as heard (no LM), so plausibly a dialect-like phonetic spelling | wav2vec2 CTC, 975M | Apache-2.0 (code + models) | partly: README + language list read | **Untested idea for `gsw`.** Language list has `deu_Latn` and `als_Latn`; `als` in ISO 639-3 is Tosk Albanian, so it is **not** Swiss German. There is no `gsw_Latn`. A CTC model has no language model pulling it toward Standard German, so its output may follow the dialect sounds. Run: separate venv, `pip install omnilingual-asr` (needs fairseq2 0.5-0.6 + a matching fairseq2n/torch wheel, Python <3.14). `ASRInferencePipeline(model_card="omniASR_CTC_1B_v2").transcribe([wav], batch_size=1)`. About 3 GB VRAM, very fast. CTC models take <=40 s segments, so feed diarized turns. Weights: dl.fbaipublicfiles.com (no HF token needed). Also ONNX via sherpa-onnx: `csukuangfj/sherpa-onnx-omnilingual-asr-1600-languages-1B-ctc-int8-v2-...` (would run in the app env, CPU). |

**Practical fallback for the `gsw` view without training:** the reference-script-based `ref_gsw` is oracle only
(rule 2). So the realistic options are (a) our LoRA fine-tune on the dev-fold scripts, (b) the Omnilingual
CTC experiment above, or (c) an LLM "back-translation" de -> gsw, which is a text view, not ASR.

---

## 2. Swiss German -> Standard German fine-tunes (CT2 availability)

All of these write **Standard German** (with `language="de", task="transcribe"`). ASGDTS = FHNW All Swiss
German Dialects Test Set (5750 clips). The numbers come from different papers and normalisations, so they are
not strictly comparable.

| id | base / type | licence | size | CT2 files? | quality claim | verified | notes |
|---|---|---|---|---|---|---|---|
| `gcoli/whisper-large-v3-swiss-german-mit` | large-v3, LoRA merged | MIT (data: i4ds SPC, MIT) | 3.1 GB fp16 | **yes**, `ct2/` subfolder with model.bin+tokenizer.json+preprocessor_config.json | ASGDTS WER 22.1 dev / 24.7 final (base large-v3: 24.0 / 26.3) | yes | Already local (`models/asr/whisper-large-v3-gsw-ct2`). Card: **set `condition_on_previous_text=False`** on long files (otherwise +2.5..11.7 WER and hallucinated text). VAD did not help them. |
| `gcoli/whisper-large-v3-turbo-swiss-german-mit` | turbo, LoRA merged | MIT | 1.6 GB | **yes**, `ct2/` | ASGDTS 23.7 / 25.9 (base turbo 26.5 / 28.5) | yes | The clean-licence turbo. 2.4x faster than the large variant. |
| `Flix-AI/flix-swissgerman-full` | large-v3 **full** FT, 1367 h (SRF subtitles, SPC, YouTube, film) | Apache-2.0 | 3.1 GB safetensors (transformers only) | no (transformers) | ASGDTS WER 25.6, cWER 13.8 (their baseline large-v3 28.56). Paper arXiv 2606.07608 | yes | Their WER uses a stricter normalisation than gcoli's, so 25.6 is not worse than gcoli's 24.7 in any meaningful sense. Training data is broadcast-heavy, which may suit conversational speech better than parliament-only. |
| `malaxy/flix-swissgerman-ct2` | CT2 conversion of the above (rev a9c347a), fp16 | Apache-2.0 | 3.1 GB | **yes**: model.bin, tokenizer.json, preprocessor_config.json, vocabulary.json | as above | yes | Created 2026-10-08. `WhisperModel("malaxy/flix-swissgerman-ct2", device="cuda", compute_type="float16")`. Lets us test Flix with no torch. **Top new candidate for queue item A3.** |
| `Flix-AI/flix-swissgerman-lora` | LoRA adapter for large-v3 | Apache-2.0 | 1.15 GB | no | cWER 13.9 | yes | Only useful as a starting point for our own fine-tune. |
| `Flurin17/whisper-large-v3-turbo-swiss-german` | turbo, 301 h private data (2026-03-20 retrain) | **CC BY-NC 4.0** | 1.6 GB | no | WER 38.0 on a private val split | yes | Origin of our current default. |
| `nebi/whisper-large-v3-turbo-swiss-german-ct2-int8` | CT2 int8 of Flurin17 | tagged Apache-2.0, but **inherits CC BY-NC** | 0.8 GB | model.bin + preprocessor_config; **no tokenizer.json** upstream (our local copy has one added) | - | yes | Converted 2025-08-24, so it **predates Flurin17's 2026-03 retrain** (older weights). |
| `jayr23/whisper-large-v3-turbo-swiss-german-ct2` | CT2 fp16 of Flurin17 (2026-04-02) | tagged Apache-2.0, inherits CC BY-NC | 1.6 GB | **missing preprocessor_config.json and tokenizer.json** | - | yes | See the bug in the TL;DR. Copy both files from `vanilla-turbo-ct2`. |
| `OSTswiss/whisper-large-v3-turbo-swiss-german-ct2` | CT2 fp16 of Flurin17 (2026-08-10) | CC BY-NC 4.0 (correctly declared) | 1.6 GB | **complete** (model.bin, tokenizer.json, preprocessor_config.json, vocabulary.json) | - | yes | Clean drop-in replacement for jayr23. |
| `PhilippeFuhrioso/whisper-large-v3-swiss-german-spc` | large-v3 on SPC | none stated | 6.2 GB fp32 transformers | no | - | yes | No licence. Skip. |
| `apexAI-Switzerland/whisper-large-v3-swissgerman` | large-v3 | none | 6.2 GB | no | - | yes | `gated: auto`, so out for us. |
| `nizarmichaud/whisper-large-v3-turbo-swissgerman` | turbo ("Michaud 17.5 %") | MIT | - | - | - | yes | **No weight files in the repo.** Flix says it was withdrawn and its benchmark is contaminated. |
| i4ds / ZHAW models | - | - | - | - | - | yes (negative) | No public ASR models under `i4ds`. ZHAW has none on HF. |

How to run any CT2 entry (app env):
```python
from faster_whisper import WhisperModel
m = WhisperModel("<dir or repo>", device="cuda", compute_type="float16")   # int8_float16 to save VRAM
segs, info = m.transcribe(wav, language="de", task="transcribe", beam_size=5,
                          condition_on_previous_text=False, word_timestamps=True)
```
For gcoli, use `snapshot_download(repo, allow_patterns="ct2/*")` and point at `<path>/ct2`. Converting Flix
yourself (needs transformers + torch on the GPU host):
`ct2-transformers-converter --model Flix-AI/flix-swissgerman-full --output_dir flix-ct2 --copy_files tokenizer.json preprocessor_config.json --quantization float16`.

**Suggested A3 order:** gcoli-large (already local), malaxy/flix-ct2 (new), gcoli-turbo, OSTswiss-turbo,
vs the current nebi int8. Use the same decode settings and `condition_on_previous_text=False` everywhere.

---

## 3. Speech -> English (`en_speech`): turbo cannot translate

- **Confirmed.** The openai/whisper README: "the `turbo` model is not trained for translation tasks. If you
  need to translate non-English speech into English, use one of the multilingual models (tiny, base, small,
  medium, large) instead of turbo." So every turbo model (vanilla, nebi, jayr23, OSTswiss, gcoli-turbo) is
  out for `task="translate"`.
- **Use** `Systran/faster-whisper-large-v3` (MIT, 3.1 GB, complete CT2 files; already local as
  `models/asr/vanilla-large-v3-ct2`):
  `m.transcribe(wav, language="de", task="translate", beam_size=5, condition_on_previous_text=False)`.
  Force `language="de"`: Swiss German is not a Whisper language, and auto-detection may choose something odd.
- Fallback for an A/B test: `Systran/faster-whisper-large-v2` (MIT, 3.1 GB, verified). Some users say v2
  translates better than v3, but a web search found **no evidence** for it, so this is unverified.
- `gcoli/whisper-large-v3-swiss-german-mit` with `task="translate"`: the LoRA was trained on transcription
  only. Translation ability probably survives partly, but this is **unverified**. Worth one run, because its
  encoder handles dialect better.
- VRAM: large-v3 fp16 about 4.5 GB, int8_float16 about 3 GB (from the translation.md estimates).

---

## 4. LLMs on vLLM 0.10.1.1 (~8 GB budget: weights + KV at 16k + ~0.7 GB activations/graphs)

The architecture check is against `vllm/model_executor/models/registry.py@v0.10.1.1`. Qwen2, Qwen3, Mistral,
Llama, Phi3 and Gemma3(ForConditionalGeneration) are present. **ApertusForCausalLM is absent** (added in
v0.10.2). On Ada (sm_89), AWQ checkpoints are auto-promoted to the `awq_marlin` kernel, and FP8 (W8A8) works
natively. Sizes are the safetensors totals from the HF API (GB = 1e9).

| id | licence | weights | KV/token | KV @16k (bf16) | fits 8 GB? | verified | notes |
|---|---|---|---|---|---|---|---|
| `Qwen/Qwen2.5-7B-Instruct-AWQ` | Apache-2.0 | 5.57 GB | 56 KiB (4 KV heads) | 0.88 GiB | **yes, ~7.2 GiB** | yes, already in HF cache | Very cheap KV. Mature JSON/guided decoding. Good German. max_pos 32k. |
| `Qwen/Qwen3-8B-AWQ` | Apache-2.0 | 6.10 GB | 144 KiB | 2.25 GiB | ~8.6 GiB bf16 KV; **~7.5 GiB with `--kv-cache-dtype fp8`** or 12k ctx | yes | Stronger reasoning than 2.5-7B. Thinking off per request: `extra_body={"chat_template_kwargs":{"enable_thinking":False}}`. Qwen recommends temp 0.7 / top_p 0.8 in non-thinking mode, but use temp 0 for the judge. |
| `Qwen/Qwen3-4B-Instruct-2507-FP8` | Apache-2.0 | 5.19 GB | 144 KiB | 2.25 GiB | yes (~7.7 GiB; ~6.6 with fp8 KV) | yes | Official FP8. Instruct-only (no thinking block). 256k native ctx. |
| `cyankiwi/Qwen3-4B-Instruct-2507-AWQ-4bit` | Apache-2.0 | 3.44 GB | 144 KiB | 2.25 GiB | **yes, ~6 GiB**, fits next to large-v3 int8 | yes | compressed-tensors W4A16, community quant (21k downloads). |
| `Qwen/Qwen3-4B-Instruct-2507` | Apache-2.0 | 8.04 GB bf16 | 144 KiB | 2.25 GiB | no | yes | Use FP8/AWQ instead. |
| `casperhansen/mistral-nemo-instruct-2407-awq` | none on repo (base Apache-2.0) | 8.35 GB | 160 KiB | 2.5 GiB | **no**. Only alone on the GPU: 8k ctx + fp8 KV, about 9.5 GiB | yes | Strong German prose. Alternatives: `RedHatAI/Mistral-Nemo-Instruct-2407-quantized.w4a16` (8.31 GB), `ModelCloud/...-gptq-4bit`. Repeats itself at long ctx; use temp 0. |
| `Qwen/Qwen2.5-14B-Instruct-AWQ` (and `Qwen/Qwen3-14B-AWQ`) | Apache-2.0 | 9.98 GB (9.3 GiB) | 192 KiB | 3.0 GiB (8k: 1.5) | **borderline, only with Whisper unloaded:** `--max-model-len 8192 --kv-cache-dtype fp8 --gpu-memory-utilization 0.95 --enforce-eager` gives about 9.3+0.75+0.6, roughly 10.7 GiB of ~11.5 usable | yes | Desktop or Xorg on the card will break it. Run it as a separate batch pass after ASR (judge-only stage), never side by side. |
| `PyrTools/Ministral-8B-Instruct-2410-AWQ` | **Mistral Research Licence** (non-commercial) | 5.76 GB | 144 KiB | 2.25 GiB | ~8.5 GiB, fp8 KV ~7.4 | yes | Interleaved sliding-window attention; vLLM treats it as full attention up to 32k. Licence makes it a poor pitch story. |
| `stelterlab/EuroLLM-9B-Instruct-AWQ` | Apache-2.0 | 6.31 GB | 168 KiB | - | **max ctx 4096**: too short for a 5-min call plus prompt | yes | Quant of the *old* EuroLLM. `utter-project/EuroLLM-9B-Instruct` is `gated: auto` (out). The new `utter-project/EuroLLM-9B-Instruct-2512` (Apache-2.0, not gated, 32k ctx) exists only in bf16 (18.3 GB) and as MLX/GGUF. We would have to AWQ it ourselves. Skip. |
| `swiss-ai/Apertus-8B-Instruct-2509` | Apache-2.0, not gated | 16.1 GB bf16 | 128 KiB | 2.0 GiB | **does not load**: needs vLLM >=0.10.2 and transformers >=4.56 | yes | Quant: `RedHatAI/Apertus-8B-Instruct-2509-FP8-dynamic` (9.1 GB incl. dup files, not gated). A second venv with vLLM 0.10.2 (torch 2.8 cu128) *should* run on driver 535 via CUDA minor-version compatibility, but this is **untested**. `swiss-ai/Apertus-v1.5-8B` is `gated: auto` with a new arch (`Apertus1p5ForConditionalGeneration`), so it is out. Nice Swiss story, but not worth the setup time. |
| `microsoft/Phi-4-mini-instruct` | MIT | 7.67 GB bf16 | 128 KiB | 2.0 GiB | no in bf16; community AWQ (`pytorch/Phi-4-mini-instruct-AWQ-INT4`, torchao format, not vLLM-AWQ) | yes | German is noticeably weaker. Not recommended. |
| `gaunernst/gemma-3-12b-it-int4-awq` | Gemma terms, **not gated** mirror | 9.08 GB (incl. vision tower) | - | - | no for 8 GB; 12 GB only alone | yes | `google/gemma-3-*` are `gated: manual`, so out. Small option: `gaunernst/gemma-3-4b-it-int4-awq` (4.0 GB, not gated). Gemma 3 has good German; arch `Gemma3ForConditionalGeneration` is supported in 0.10.1.1. |

**Common vLLM flags (8 GB slice next to Whisper):**
```bash
vllm serve Qwen/Qwen2.5-7B-Instruct-AWQ --max-model-len 16384 --gpu-memory-utilization 0.62 \
  --max-num-seqs 8 --served-model-name judge --port 8000          # add --kv-cache-dtype fp8 for Qwen3-8B
```
- `--gpu-memory-utilization` is a fraction of the *total* 12 GB (0.62 is about 7.4 GiB). vLLM refuses to start
  if that much is not free, so start it before or alongside a Whisper whose footprint you know.
- Structured output: `extra_body={"guided_json": schema}` or OpenAI `response_format={"type":"json_schema",
  "json_schema":{"name":"verdict","schema":schema}}`. The default backend in 0.10.1 is `auto` (xgrammar first).
- Logprobs: `logprobs=True, top_logprobs=5`. The server caps at `--max-logprobs` (default 20). For G-Eval style
  scoring, read the top-k logprobs of the score token. This works with guided JSON as long as the score is a
  single-token enum.

**Top 5 for a German compliance judge (judgement, not measured; settle with `callguard experiment`):**
1. `Qwen/Qwen3-8B-AWQ` (thinking off, fp8 KV, 16k): the best reasoning that fits 8 GB.
2. `Qwen/Qwen2.5-7B-Instruct-AWQ`: already cached, the cheapest KV, and the most predictable JSON. **Default /
   baseline.**
3. `Qwen/Qwen3-4B-Instruct-2507-FP8` (or the cyankiwi AWQ): runs side by side with large-v3. Good for the
   multi-view ensemble.
4. `Qwen/Qwen2.5-14B-Instruct-AWQ` / `Qwen/Qwen3-14B-AWQ`: only as a judge-only pass with Whisper unloaded at
   8k ctx. Likely the most accurate if it fits.
5. `casperhansen/mistral-nemo-instruct-2407-awq`: a second model family for ensemble diversity (different
   errors from Qwen). Also alone on the GPU, 8k ctx.

---

## 5. Embeddings

| id | licence | size | max tokens | vLLM 0.10.1.1 | CPU (sentence-transformers) | verified | notes |
|---|---|---|---|---|---|---|---|
| `BAAI/bge-m3` | MIT | 568M params (2.27 GB incl. dup .bin+.safetensors; ~1.1 GB fp16) | 8192 | yes (`XLMRobertaModel` -> RobertaEmbeddingModel) | yes, `SentenceTransformer("BAAI/bge-m3")` | yes | Dense only via vLLM/ST. Sparse/colbert need `FlagEmbedding`. Strong multilingual, no prefix needed. **Pick this.** |
| `intfloat/multilingual-e5-large-instruct` | MIT | 560M (1.12 GB) | 512 | yes (`XLMRobertaModel`) | yes | yes | Queries need `"Instruct: <task>\nQuery: <text>"`, documents no prefix. The 512-token limit means turn-level chunks only. |
| `Qwen/Qwen3-Embedding-0.6B` | Apache-2.0 | 0.6B (1.19 GB) | 32k | yes (`Qwen3ForCausalLM` with pooling; card says vllm>=0.8.5) | yes (sentence-transformers >=2.7, transformers >=4.51) | yes | Top MTEB-multilingual for its size. Use a query instruction (`prompt_name="query"`). Last-token pooling with left padding (ST handles it). |

Commands:
```bash
# vLLM 0.10.1.1 (--task is deprecated there but still accepted; the new form is --runner pooling --convert embed)
vllm serve BAAI/bge-m3 --runner pooling --convert embed --gpu-memory-utilization 0.08 --max-model-len 8192 --port 8001
# then: POST /v1/embeddings {"model":"BAAI/bge-m3","input":[...]}
```
The app env has no torch, so sentence-transformers on CPU would add torch-cpu (~200 MB wheel from the CPU index).
Alternative: call the vLLM embeddings endpoint, or use `fastembed` (ONNX, ships bge-m3 / e5) if torch must
stay out. That option is unverified for bge-m3.

---

## 6. Audio LLMs (could they understand Swiss German?)

None has published Swiss German results. Voxtral and Qwen2.5-Omni both use Whisper-style audio encoders, so
expect something like Whisper's zero-shot level (ASGDTS large-v3 ~26-28 % WER) plus a stronger LM.

| id | licence | weights | vLLM 0.10.1.1 | VRAM | verified | notes |
|---|---|---|---|---|---|---|
| `mistralai/Voxtral-Mini-3B-2507` | Apache-2.0, not gated | 9.35 GB bf16 (`consolidated.safetensors`; repo also has HF-format shards, so download one format) | **yes** (`VoxtralForConditionalGeneration`; card: vllm >=0.10.0, `vllm[audio]`, mistral_common >=1.8.1) | ~9.5 GB bf16 (card) | yes | Languages: en, es, fr, pt, hi, **de**, nl, it. Up to ~30 min audio for transcription and ~40 min for understanding (32k ctx), so a whole 5-min call fits in one request. `vllm serve mistralai/Voxtral-Mini-3B-2507 --tokenizer_mode mistral --config_format mistral --load_format mistral`. Has `/v1/audio/transcriptions` plus chat with audio. |
| `RedHatAI/Voxtral-Mini-3B-2507-FP8-dynamic` | Apache-2.0 | ~6.1 GB per format | **yes, card says validated on vLLM 0.10.1.1** | ~7 GB est. | yes | **The audio LLM to try.** Same serve flags. Experiment: "Transcribe in Swiss German spelling" and audio-direct compliance QA. Runs *instead of* the text LLM. |
| `Qwen/Qwen2.5-Omni-3B` | Qwen Research licence ("other", non-commercial) | 11.97 GB total (thinker + talker + token2wav) | yes, thinker only (text out) via `Qwen2_5OmniModel` | thinker ~7-8 GB bf16 est. | yes | Feed <=30 s chunks (diarized turns). `Qwen/Qwen2.5-Omni-3B-AWQ` is not public (401). `Qwen/Qwen2.5-Omni-7B-AWQ` (12.7 GB incl. talker) is too big. |
| `Qwen/Qwen2-Audio-7B-Instruct` | Apache-2.0 | 16.8 GB bf16 | yes | too big unquantized | yes | Older. Skip. |
| `microsoft/Phi-4-multimodal-instruct` | MIT | ~11.1 GB bf16 + speech-LoRA 0.9 GB | yes (`Phi4MMForCausalLM`; needs `--enable-lora --max-lora-rank 320 --max-loras 2` and the `speech-lora` path) | ~12 GB, so **does not fit** | yes | German listed among its speech languages. Not viable on the 4070. |
| `swiss-ai/Apertus-v1.5-8B` | Apache-2.0 | 18.4 GB | no (fork) | - | yes | `gated: auto`, so out. |

---

## 7. Offline denoisers

| package / model | licence | install | torch? | verified | notes |
|---|---|---|---|---|---|
| **sherpa-onnx `OfflineSpeechDenoiser` + DPDFNet** (`dpdfnet2.onnx` 10 MB, `dpdfnet4/8`, `dpdfnet_baseline`; source `Ceva-IP/DPDFNet`) | Apache-2.0 | **already installed** (sherpa-onnx 1.13.8 exposes `OfflineSpeechDenoiserDpdfNetModelConfig`). Models: `wget https://github.com/k2-fsa/sherpa-onnx/releases/download/speech-enhancement-models/dpdfnet2.onnx` | no (ONNX, CPU or GPU) | yes (API present in our venv, release assets listed) | DeepFilterNet2 + dual-path RNN. 16 kHz models meant for downstream ASR. `attenuation_limit_db` (example uses 12 dB). Keep it mild for ASR: heavy denoising often *raises* Whisper WER. Example: `python-api-examples/offline-speech-enhancement-dpdfnet.py`, call `sd(samples, sr)` and use `.samples` / `.sample_rate`. **Pick this.** |
| sherpa-onnx + GTCRN (`gtcrn_simple.onnx`, 0.5 MB) | Apache-2.0 / MIT | same release | no | yes | Ultra-light. Weaker than DPDFNet, but real-time on CPU. `OfflineSpeechDenoiserGtcrnModelConfig`. |
| DeepFilterNet3 Rust binary `deep-filter-0.5.6-x86_64-unknown-linux-musl` (GitHub release v0.5.6) | MIT/Apache | download the static binary | no | yes (release assets) | `deep-filter -a 12 -D -o out/ in.wav`. Resamples 16k -> 48k -> 16k internally (checked in `enhance_wav.rs`). Embedded DF3 model. |
| `deepfilternet` 0.5.6 (pip, +`deepfilterlib`) | MIT | `pip install deepfilternet` | yes | yes (PyPI) | Last release 2023. Pins **numpy<2** and `packaging<24` (clashes with our numpy 2.x). Imports the removed `torchaudio.backend.common.AudioMetaData` (and `torch._six` in older code), so it breaks on torchaudio >=2.1 without patches. **Avoid in-process**; use the binary or sherpa. |
| `noisereduce` 3.0.3 | MIT | `pip install noisereduce` | no (numpy/scipy) | yes | Spectral gating. Fast, harmless, weak. Baseline for the A7 experiment. |
| `speechbrain` 1.1.1 + `speechbrain/metricgan-plus-voicebank` / `sepformer-wham16k-enhancement` | Apache-2.0 | pip | yes (torch >=2.1) | PyPI yes; HF models not re-checked | Torch only on the GPU host. |
| `clearvoice` 0.1.2 (ClearerVoice-Studio: FRCRN_SE_16K, MossFormer2_SE_48K) | Apache-2.0 | pip | yes | PyPI yes | Pins numpy<2 and old librosa/opencv. Separate venv. |
| `resemble-enhance` 0.0.1 | MIT | pip | pins **torch==2.1.1**, deepspeed | yes | Do not use (pins clash with everything). |
| `denoiser` (Meta, dns64) | CC BY-NC | pip | yes | yes | Stale (2022). Skip. |

Our case audio is synthetic TTS with added noise. Denoising helps only if noise actually hurts our ASR. Measure
it with A7 (clean vs noisy vs noisy+DPDFNet, same ASR), and include clean+DPDFNet to catch damage.

---

## Sources

- HF model API (`https://huggingface.co/api/models/<id>`) and model cards for every id above (queried 2026-10-10).
- Flix paper: https://arxiv.org/abs/2606.07608
- "Does Whisper understand Swiss German?": https://arxiv.org/abs/2404.19310
- SwissText 2023 (SwissDial, Spaiche): https://aclanthology.org/2023.swisstext-1.pdf
- openai/whisper README (turbo not trained for translation): https://github.com/openai/whisper
- vLLM registry: https://github.com/vllm-project/vllm/blob/v0.10.1.1/vllm/model_executor/models/registry.py (Apertus appears only from v0.10.2)
- vLLM arg_utils v0.10.1.1 (`--runner/--convert`, `--task` deprecated, `max_logprobs=20`)
- Omnilingual ASR: https://github.com/facebookresearch/omnilingual-asr (README, `lang_ids.py`, per-language CSV)
- sherpa-onnx speech enhancement: https://github.com/k2-fsa/sherpa-onnx/releases/tag/speech-enhancement-models
- DPDFNet: https://huggingface.co/Ceva-IP/DPDFNet
- DeepFilterNet: https://github.com/Rikorose/DeepFilterNet (release v0.5.6, `libDF/src/bin/enhance_wav.rs`)
- DeepFilterNet torchaudio breakage: https://discuss.pytorch.org/t/no-module-named-torchaudio-backend-common/186937
- faster-whisper 1.2.1 `transcribe.py` (tokenizer fallback to `openai/whisper-tiny`, `FeatureExtractor(feature_size=80)` default), read from our venv.
