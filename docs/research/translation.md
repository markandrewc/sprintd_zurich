# Self-hostable machine translation for the transcript views

Scope: which self-hostable models can produce our three translated views of a call:

- **gsw -> de**: Swiss German dialect text to Standard German
- **gsw -> en**: Swiss German dialect text to English
- **de -> en**: Standard German (what our Whisper fine-tune already outputs) to English

Also covered: Whisper `task=translate` as a direct speech-to-English view, and how to keep translations aligned to
segments. Research only, done 2026-10-09/10: no weights downloaded, nothing run. Every "VRAM" figure is an
**estimate** from the published file sizes, not a measurement. Numbers in [brackets] point to the Sources list.

---

## Recommendation for our 4070

**1. Use the LLM we already serve as the translator for all three directions.** It costs no extra VRAM, it can see
context across segments, and vLLM structured outputs (`json_mode: json_schema`, already in `config/gpu.yaml`) keep
segment ids aligned.
   - Default: **`Qwen/Qwen3-8B-AWQ`** (Apache-2.0, 8.19B params, 6.10 GB 4-bit weights [Q3c]). Run it in
     non-thinking mode (`enable_thinking=False`, which also works through vLLM [Q3c]).
   - Swiss-specific challenger: **`swiss-ai/Apertus-8B-Instruct-2509`** (Apache-2.0 plus an acceptable-use gate,
     8.05B params, native `ApertusForCausalLM` in vLLM [VL]). It is the only 7-9B open model we found with Swiss
     German *explicitly* in training: "Swiss-German dialect instructions (6K)" in post-training and a FineWeb-2 subset
     of `.ch`/`.swiss` sites (1.8B tokens) in pre-training [AP]. On 12 GB, use the FP8-dynamic build (9.13 GB
     [APfp8]; FP8 W8A8 is supported on Ada GPUs in vLLM [VLq]) with a short `--max-model-len`, or the Q4_K_M GGUF
     (5.06 GB [APgguf]) through our existing `llama_cpp` backend.
   - **No published benchmark scores any 7-9B open LLM on Swiss German -> Standard German text.** Neither model is
     proven. A/B them on our own data (point 4) and pick by downstream check precision/recall.

**2. For gsw -> en, pivot through Standard German (gsw -> de -> en)** and keep the direct gsw -> en as a second
variant. The only published evidence: on CODET Swiss German (368 locales), normalising dialect to Standard German
first (GPT-4, zero-shot) and then translating with NLLB-200-3.3B raised BLEU from 47.77 to 73.56 [VD25]. That result
used GPT-4 and NLLB, not our models, so it is a hint, not proof.

**3. de -> en is the easy direction.** It is high-resource, and the LLM from point 1 handles it. Cheap dedicated
baseline: `Helsinki-NLP/opus-mt-de-en` (Apache-2.0, ~0.3 GB; newstest2019 de-en BLEU 40.1 [OPde]) converted to
CTranslate2. CTranslate2 is already installed through faster-whisper, and it supports MarianMT, NLLB, M2M-100 and T5
[CT2].

**4. Evaluate on the oracle scripts first.** `data_upstream/.../Transkript/` holds the 30 dialogues as written
Zurich-style dialect, one turn per segment (e.g. "Ich ha am Samschtig im Internet öppis bstellt"). Translate them
gsw -> de and gsw -> en with each candidate, feed every view to the same checks, and compare precision/recall. That
separates translation quality from ASR errors. For an external sanity check there is **NTREX-128 Swiss German**: 1997
news sentences in Bern and Zurich dialect (`en-gsw_be`, `en-gsw_zh`), aligned with the NTREX German and English
references [AE23][DE]. Use it to score gsw -> de and gsw -> en with chrF/COMET. Be careful with automatic metrics
when Swiss German is the *output* [AE23]; here it is only the input.

**5. Optional dedicated-MT baselines that fit next to the LLM:**
   - **OPUS-MT `Helsinki-NLP/opus-mt-tc-bible-big-gmw-deu_eng_nld`** (Apache-2.0, 217M params, 0.87 GB fp32): lists
     `gsw` as a source and takes `>>deu<<`/`>>eng<<` target tokens [OPbib]. Est. under 1 GB VRAM in CT2 int8. Its
     card gives no gsw-specific score. The older sibling `opus-mt-tc-big-gmw-gmw` (CC-BY-4.0) reports gsw-deu BLEU
     27.5 / chrF 0.450 and gsw-eng 19.1 / 0.352, but on tiny Tatoeba sets (67 and 205 sentences) [OPgmw].
   - **MADLAD-400-3B-MT** (Apache-2.0, 2.94B params): has a `<2gsw>` language token and gsw web data in training
     [MLtok][ML]. **No published gsw translation score.** CT2 int8 conversion `Nextcloud-AI/madlad400-3b-mt-ct2-int8`
     is 2.95 GB [MLct2], so it needs about 3.5-4.5 GB (estimate). Run it while vLLM is stopped, or on the PC's CPU.

**6. Do not use for this project:**
   - NLLB-200: CC-BY-NC, and **it has no Swiss German at all**. `als_Latn` is *Tosk Albanian*, not Alemannic [FL].
   - SeamlessM4T v2: CC-BY-NC, no gsw [SM].
   - TowerInstruct / Tower+: non-commercial licenses, no gsw [TW][TWp].
   - Aya Expanse: CC-BY-NC, no gsw [AY].
   - M2M-100: MIT, but no gsw [M2M].

**7. Speech -> English with Whisper `task=translate`:**
   - **It will not work with our current model.** It is a large-v3-*turbo* fine-tune, and OpenAI states "the
     `turbo` model is not trained for translation tasks... will return the original language even if
     `--task translate` is specified" [WR].
   - A direct English view would need non-turbo large-v3: stock, or the MIT LoRA fine-tune
     `gcoli/whisper-large-v3-swiss-german-mit` that `gpu.yaml` already points at. faster-whisper accepts
     `task="translate"` [FW].
   - **We found no published evaluation of Whisper translating Swiss German *audio* into English.** We do know that
     Whisper large-v3 already "translates" Swiss German speech into Standard German when set to transcribe
     (SwissDial BLEU 53-70 per dialect [DW]).
   - Treat it as a one-hour side experiment (est. ~3-4.5 GB VRAM in fp16 [FWb]). It is not the main English view.

**Suggested GPU layout on the 4070** (all estimates). ASR results are cached (`.cache/asr`), so ASR and the LLM do
not need to share the GPU:
1. Run ASR for all calls (turbo int8, est. ~1.5-3 GB).
2. Start vLLM with Qwen3-8B-AWQ at `GPU_UTIL≈0.75` and `MAX_LEN 8192`: 6.1 GB weights plus about 2-3 GB KV cache.
3. Run OPUS-MT on CT2 int8 inside the pipeline process (under 1 GB).
4. Apertus FP8 (9.1 GB) only fits with vLLM alone on the card and a short context. Use the GGUF if it gets tight.
   Under WSL2, the Windows desktop also takes some VRAM, so lower `GPU_UTIL`.

**Which view will likely need the least fine-tuning** (our judgement, not measured):
- **de view**: lowest effort. ASR already outputs Standard German, the case keyword list has a `de` list per keyword,
  and LLM judges work in German out of the box.
- **en view**: de -> en is reliable, but it adds an error stage, and keyword lists would have to be translated (once,
  then reviewed by hand).
- **gsw view**: highest effort. It needs dialect-orthography ASR (another workstream), and how well 7-9B models read
  written Swiss German is unverified. If any fine-tuning becomes necessary, it will be here. The only data available
  for that is small: SwissDial (8 dialects, about 3 h per dialect, dialect and Standard German transcripts [SD]) and
  NTREX-gsw.

---

## 1. Language coverage, checked against primary sources

| Model | Swiss German supported? (code) | License | Params / files | Formats | Runs in | Evidence |
|---|---|---|---|---|---|---|
| **NLLB-200** (600M / 1.3B / 3.3B, incl. distilled) | **No.** There is no `gsw_*` code. `als_Latn` is listed in FLORES-200 as **"Tosk Albanian"** [FL]. The NLLB HF card's `als` tag means Albanian, not Alemannic [NL] | **CC-BY-NC-4.0** [NL] | 600M: 2.46 GB, 1.3B: 5.48 GB, 3.3B: 17.6 GB (pytorch .bin) [HF API]. CT2 int8: `OpenNMT/nllb-200-3.3B-ct2-int8` 3.36 GB, `OpenNMT/nllb-200-distilled-1.3B-ct2-int8` 1.38 GB | transformers, CT2 | transformers, CTranslate2 [CT2]. **Not vLLM** [VL] | CODET: dialect -> English with Swiss German fed as German; COMET (without source) about 0.86-0.89 per locale, best with 3.3B. Short SADS questionnaire sentences [CO] |
| **MADLAD-400 MT** (3B / 7B / 7B-bt / 10B) | **Yes, at least nominally.** `gsw` is in the card's language list and `<2gsw>` is in the tokenizer [ML][MLtok]. The source language is not tagged; you pick the target with `<2de>` or `<2en>` [ML]. The paper's data audit note for gsw reads "STILL BOILERPLATE (r1: ok but idk diff between gsw and de)" [MLp] | **Apache-2.0** [ML] | 3B: 2.94B params, 11.76 GB fp32. 7B: 8.30B. 10B: 10.7B [HF API]. CT2 int8 3B: 2.95 GB [MLct2]. GGUF q4k in the official repo: 1.65 GB [ML] | transformers (T5), CT2, GGUF (candle) | transformers, CTranslate2 (T5 supported [CT2]). **Not vLLM** | **No gsw score published** (FLORES/NTREX have no gsw) [MLp] |
| **SeamlessM4T v2 large** | **No.** `deu` is supported for speech and text in and out. Luxembourgish is speech-input only. No gsw [SM] | **CC-BY-NC-4.0** [SM] | 2.31B params, 9.24 GB [HF API] | transformers, fairseq2 | transformers / seamless_communication. Not vLLM, no CT2 | None for Swiss German |
| **M2M-100** (418M / 1.2B / 12B) | **No.** 100 languages, `lb` included, no gsw [M2M] | MIT [M2M] | 1.2B: 4.96 GB [HF API] | transformers, CT2 | transformers, CT2 [CT2] | None |
| **OPUS-MT** (Helsinki-NLP, Marian) | **Yes, as a source** in the multilingual West-Germanic, Germanic and mul models: `opus-mt-gmw-en`, `opus-mt-gmw-gmw`, `opus-mt-gem-en`, `opus-mt-mul-en`, `opus-mt-tc-big-gmw-gmw`, `opus-mt-tc-bible-big-gmw-en`, `opus-mt-tc-bible-big-gmw-deu_eng_nld` [OPgmw][OPbib][OPbibEn]. No gsw-only pair model exists | Apache-2.0 (bible-big, older gmw). **CC-BY-4.0** (`tc-big-gmw-gmw`) | 213-232M params. 0.43 GB (fp16) to 0.93 GB (fp32) [HF API] | transformers (Marian), CT2 | transformers, CTranslate2 [CT2]. Not vLLM | Tatoeba only, very small sets: tc-big-gmw-gmw gsw-deu BLEU 27.5 / chrF 0.450 (67 sent.), gsw-eng 19.1 / 0.352 (205 sent.) [OPgmw]. opus-mt-mul-en gsw-eng 18.2 / 0.334 [OPmul]. opus-mt-gem-en 15.3 / 0.333. opus-mt-gmw-gmw gsw-deu 10.5 / 0.350. The bible-big cards give only multi-language averages [OPbib] |
| **TowerInstruct-7B-v0.2** | **No.** 10 languages (en, pt, es, fr, de, nl, it, ko, zh, ru) [TW] | **CC-BY-NC-4.0** (plus Llama 2 license) [TW] | 6.74B, 26.9 GB fp32 | transformers | vLLM (LlamaForCausalLM), transformers | None for gsw |
| **Tower+ 9B** | **No.** About 22-27 languages listed, German included, no gsw [TWp] | **Non-commercial**: YAML says CC-BY-NC-SA-4.0, card text says CC-BY-NC-4.0 [TWp] | 9.24B, 18.5 GB bf16 | transformers, GGUF | vLLM (Gemma2), transformers | None for gsw |
| **EuroLLM-9B-Instruct-2512** | **No.** 35 languages (EU-24 plus others) [EU] | Apache-2.0 [EU] | 9.15B, 18.3 GB bf16 | transformers, GGUF | vLLM (LlamaForCausalLM) | None for gsw |
| **Aya Expanse 8B** / **Aya-101** | **No.** Expanse covers 23 languages [AY]. Aya-101 (mT5, 101 languages) has `ltz`, not gsw [AY101] | Expanse: **CC-BY-NC**. Aya-101: Apache-2.0 | Expanse 8.03B. Aya-101 12.9B (51.7 GB fp32) | transformers | Expanse: vLLM (Cohere). Aya-101: transformers/CT2 (mT5) | None for gsw |
| **TranslateGemma 4B / 12B** (Jan 2026) | **No.** 55 WMT24++ languages. The chat template maps `de-CH` to plain "German" and has no gsw code [TG][TGt] | Gemma terms (gated) [TG] | 4.97B (8.6 GB bf16) / 13.2B | transformers | vLLM only with a modified chat template (community mirror [TGt]). **2K-token input context** [TG] | WMT24++ (55 languages) COMET 81.6 (4B) / 83.5 (12B) [TG]. Nothing for gsw |
| **Hunyuan-MT-7B** | **No.** 33 languages, de included [HY] | Tencent Hunyuan Community License. **Does not apply in the EU, UK or South Korea** [HYl] | 8.03B | transformers | Custom architecture (`HunYuanDenseV1`). vLLM support not verified by us | WMT25 claims, nothing for gsw |
| **Seed-X-7B** | **No.** 28 languages [SX] | OpenMDW [SX] | 7.51B | transformers | vLLM (Mistral architecture) | Nothing for gsw |
| **SalamandraTA-7B-instruct** | **No.** 40 languages [SA] | **GPL-3.0** [SA] | 7.77B | transformers, GGUF | vLLM (Llama) | Nothing for gsw |
| **Qwen2.5-7B-Instruct** | **Not listed** ("over 29 languages") [Q25] | Apache-2.0 | 7.62B. AWQ 5.57 GB | transformers, AWQ, GGUF | vLLM, transformers, llama.cpp | Nothing for gsw |
| **Qwen3-8B** | **Not listed.** The 119-language list in the Qwen3 blog includes Luxembourgish and Limburgish but not Swiss German or Alemannic [Q3b] | Apache-2.0 [Q3c] | 8.19B. AWQ 6.10 GB. Q4_K_M GGUF 5.03 GB | transformers, AWQ, GGUF | vLLM [VL], llama.cpp | Nothing for gsw |
| **Llama-3.1-8B-Instruct** | **No.** 8 supported languages incl. German. The card calls other languages out-of-scope (written Swiss German is a grey zone) [LL] | Llama 3.1 Community License (gated) [LL] | 8.03B, 16.1 GB bf16 | transformers, AWQ/GGUF (community) | vLLM, llama.cpp | Nothing for gsw |
| **Mistral-Nemo-Instruct-2407** | **Not listed** (multilingual; German MMLU 62.7%) [MN] | Apache-2.0 [MN] | 12.25B, about 24.5 GB bf16 | transformers / mistral format | vLLM | Nothing for gsw. **On 12 GB it only fits as 4-bit (est. ~7-8 GB) and leaves little KV cache** |
| **Apertus-8B-Instruct-2509** | **Yes, explicitly targeted.** "Swiss-German dialect instructions (6K)" in SFT and FineWeb-2-Swiss pre-training data [AP]. The recommended system prompt claims "strong support for... Swiss German dialects" [AP] | Apache-2.0 plus AUP gate [APc] | 8.05B, 16.1 GB bf16. FP8-dynamic 9.13 GB [APfp8]. Q4_K_M 5.06 GB [APgguf] | transformers (>= 4.56), FP8, GGUF | **vLLM native** (`ApertusForCausalLM`) [VL], SGLang, llama.cpp | **No Swiss German MT score published.** Related: Romansh WMT24++ RG -> DE BLEU 41.3 (8B) vs 35.6 for Llama-3.3-70B [AP, Table 24] |
| **Apertus v1.5 8B** (Jul 2026) | Not stated in the card. **Accepts audio input** (24 kHz, 40 tokens/s) [AP15] | Apache-2.0 plus AUP [AP15] | 8.90B, 18.4 GB bf16. Community FP8 11.4 GB | transformers fork | **Needs the swiss-ai fork of vLLM/transformers** for now [AP15] | No evals published yet ("will be provided in the technical report") [AP15]. Too big for 12 GB next to anything else (estimate) |

Not checked in depth: Qwen3.5-9B ("201 languages and dialects", Apache-2.0) and Gemma 4 (Apache-2.0, "140
languages"). Both are newer than the models above. We did not verify Swiss German support for either.

---

## 2. Published evidence on Swiss German translation

| What | Direction | Systems | Result | Relevance for us |
|---|---|---|---|---|
| Alam & Anastasopoulos, VarDial 2025 [VD25] | gsw (CODET/SADS, 368 locales) -> English | GPT-4 zero-shot normalisation to Standard German, then NLLB-200-3.3B | Avg BLEU **47.77 -> 73.56** with normalisation (Table 6/16). LoRA-tuned 7B models beat GPT-4 on Arabic normalisation with about 10k pairs. For Swiss German only GPT-4 was used | Supports **pivoting gsw -> de -> en**. Shows that LoRA on small parallel data can work (not shown for gsw) |
| CODET, Alam et al. 2024 [CO] | gsw (SADS) -> English | NLLB 600M / 1.3B / 3.3B | COMET (without source) about 0.86-0.89 per locale. Northern, more German-like dialects score higher | NLLB "works" by treating gsw as German, but it is NC-licensed |
| Aepli et al., WMT 2023 [AE23][DE] | English -> Bern / Zurich dialect | 9 neural (Textshuttle) + 1 rule-based | Main point: existing metrics are not dialect-robust. Releases **NTREX-128 Swiss German** (1997 sentences, CC-BY-SA-4.0) | Our best external **gsw-source test set** (reverse it: gsw -> de/en against the NTREX deu/eng references) |
| Mutal et al., MT Summit 2023 [MU23] | "normalised Swiss German" ASR output -> Standard German | fine-tuned OPUS-MT (incl. `opus-mt-tc-big-gmw-gmw`), BERT2BERT, mBART25/50 | raw ASR chrF 75.27. Fine-tuned gmw-gmw 78.95. mBART50 79.82 (BLEU 54.68) | Fine-tuned seq2seq. Their input is word-normalised, not phonetic dialect spelling |
| Dolev, Lutz, Aepli, VarDial 2024 [DW] | gsw **speech** -> Standard German text | Whisper large-v3 zero-shot | SwissDial BLEU 53.5 (Walser) to 70.0 (Grisons). Concise style, drops modal particles, 4/16 long conversations had hallucinated sentences | Explains why our ASR "de" view already exists. Nothing for English |
| Honnet et al., LREC 2018 [HO] | Bernese -> Standard German | char-NMT + PBSMT | BLEU about 36 | Pre-LLM baseline only |
| OPUS-MT model cards [OPgmw][OPmul] | gsw -> de / en | Marian | See table above (tiny Tatoeba sets) | Weak evidence |
| Swiss-Bench 003, 2026 [SB] | gsw *comprehension* (30 items: ZH/BE/BS) | 10 large models (no 7-9B, no Apertus) | 70.0-96.7% | Large models read written gsw well. Says nothing about 8B models |
| "Normalizing Swiss German Dialects with the Power of LLMs" (Procedia CS 2024) [PR] | gsw -> de | fine-tuned mT5 small/base/large on SwissDial | **Not verified**: the publisher page returned 403. Per the search abstract, even mT5-small normalises well | Possible LoRA/fine-tune recipe if needed |

**What we could not find:** a "SwissBench" for MT; any published gsw -> de or gsw -> en score for Qwen2.5/Qwen3,
Llama 3.1, Mistral-Nemo, EuroLLM, Tower or Apertus; any Swiss German speech -> English evaluation for Whisper or
SeamlessM4T.

---

## 3. Speech -> English directly (Whisper `task=translate`)

- **Turbo models do not translate.** OpenAI's README: "the `turbo` model is not trained for translation tasks...
  The `turbo` model will return the original language even if `--task translate` is specified" [WR]. Our ASR,
  `nebi/whisper-large-v3-turbo-swiss-german-ct2-int8`, is a CT2 conversion of `Flurin17/whisper-large-v3-turbo-swiss-german`
  [NB]. It therefore cannot produce an English view.
- **Non-turbo large-v3** (stock, or the LoRA-merged `gcoli/whisper-large-v3-swiss-german-mit` [GC]) was trained with
  the translate task. faster-whisper exposes `task="translate"` [FW]. Whether a Swiss German fine-tune *keeps*
  translate ability after transcription-only fine-tuning is **not verified**, and neither is how well stock large-v3
  translates Swiss German audio to English. Swiss German is "allegedly not part of Whisper's training data" [DW],
  so the model can only handle it as German.
- VRAM (estimate from the faster-whisper large-v2 benchmark): fp16 beam 5 about 4.5 GB, int8 about 2.9 GB [FWb].
- Other audio-input models: Voxtral Mini 3B (Apache-2.0, vLLM, speech translation, but German rather than gsw,
  ~9.5 GB bf16 [VX]) and Apertus v1.5 (audio input, needs a vLLM fork [AP15]). Neither has published Swiss German
  results. Both would have to run *instead of* the LLM on 12 GB.
- **Verdict:** a quick side experiment on 2-3 calls with stock large-v3. Compare its English with gsw -> de -> en text
  MT. Do not build the English view on it.

---

## 4. Keeping segment alignment

The pipeline's unit is the diarized segment (`Transcript.segments`, with start/end, speaker, role). Every view
should be **a parallel text field on the same segment id**, never a re-segmented text. Timestamps, snippets and
evidence passages then come from the source segment for every view.

Recipe for LLM translation (vLLM, temperature 0):

1. **Window**: translate N = 8-12 consecutive segments per request. Add the previous 4-6 segments (source and their
   finished translation) as read-only context, plus speaker roles ("Beratung" / "Kunde"). This resolves pronouns and
   ellipsis without letting the model merge turns.
2. **Prompt** (system, keep it short):
   - Translate each segment separately.
   - Never merge, split, summarise or drop a segment.
   - Keep names, amounts, dates, account/card digits and codes exactly.
   - Write numbers as digits.
   - If a segment is unintelligible, copy it.
   - Output only JSON.
   - For gsw input, say "Zurich-style Swiss German in phonetic spelling".
3. **Structured output**: `{"segments":[{"id":int,"text":str}]}`, with the JSON schema fixing `minItems = maxItems = N`
   and, if possible, an `enum` of the expected ids. The `json_schema` mode is already wired in `gpu.yaml`.
4. **Validate**:
   - The ids match.
   - Every digit group in the source appears in the target (for gsw input, after normalising number words, or just
     flag the segment).
   - Length ratio is within about 0.5-2.0.
   - On failure, re-translate that segment alone, with context.
5. **Pivot**: produce `de` first (from gsw), then `en` from `de` with the same windowing. Also store direct `gsw -> en`
   so both can be compared.
6. **Cache** per (model, prompt version, source hash), like `.cache/asr` and `.cache/check`.

For sentence-level NMT (OPUS-MT, MADLAD, NLLB): translate one segment per input with no context. Split long segments
into sentences and join the outputs back under the same id. Word timestamps exist only for the source view, so
translated views get segment-level timestamps only.

Keywords: `Stichwortliste.json` already has a `de` and a `gsw` list per keyword. The English view needs an `en` list.
Translate it once with the LLM, then check it by hand, or let only the LLM checks run on the English view.

---

## 5. VRAM cheat-sheet for the 4070 (12 GB, all estimates)

| Component | Weights on disk | Est. VRAM | Note |
|---|---|---|---|
| ASR turbo gsw CT2 int8 (current) | about 0.8 GB | 1.5-3 GB | cached, so it can run before vLLM starts |
| Qwen3-8B-AWQ in vLLM | 6.10 GB [HF API] | 8.5-9.5 GB at `GPU_UTIL 0.75` | recommended default |
| Qwen2.5-7B-Instruct-AWQ in vLLM | 5.57 GB | about 8-9 GB | fallback |
| Apertus-8B-Instruct FP8-dynamic in vLLM | 9.13 GB | about 10.5-11.5 GB, short context | alone on the GPU only |
| Apertus-8B Q4_K_M (llama.cpp) | 5.06 GB | about 6-7 GB at 8k context | our `llama_cpp` backend |
| OPUS-MT big (CT2 int8) | about 0.25 GB after conversion | under 1 GB | fits next to the LLM |
| MADLAD-400-3B (CT2 int8) | 2.95 GB | 3.5-4.5 GB | sequential, or on CPU |
| NLLB-200-3.3B (CT2 int8) | 3.36 GB | about 4 GB | NC license, no gsw |
| Whisper large-v3 fp16 (translate test) | about 3.1 GB | about 4.5 GB [FWb] | sequential |

Side note outside this topic: the upstream of our current ASR, `Flurin17/whisper-large-v3-turbo-swiss-german`, is
**CC-BY-NC-4.0** [FLR], even though the nebi CT2 repo is tagged apache-2.0 and defers to the original [NB]. The
`gcoli/...-mit` model in `gpu.yaml` exists for that reason [GC].

---

## Sources

- [FL] FLORES-200 language list (`als_Latn` = Tosk Albanian; `deu_Latn`, `ltz_Latn`, `lim_Latn`): https://github.com/facebookresearch/flores/blob/main/flores200/README.md
- [NL] NLLB-200 model card (CC-BY-NC-4.0; language tags): https://huggingface.co/facebook/nllb-200-distilled-600M ; special tokens: https://huggingface.co/facebook/nllb-200-distilled-600M/blob/main/special_tokens_map.json
- [ML] MADLAD-400-3B-MT card (Apache-2.0, `gsw` in language list, usage with `<2xx>`, GGUF files): https://huggingface.co/google/madlad400-3b-mt
- [MLtok] MADLAD tokenizer (`<2gsw>`, `<2de>`, `<2en>`): https://huggingface.co/google/madlad400-3b-mt/blob/main/tokenizer.json
- [MLp] Kudugunta et al. 2023, MADLAD-400 paper (gsw audit note; FLORES/NTREX evals): https://arxiv.org/abs/2309.04662
- [MLct2] MADLAD-400-3B CT2 int8: https://huggingface.co/Nextcloud-AI/madlad400-3b-mt-ct2-int8
- [SM] SeamlessM4T v2 card (CC-BY-NC-4.0; language table): https://huggingface.co/facebook/seamless-m4t-v2-large
- [M2M] M2M-100 1.2B card (MIT; 100 languages): https://huggingface.co/facebook/m2m100_1.2B
- [OPgmw] OPUS-MT tc-big gmw-gmw (CC-BY-4.0; gsw-deu/gsw-eng Tatoeba scores): https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-gmw-gmw and https://huggingface.co/Helsinki-NLP/opus-mt-tc-big-gmw-gmw/blob/main/benchmark_results.txt ; older gmw-gmw: https://huggingface.co/Helsinki-NLP/opus-mt-gmw-gmw ; gem-en: https://huggingface.co/Helsinki-NLP/opus-mt-gem-en ; gmw-en: https://huggingface.co/Helsinki-NLP/opus-mt-gmw-en
- [OPbib] OPUS-MT tc-bible-big gmw -> deu/eng/nld (Apache-2.0; gsw source): https://huggingface.co/Helsinki-NLP/opus-mt-tc-bible-big-gmw-deu_eng_nld
- [OPbibEn] OPUS-MT tc-bible-big gmw -> en: https://huggingface.co/Helsinki-NLP/opus-mt-tc-bible-big-gmw-en
- [OPmul] OPUS-MT mul-en (gsw-eng Tatoeba 18.2): https://huggingface.co/Helsinki-NLP/opus-mt-mul-en
- [OPde] OPUS-MT de-en (Apache-2.0; newstest scores): https://huggingface.co/Helsinki-NLP/opus-mt-de-en
- [CT2] CTranslate2 Transformers converter, supported models (MarianMT, M2M100, NLLB, T5, Whisper, Qwen3...): https://github.com/OpenNMT/CTranslate2/blob/master/docs/guides/transformers.md
- [VL] vLLM supported models (Apertus, Qwen3, Llama, Gemma3; encoder-decoder MT only via plugins, BART plugin only): https://github.com/vllm-project/vllm/blob/main/docs/models/supported_models.md
- [VLq] vLLM quantization hardware table (FP8 W8A8 on Ada, AWQ, GGUF, bitsandbytes): https://github.com/vllm-project/vllm/blob/main/docs/features/quantization/README.md
- [TW] TowerInstruct-7B-v0.2 card: https://huggingface.co/Unbabel/TowerInstruct-7B-v0.2
- [TWp] Tower-Plus-9B card: https://huggingface.co/Unbabel/Tower-Plus-9B
- [EU] EuroLLM-9B-Instruct-2512 card: https://huggingface.co/utter-project/EuroLLM-9B-Instruct-2512
- [AY] Aya Expanse 8B card: https://huggingface.co/CohereLabs/aya-expanse-8b
- [AY101] Aya-101 card: https://huggingface.co/CohereLabs/aya-101
- [TG] TranslateGemma 12B card (55 languages, 2K input context, WMT24++ metrics, Gemma license): https://huggingface.co/google/translategemma-12b-it ; tech report: https://arxiv.org/abs/2601.09012
- [TGt] vLLM-compatible TranslateGemma chat template (language code map incl. `de-CH` -> "German"): https://huggingface.co/Infomaniak-AI/vllm-translategemma-4b-it
- [HY] Hunyuan-MT-7B card: https://huggingface.co/tencent/Hunyuan-MT-7B ; [HYl] license: https://huggingface.co/tencent/Hunyuan-MT-7B/blob/main/License.txt
- [SX] Seed-X-PPO-7B card: https://huggingface.co/ByteDance-Seed/Seed-X-PPO-7B
- [SA] SalamandraTA-7B-instruct card: https://huggingface.co/BSC-LT/salamandraTA-7b-instruct
- [Q25] Qwen2.5-7B-Instruct card: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- [Q3c] Qwen3-8B card (Apache-2.0, enable_thinking also via vLLM): https://huggingface.co/Qwen/Qwen3-8B ; AWQ: https://huggingface.co/Qwen/Qwen3-8B-AWQ ; GGUF: https://huggingface.co/Qwen/Qwen3-8B-GGUF
- [Q3b] Qwen3 blog, 119-language list: https://qwenlm.github.io/blog/qwen3/
- [LL] Llama-3.1-8B-Instruct card (8 supported languages, license): https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct
- [MN] Mistral-Nemo-Instruct-2407 card: https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407
- [AP] Apertus tech report (Swiss German SFT data, FineWeb-2-Swiss, Romansh WMT24++ Table 24, system prompt): https://arxiv.org/abs/2509.14233
- [APc] Apertus-8B-Instruct-2509 card: https://huggingface.co/swiss-ai/Apertus-8B-Instruct-2509
- [APfp8] Apertus-8B FP8-dynamic: https://huggingface.co/RedHatAI/Apertus-8B-Instruct-2509-FP8-dynamic
- [APgguf] Apertus-8B GGUF: https://huggingface.co/bartowski/swiss-ai_Apertus-8B-Instruct-2509-GGUF
- [AP15] Apertus v1.5 8B card (audio input, vLLM fork): https://huggingface.co/swiss-ai/Apertus-v1.5-8B
- [VD25] Alam & Anastasopoulos 2025, "Large Language Models as a Normalizer for Transliteration and Dialectal Translation", VarDial: https://aclanthology.org/2025.vardial-1.5/
- [CO] Alam et al., CODET (contrastive dialectal MT benchmark, Swiss German from SADS): https://arxiv.org/abs/2305.17267
- [AE23] Aepli, Amrhein, Schottmann, Sennrich 2023, "A Benchmark for Evaluating Machine Translation Metrics on Dialects Without Standard Orthography" (WMT): https://arxiv.org/abs/2311.16865
- [DE] NTREX-128 Swiss German data (`ntrex-128/references/en-gsw_be|zh.refA.txt`): https://github.com/textshuttle/dialect_eval ; NTREX-128: https://github.com/MicrosoftTranslator/NTREX
- [MU23] Mutal et al. 2023, "Improving Standard German Captioning of Spoken Swiss German: Evaluating Multilingual Pre-trained Models" (MT Summit): https://aclanthology.org/2023.mtsummit-users.6/
- [DW] Dolev, Lutz, Aepli 2024, "Does Whisper Understand Swiss German?" (VarDial): https://arxiv.org/abs/2404.19310
- [HO] Honnet et al. 2018, "Machine Translation of Low-Resource Spoken Dialects: Strategies for Normalizing Swiss German": https://arxiv.org/abs/1710.11035
- [SB] Swiss-Bench 003 (2026): https://arxiv.org/abs/2604.05872
- [PR] "Normalizing Swiss German Dialects with the Power of Large Language Models", Procedia Computer Science 2024 (not verified, 403): https://www.sciencedirect.com/science/article/pii/S1877050924030035
- [SD] SwissDial corpus page (ETH): https://mtc.ethz.ch/publications/open-source/swiss-dial.html ; paper: https://arxiv.org/abs/2103.11401
- [WR] openai/whisper README (turbo not trained for translation): https://github.com/openai/whisper/blob/main/README.md
- [FW] faster-whisper `transcribe(task=...)`: https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py ; [FWb] VRAM benchmark: https://github.com/SYSTRAN/faster-whisper/blob/master/README.md
- [NB] nebi CT2 conversion card: https://huggingface.co/nebi/whisper-large-v3-turbo-swiss-german-ct2-int8
- [FLR] Flurin17 turbo Swiss German card (CC-BY-NC-4.0, Standard German output): https://huggingface.co/Flurin17/whisper-large-v3-turbo-swiss-german
- [GC] gcoli large-v3 Swiss German MIT card: https://huggingface.co/gcoli/whisper-large-v3-swiss-german-mit
- [VX] Voxtral Mini 3B card: https://huggingface.co/mistralai/Voxtral-Mini-3B-2507
- [HF API] Parameter counts and file sizes from `https://huggingface.co/api/models/<id>?blobs=true` (queried 2026-10-09)
