# Fine-tuning Swiss German Whisper on one RTX 4070 (12 GB) over a weekend

Status: desk research only, done 2026-10-09/10. Nothing was downloaded or run. Every number marked
**(estimate)** is my own arithmetic, not a measurement. Everything else links to a primary source
(model card, paper, repo or code) listed under [Sources](#sources).

Context: callguard currently transcribes with `nebi/whisper-large-v3-turbo-swiss-german-ct2-int8`
(faster-whisper, Standard German output, `condition_on_previous_text: true`, `word_timestamps: true`,
`snippets.pad: 2.0` s). The case data is 60 WAVs, 30 unique dialogues: 2.32 h clean plus 2.32 h noisy,
2.4 to 9.6 min per call (measured locally from the WAV headers). Labels: 12 alarm, 14 no_alert and 4 review.

---

## Recommendation for our 4070

1. **Pick the transcript view with the oracle before training anything.** The `oracle` profile already
   gives perfect dialect text (the scripts). Run the checks on (a) the dialect scripts, (b) an LLM translation
   of them into Standard German and (c) English, with the same grouped folds (point 7). This shows how much
   the view itself matters at zero ASR error. Train a dialect ASR only if the dialect view clearly wins.
   - The **Standard German** view needs no ASR fine-tuning.
   - The **English** view needs no ASR fine-tuning either: translate the Standard German text with the LLM.
   - The **dialect** view needs fine-tuning. Whisper itself only writes standardised language
     ([STT4SG-350ASR paper](https://swissnlp.org/wp2020/wp-content/uploads/2025/09/STT4SG-350ASR-Transcribed_SwissGerman.pdf):
     Whisper "exclusively produces outputs in standardized languages"). A limited HF search found no public
     Whisper model that outputs Swiss German dialect text.
2. **Use LoRA, not a full fine-tune, on `openai/whisper-large-v3-turbo`** (or continue from
   `gcoli/whisper-large-v3-turbo-swiss-german-mit`, which is MIT and already adapted to Swiss German
   acoustics). The recipe below has been run on a 12 GB card: LoRA r=32, alpha=64 on `q_proj`/`v_proj`,
   lr 3e-4, linear decay, bf16, gradient checkpointing, batch 16. On a 12 GB RTX 3080 Ti it took about
   1.6 h for 80 h of audio ([gcoli card](https://huggingface.co/gcoli/whisper-large-v3-turbo-swiss-german-mit),
   [training_provenance.json](https://huggingface.co/gcoli/whisper-large-v3-turbo-swiss-german-mit/raw/main/training_provenance.json)).
   A full fine-tune of turbo with AdamW needs about 18 bytes per parameter, roughly 14.6 GB, before
   activations, so it does not fit in 12 GB. With 8-bit AdamW it is borderline (section 1.3).
3. **Train on 30 s windows with timestamp tokens, not on padded single sentences.** Put real timestamps
   in about 50 % of the samples and a previous-text prompt in about 50 %. Use i4ds `whisper-prep` to cut
   or concatenate the audio. This is the recipe of
   [arXiv 2412.15726](https://arxiv.org/abs/2412.15726), which shows that training on padded sentences
   breaks segmentation. Then check word timestamps against a forced alignment before trusting the snippets.
4. **Dialect data you can download this weekend:**
   - [`i4ds/swiss-german-city-sentences_v2`](https://huggingface.co/datasets/i4ds/swiss-german-city-sentences_v2)
     is synthetic TTS speech with both dialect and Standard German text. It is not gated, but its licence
     is "other" and unspecified.
   - Our 60 calls, used only through grouped cross-validation.

   SwissDial needs a web form. SDS-200 and STT4SG-350 need a signed licence sent by email, which will
   not arrive before Sunday.
5. **Integrity risk.** If an ASR is fine-tuned on the case scripts and then run on the same calls, it has
   memorised the content. The case README says "Do not feed ... scripts ... into your audio pipeline as
   hidden hints." Any number you report for an ASR trained on case data must come from a model that never
   saw that call's dialogue group (fold models). For the demo, prefer models trained only on public data,
   or ask the organisers.
6. **Convert for faster-whisper.** Merge the LoRA, copy the base `generation_config.json` (it holds the
   alignment heads), then run
   `ct2-transformers-converter --model <merged> --output_dir <out> --copy_files tokenizer.json preprocessor_config.json --quantization float16`.
   On the 4070, load the result with `compute_type="int8_float16"` or `"float16"`.
7. **Avoid leakage with 22 dialogue groups.** The groups are D01 to D10, the pairs C01+C02 up to C15+C16
   (near-identical "context pair" scripts), and C17 to C20. The clean and noisy recordings of a dialogue
   always stay in the same fold. Use GroupKFold with k=5.
8. **LLM: no QLoRA for the submission.** About 30 labelled dialogues (22 independent groups, 4 "review")
   are too few to tell a QLoRA gain from noise. The literature says few-shot fine-tuning and in-context
   learning generalise about equally, with large variance. A QLoRA of an 8B model does fit on 12 GB
   (Unsloth lists a 6 GB minimum), so it can be a post-hackathon experiment.
9. **Cheap fix you can make now, unrelated to training.** gcoli measured that faster-whisper's default
   `condition_on_previous_text=True` costs this model family 2.5 (turbo) to 11.7 (large) WER points on
   15-minute files ([gcoli card](https://huggingface.co/gcoli/whisper-large-v3-turbo-swiss-german-mit)).
   Our `config/base.yaml` leaves it at `true`.
10. **Licence note on the current ASR.** `nebi/...-ct2-int8` is tagged `apache-2.0`, but its card says it is
    "just a ct2-converted model of the original Flurin17/whisper-large-v3-turbo-swiss-german", and that
    model is **CC BY-NC 4.0**
    ([nebi card](https://huggingface.co/nebi/whisper-large-v3-turbo-swiss-german-ct2-int8),
    [Flurin17 card](https://huggingface.co/Flurin17/whisper-large-v3-turbo-swiss-german)). The licence-clean
    alternative is `gcoli/whisper-large-v3-turbo-swiss-german-mit` (MIT).

---

## 1. Memory and time (a)

### 1.1 Model facts

| Model | Params | Layers enc/dec | Mel bins | File (HF safetensors) | Licence | Source |
|---|---|---|---|---|---|---|
| openai/whisper-small | 244 M | 12/12 | 80 | about 1 GB | MIT | [HF blog](https://huggingface.co/blog/fine-tune-whisper) |
| openai/whisper-medium | 769 M | 24/24 | 80 | not checked | MIT | [HF blog](https://huggingface.co/blog/fine-tune-whisper) |
| openai/whisper-large-v3-turbo | 809 M | 32/**4** | 128 | 1,617,824,864 B (fp16) | MIT | [card](https://huggingface.co/openai/whisper-large-v3-turbo), [config.json](https://huggingface.co/openai/whisper-large-v3-turbo/raw/main/config.json) |
| openai/whisper-large-v3 | 1550 M | 32/32 | 128 | about 3.1 GB fp16 | MIT | [HF blog](https://huggingface.co/blog/fine-tune-whisper) |

Turbo "is the exact same model [as large-v3], except that the number of decoding layers have reduced
from 32 to 4" ([card](https://huggingface.co/openai/whisper-large-v3-turbo)). Most of the training cost is
therefore in the 32-layer encoder.

**Whisper always pads input to 30 s.** Training cost scales with the number of samples, not with the
hours of audio. "the GPU memory required by the models is the same for audio samples of any length"
([HF Whisper event README](https://github.com/huggingface/community-events/blob/main/whisper-fine-tuning-event/README.md)).
A 5 s sentence costs as much as a full 30 s window, so packing data into about 30 s windows is up to
6 times cheaper per hour of audio (and it is also what keeps the timestamps working, see section 2).

### 1.2 Measured data points from primary sources

| Who / what | Model, method | GPU | Settings | Data, time | Result |
|---|---|---|---|---|---|
| gcoli, turbo MIT ([card](https://huggingface.co/gcoli/whisper-large-v3-turbo-swiss-german-mit), [provenance](https://huggingface.co/gcoli/whisper-large-v3-turbo-swiss-german-mit/raw/main/training_provenance.json)) | turbo, LoRA r=32, alpha=64, dropout 0.05, `q_proj`+`v_proj`, merged | **RTX 3080 Ti 12 GB**, Windows 11 | lr 3e-4 linear, warmup 500, 1 epoch, batch 16, bf16, grad checkpointing | 40 h SPC v2 + 40 h Gemeinderat Zürich pseudo-labels; **about 1.6 h** | WER 23.7 / 25.9 (ASGDTS dev/final) vs 26.5 / 28.5 base; "lr 1e-3 produced no gain at all, 3e-4 gained 1.8 points" |
| gcoli, large-v3 MIT ([provenance](https://huggingface.co/gcoli/whisper-large-v3-swiss-german-mit/raw/main/training_provenance.json)) | large-v3, same LoRA | RTX 3080 Ti 12 GB | batch 8 x grad-accum 2, bf16, grad checkpointing | 20 h SPC + 80 h Zürich PL | WER 22.1 / 24.7 |
| Vaibhavs10 fast-whisper-finetuning ([README](https://github.com/Vaibhavs10/fast-whisper-finetuning)) | large-v2 in **8-bit** + LoRA r=32, alpha=64, `q_proj`/`v_proj` (15.7 M trainable, 1 %) | Colab T4 16 GB | lr 1e-3, warmup 50, 3 epochs, batch 8, fp16 | about 12 h Common Voice Hindi; "about 6-8 hours" | "less than 8GB GPU VRAM"; max batch 24 at 8 GB; full fine-tune "OOM on T4"; "~24GB of GPU VRAM for full fine-tuning" of large-v2 |
| HF blog ([fine-tune-whisper](https://huggingface.co/blog/fine-tune-whisper)) | small, full fine-tune | Colab (GPU not named) | batch 16, lr 1e-5, warmup 500, 5000 steps, fp16, grad checkpointing | about 8 h CV11 Hindi; "approximately 5-10 hours" | WER 63.5 -> 32.0 |
| HF Whisper event ([README](https://github.com/huggingface/community-events/blob/main/whisper-fine-tuning-event/README.md)) | small / medium, full fine-tune | V100 16 GB / A100 40 GB | V100: small batch 16 x accum 2, medium batch 2 x accum 16; A100: small 64, medium 32 | medium on V100: "upwards of 12 hours for 5k training steps"; small on A100 "approximately 8 hours" | lists 8-bit Adam (`optim="adamw_bnb_8bit"`), Adafactor and DeepSpeed ZeRO-2 as memory savers |
| i4ds paper ([arXiv 2412.15726](https://arxiv.org/abs/2412.15726) section 3.2) | large-v2, full fine-tune | A100 40 GB | batch 16 x accum 16 = 256, 8-bit optimizer, grad checkpointing on encoder and decoder, stochastic depth, mixed precision | 908 h; **about 42 h** | SOTA Swiss German (see section 2) |

### 1.3 VRAM budget on 12 GB

Bytes per parameter in mixed precision, from the HF guide
([model memory anatomy](https://huggingface.co/docs/transformers/model_memory_anatomy)):

- weights: 6 B (fp16 copy plus fp32 copy)
- AdamW states: 8 B (2 B with bitsandbytes 8-bit Adam)
- gradients: 4 B
- plus activations

The table applies these rules (all **estimates** except the gcoli rows).

| Setup | Trainable | Static memory | Fits 12 GB? | Batch suggestion |
|---|---|---|---|---|
| **turbo LoRA r=32 `q_proj`/`v_proj`**, frozen bf16 base, grad ckpt | 6.55 M (80 modules x 32 x 2560) | about 1.7 GB | **yes, measured** (gcoli, 12 GB, batch 16) | 8 x accum 2 (or 16 x 1) |
| turbo LoRA r=16 on `q,k,v,out_proj,fc1,fc2` | about 14 M | about 1.8 GB | yes (estimate) | 8 x accum 2 |
| large-v3 LoRA r=32 `q`/`v` | 15.7 M | about 3.3 GB | **yes, measured** (gcoli, batch 8 x accum 2) | 8 x accum 2 |
| turbo full fine-tune, AMP + AdamW fp32 | 809 M | 18 B/param, about 14.6 GB | **no** | - |
| turbo full fine-tune, AMP + `adamw_bnb_8bit` | 809 M | 10 to 12 B/param, about 8.1 to 9.7 GB | borderline (estimate) | 1-2 x accum 16-32, grad ckpt on; expect OOM tuning |
| turbo, encoder frozen, decoder full fine-tune + 8-bit Adam | about 172 M (4 dec layers + 66 M embeddings) | about 3 GB with the frozen fp16 encoder | yes (estimate); no backward pass through the encoder, so about 3x faster | 16-32 |
| small full fine-tune, AdamW | 244 M | about 4.4 GB | yes (V100 16 GB table: 16 x accum 2) | 16 |
| medium full fine-tune, AdamW | 769 M | about 13.8 GB | no; HF event used batch 2 x accum 16 on a **16 GB** V100 | only with 8-bit Adam |

Stop the vLLM server while training, because the two will not share 12 GB. bf16 works on the 4070
(Ada, compute capability 8.9). CTranslate2 keeps float16/bfloat16/int8_float16 natively on
CC >= 8.0 ([CT2 quantization docs](https://opennmt.net/CTranslate2/quantization.html)).

### 1.4 Hours per epoch on the 4070 (estimate)

Anchor: gcoli trained turbo LoRA on 80 h for one epoch in about 1.6 h on a 12 GB RTX 3080 Ti. The card
does not give the sample lengths. If its samples averaged 10 to 30 s, that is 9,600 to 28,800 samples,
i.e. about 1.7 to 5 samples/s. A rough FLOP check (6 x 635 M encoder params x 1500 frames, about
6 to 7 TFLOP per 30 s sample, at 20 to 25 effective TFLOPS) gives about 3 samples/s, which agrees.
The RTX 4070 (5,888 CUDA cores, 192-bit bus, per the
[NVIDIA spec page](https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4070-family/)) is in the
same class as the 3080 Ti; I did not check the 3080 Ti's spec page. For turbo LoRA I therefore assume
**1.5 to 4 samples/s**, and **all values below are estimates**.

| Audio per epoch | Packed 30 s windows | Hours/epoch, packed | Sentence-level, 5 s mean (SDS-200/STT4SG style) | Hours/epoch, sentences |
|---|---|---|---|---|
| our calls, 4.64 h | about 560 | **0.04-0.1 h (2-6 min)** | - | - |
| 5 h | 600 | 0.04-0.11 h | 3,600 | 0.25-0.7 h |
| 20 h | 2,400 | 0.17-0.45 h | 14,400 | 1-2.7 h |
| 50 h | 6,000 | **0.4-1.1 h** | 36,000 | 2.5-6.7 h |

- A full fine-tune (weight gradients for all layers) costs about 1.3x more (estimate).
- The frozen-encoder variant costs about 0.35x (estimate).
- whisper-small is about 5 to 7 times cheaper per sample (encoder about 88 M vs 635 M params, estimate).
  Its zero-shot Swiss German is much weaker, so it is only worth it for fast pipeline debugging.
- medium costs about 0.5x of turbo per sample (estimate) and is not better than turbo, so there is no
  reason to pick it.
- Generation-based evaluation inside the HF Trainer (`predict_with_generate`) is slow. Evaluate a few
  hundred windows every N steps, or evaluate with faster-whisper after conversion.

**Conclusion for (a):** compute is not the bottleneck this weekend; labelled data and evaluation are.
Several 5-fold LoRA runs on our calls, plus one run of a few tens of hours of public data, fit into one
night.

---

## 2. The timestamp problem (b)

### 2.1 What arXiv 2412.15726 shows

Timmel, Paonessa, Kakooee, Vogel and Perruchoud (FHNW i4ds), "Fine-tuning Whisper on Low-Resource
Languages for Real-World Applications", [arXiv 2412.15726](https://arxiv.org/abs/2412.15726) (v3, Apr 2025,
[HTML](https://arxiv.org/html/2412.15726v3)):

- **The problem.** Their Table 1 shows that Whisper large-v2 fine-tuned on sentence-level data "fails to
  predict timestamps and performs worse than the original Large-v2" on long audio. Section 3.1 explains
  why: sentence datasets (SPC, SDS-200, STT4SG-350) need heavy padding to fill 30 s, which risks
  "compromising the model's ability to robustly handle long-form audio and predict timestamps".
- **Table 5, measured with WhisperX, beam 5 and VAD.** On the STT4SG-350 test set, the sentence-level
  model scores **best in-domain** (BLEU 77.38 vs 76.55 for long-form "All" and 64.15 for base large-v2).
  On real long-form audio it collapses:
  - SRG (Swiss TV) SubER: **51.34** for sentence-level, 41.64 for "All", 30.63 for base.
  - Dataset-A (a real phone call): BLEU **35.01** for sentence-level, 47.22 for "All", 48.89 for base.

  Note that Dataset-A is a doctor-patient **phone call**, the closest public result to our domain. Even
  their long-form-trained model only roughly matched the base model there, until they added
  in-distribution data (Table 6: WER 34.50 vs 38.00, SubER 35.31 vs 39.12).
- **The recipe (section 3.1, `whisper-prep`):**
  - Concatenate sentence clips into long-form audio plus an SRT file.
  - Correct the start and end times with Silero VAD.
  - Overlap the non-speech parts by up to 200 ms; 50 % chance.
  - "Negative overlap" (speech overlapping by 200 ms); 10 % chance.
  - Keep the same speaker for consecutive clips with 50 % probability.
  - Cut into 30 s windows with `<|t|>` tokens.
- **Training (sections 3.2 and 4.4):**
  - each sample has a 50 % chance of timestamps and a 50 % chance of a previous-text prompt (after
    [openai/whisper#838](https://github.com/openai/whisper/discussions/838), where jongwook confirms
    "`<|notimestamps|>` was used 50% of the samples")
  - SpecAugment and stochastic depth
  - AdamW, max lr 2e-4, weight decay 0.1, 128 warmup steps, betas 0.9/0.98, eps 1e-9
  - to limit forgetting they added 125 h of Common Voice 13 German, also cut into 30 s windows, and
    406 h of pseudo-labelled Swiss TV
- **Code:**
  - [i4ds/Whisper-prep](https://github.com/i4ds/Whisper-prep) (MIT): concatenates sentences and also
    cuts existing SRT/VTT plus audio into 30 s windows with `<|0.00|>text<|1.50|>` labels (its "Option B/C").
  - [i4ds/Whisper-finetune](https://github.com/i4ds/Whisper-finetune) (MIT): LoRA, timestamp and prompt
    training, 8-bit AdamW, gradient checkpointing, conversion to CT2.

**Trap in i4ds/Whisper-finetune:** its README warns that `no_timestamp_training: True` overrides
`no_timestamp_rate`, so "that combination trains with no timestamps at all". The repo's own
[`configs/config_turbo_best.yaml`](https://github.com/i4ds/Whisper-finetune/blob/main/configs/config_turbo_best.yaml)
sets exactly that combination. Set `no_timestamp_training: False` and `no_timestamp_rate: 0.5`. The README
also explains why WER does not catch the bug: "WER does not move ... only the timings are wrong".

### 2.2 How faster-whisper produces our timestamps (read from the code)

- **Segment boundaries** come from the predicted timestamp tokens. The i4ds README warns that a model
  trained without timestamps can "emit full-width 30 second segments on long audio". faster-whisper's
  sequential `WhisperModel.transcribe` uses the same seek logic over timestamp tokens.
  The seek position is also advanced from the last word end only when word timestamps are on
  ([transcribe.py](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py),
  `if not single_timestamp_ending: ... seek = round(last_word_end * ...)`).
- **Word timestamps** do not come from timestamp tokens. They come from DTW over the cross-attention of
  the model's **alignment heads**: `find_alignment` calls `self.model.align(...)`. For turbo these heads
  are `[[2,4],[2,11],[3,3],[3,6],[3,11],[3,14]]`
  ([generation_config.json](https://huggingface.co/openai/whisper-large-v3-turbo/raw/main/generation_config.json)).
  The CT2 converter copies `alignment_heads` from `generation_config`. If that is missing it falls back to
  "the last half layers" with all heads
  ([converter source](https://github.com/OpenNMT/CTranslate2/blob/master/python/ctranslate2/converters/transformers.py),
  `WhisperLoader.set_config`). The nebi, gcoli and Flurin17 Swiss German models all still carry the base
  turbo heads (I checked their config files).
- `BatchedInferencePipeline.transcribe` defaults to `without_timestamps=True` and `vad_filter=True`.
  Segments come from VAD chunks of at most 30 s, so segmentation does **not** depend on predicted
  timestamp tokens.

### 2.3 What to do so word timestamps keep working

1. Train on **30 s windows with timestamp tokens** (50 %) and `<|notimestamps|>` (50 %), with a 50 %
   previous-text prompt. Include windows where a segment is cut by the window edge (whisper-prep handles
   this: a trailing start-only timestamp).
2. Mix in **public long-form replay data with timestamps**, about 1:1 with in-domain data:
   [`i4ds/spc_r_whisper`](https://huggingface.co/datasets/i4ds/spc_r_whisper). It has 74,083 rows already
   in `<|t|> text <|t|>` format with a `prompt` column; I inspected rows via the datasets-server. This
   follows the paper's anti-forgetting step (section 4.4).
3. Keep LoRA small (r=32, `q_proj`/`v_proj`), lr 3e-4, 1 to 3 epochs, and pick the best checkpoint. The
   Flurin17 card shows over-fitting after step 750: WER 37.96, then 42.92 at 1000.
4. **Untested idea:** the alignment heads are decoder cross-attention heads (`encoder_attn`) in layers
   2-3. If word timestamps degrade, try a LoRA that excludes `encoder_attn` (PEFT `target_modules`
   regex on `encoder.layers.*.self_attn` and `decoder.layers.*.self_attn`) and compare.
5. Always keep the base `generation_config.json` next to the merged weights before conversion.
6. At inference, use VAD (`vad_filter=True`) or `BatchedInferencePipeline` together with
   `word_timestamps=True`, so segmentation does not rely on timestamp tokens. Set
   `condition_on_previous_text=False` (gcoli's long-form finding).
7. **Check it** on a held-out fold. Compare each fine-tuned model's word start times with a CTC forced
   alignment of the script (section 3.3). Our snippets are padded by 2 s, so a reasonable pass criterion
   is a median |Δstart| under 0.3 s, 95 % of words within 1 s, and no segment longer than 25 s
   (my own threshold, not from a source).

---

## 3. Data (c)

### 3.1 Swiss German corpora: access as of 2026-10-09

| Corpus | Hours | Text it provides | Licence (primary) | Access | Usable by Sunday? |
|---|---|---|---|---|---|
| **SPC v1/v2** (Grosser Rat Bern) | 70 / **293** h train | Standard German | **MIT** | direct Dropbox links on [FHNW i4ds datasets](https://www.cs.technik.fhnw.ch/i4ds-datasets) | yes |
| **SPC_R** [`i4ds/spc_r`](https://huggingface.co/datasets/i4ds/spc_r) | **555 h** (525 train / 30 test), 12,900 + 679 multi-minute rows with an `srt` column | Standard German (Whisper large-v3 output corrected by GPT-4o with RAG, [arXiv 2506.07726](https://arxiv.org/abs/2506.07726)) | **CC BY 4.0** (the card wrongly adds "share-alike") | HF, **not gated**, 6.04 GB | yes |
| [`i4ds/spc_r_whisper`](https://huggingface.co/datasets/i4ds/spc_r_whisper) | 74,083 windows of 30 s or less | Standard German with `<|t|>` tokens and a `prompt` column | **not stated** on the card (derived from SPC_R, CC BY 4.0) | HF, not gated, 6.4 GB | yes (best replay set) |
| All Swiss German Dialects Test Set | 13 h | Standard German (text from Common Voice DE) | **MIT** | Dropbox, [FHNW page](https://www.cs.technik.fhnw.ch/i4ds-datasets) | yes (good regression test; gcoli uses speaker-disjoint dev/final halves) |
| Gemeinderat Zürich | 1,208 h | **none** (audio only) | MIT | Dropbox, [FHNW page](https://www.cs.technik.fhnw.ch/i4ds-datasets) | yes, but needs pseudo-labels (gcoli recipe) |
| **SDS-200** | 200 h | Standard German | **META-SHARE ResearchUsageOnly NoRedistribution**; commercial use by arrangement | "send the completed and signed license file to info@swissnlp.org" ([swissnlp.org/datasets](https://swissnlp.org/datasets/)) | **no** (manual approval) |
| **STT4SG-350** | 343 h, 247,527 recordings, mean 5.0 s | Standard German | same META-SHARE research licence ([swissnlp](https://swissnlp.org/datasets/)); the paper says NonCommercial NoRedistribution ([arXiv 2305.18855](https://arxiv.org/abs/2305.18855)) | signed form by email | **no** |
| STT4SG-350-ASR | (transcripts only) | **dialect** text, automatic (wav2vec2 trained on SwissDial 1.1) | CC BY 3.0 CH | direct download ([swissnlp](https://swissnlp.org/datasets/)) | **useless without the STT4SG-350 audio** |
| **SwissDial** v1.1 | about 3 h per dialect, 8 dialects (AG, BE, BS, GR, LU, SG, VS, ZH); 30,921 files, 11,213 unique DE sentences ([STT4SG-350ASR paper](https://swissnlp.org/wp2020/wp-content/uploads/2025/09/STT4SG-350ASR-Transcribed_SwissGerman.pdf)) | **dialect + Standard German**, one speaker per dialect, clean ([arXiv 2103.11401](https://arxiv.org/abs/2103.11401)) | **not stated** on the [project page](https://mtc.ethz.ch/publications/open-source/swiss-dial.html) or the form; HF stubs and the gcoli card call it CC BY-NC (secondary) | [JotForm](https://form.jotform.com/223344961502048) (name, organisation, intended use); unknown whether approval is automatic | maybe (submit the form now) |
| [`i4ds/swiss-german-city-sentences_v2`](https://huggingface.co/datasets/i4ds/swiss-german-city-sentences_v2) | 54,098 rows, 16.1 GB (roughly 70 to 140 h, estimate) | **dialect (`sentence_ch`) + Standard German (`sentence_de`)**, `dialect_code` | `license: other`, **no terms given** | HF, **not gated** | yes, for experiments; the licence is unclear |
| ArchiMob R2 | not verified | dialect transcription with normalisation | CC BY-NC-SA 4.0 | SWISSUbase DOIs ([UZH page](https://www.spur.uzh.ch/en/research/projects-all/lab-projects/ArchiMob0.html)); registration not verified | unclear |
| SwissGPC (podcasts) | 7,765 + 989 h | weak labels via a pipeline | repo licence | pipeline only, no audio ([swissnlp](https://swissnlp.org/datasets/)) | no |

- None of SDS-200, STT4SG-350 or SwissDial is on the HF hub. A search found only empty stubs, such as
  `buenavista62/swissdial_dataset_v1_1`, which holds just a README.
- The i4ds turbo training config also lists `i4ds/SRG_V4_whisper-prep_v2` and `i4ds/sg_corpus_whisper_v2`.
  Neither is in the public i4ds dataset list, so I treat them as private.

### 3.2 Target text: dialect or Standard German?

- **Standard German target.** All large public corpora use it: SPC, SPC_R, SDS-200, STT4SG-350.
  Off-the-shelf models already output it (nebi/Flurin17, gcoli). WER and BLEU are comparable across
  papers, and LLMs have far more Standard German training text. **No fine-tuning is needed for this view.**
- **Dialect target.** There is no standard orthography: SwissDial asked one annotator per dialect to
  translate, because "there is no official standard orthography"
  ([arXiv 2103.11401](https://arxiv.org/abs/2103.11401) section 3.1). Our scripts are one more
  orthography.
  - Freely usable data: city-sentences v2 (synthetic, licence unclear), SwissDial (form; 8 single
    speakers; likely non-commercial) and our scripts (only about 2.3 h unique audio).
  - Score dialect output with **CER** or a spelling-normalised WER; plain WER penalises valid spellings.
  - **Recommendation:** train dialect output as a **separate model** (its own LoRA, its own CT2 folder).
    Do not mix the two targets under the same `<|de|>` token, or the model will be pulled between two
    spellings for the same audio.
  - **Untested idea:** a single model could use a reused language token for dialect output.
- Our case audio is synthetic TTS, and so is city-sentences v2. That may be a domain match or a trap
  (TTS artefacts). Only the held-out folds will tell.

### 3.3 Our 60 calls: cutting long calls into 30 s training windows without gold timestamps

Facts measured locally:

- The noisy versions are **1.6 to 4.0 s longer** than the clean ones, for all 30 pairs. The scripts list
  planned noise events (e.g. "Glocke T002"), so clean timings **cannot** be copied to the noisy file.
  Align each WAV separately.
- The scripts have turn headers (`T001 · Beratung`). The case README warns that they are "not verified
  transcriptions".

Options, best first:

1. **CTC forced alignment of the dialect script** with
   [ctc-forced-aligner](https://github.com/MahmoudAshraf97/ctc-forced-aligner) (code BSD-2-Clause) and its
   default [`MahmoudAshraf/mms-300m-1130-forced-aligner`](https://huggingface.co/MahmoudAshraf/mms-300m-1130-forced-aligner)
   (1.26 GB, **CC BY-NC 4.0**; fine for internal data prep, do not ship it). The command is
   `ctc-forced-aligner --audio_path call.wav --text_path turns.txt --language deu --romanize --split_size sentence`.
   - Romanisation (uroman) makes umlaut and dialect spellings acoustically usable.
   - `<star>` tokens (`--star_frequency`) absorb noise and wording that differs from the script.
   - Low per-segment scores flag places where the speech does not follow the script; drop those windows.
   - Using `deu` for Swiss German is my choice; I did not verify it against a gsw list.
2. **Apache-licensed aligner:** the same tool with `--alignment_model jonatasgrosman/wav2vec2-large-xlsr-53-german`
   ([Apache-2.0](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-german)) and no romanisation.
   Its German character set covers the dialect spellings. Quality on Swiss German speech is **unverified**.
3. **Whisper-based text alignment:** [stable-ts](https://github.com/jianfch/stable-ts) (MIT)
   `model.align(audio, text, language="de")` aligns arbitrary plain text with Whisper cross-attention.
   I did not verify that it works on dialect text or with a faster-whisper backend.
4. **No extra model:** use our ASR's segment and word timestamps (Standard German) plus diarizer speaker
   changes. Map script turns to ASR spans in order, using speaker alternation and fuzzy matches on
   names, numbers and cognates. This gives turn-level boundaries, which is enough to pack whole turns
   into windows of 30 s or less. Turns longer than 30 s still need option 1.

Then:

1. Write one SRT per WAV with sentence-level cues.
2. Run whisper-prep "Option B/C" (existing SRT + audio) with `netflix_normalize: false` and
   `cut_initial_audio: true`. It cuts 30 s windows with `<|t|>` labels and previous-text prompts.
3. Listen to 10 random windows per fold before training.

**Avoiding leakage.** Use GroupKFold over **22 dialogue groups** (from the script titles):

- D01 to D10: 10 groups, each the K1+K2 recordings
- {C01,C02}, {C03,C04}, ..., {C15,C16}: 8 groups, each 4 recordings. The pairs share the title, the
  scenario and about the same word count (C01: 326 words, C02: 324).
- C17 to C20: 4 groups, each K3+K4

Rules:

- Use k=5 folds, stratified on the label as far as the groups allow.
- Never split clean from noisy, or a context pair.
- Prompts may only use text from the same call.
- Synthetic voices may recur across dialogues. This speaker leakage cannot be removed, so report it.
- The same grouping applies to LLM few-shot examples. An in-context example drawn from C06 while
  scoring C05 is leakage.

---

## 4. Converting to CTranslate2 for faster-whisper (d)

```bash
# 1) merge LoRA (PEFT) and save a plain transformers checkpoint
python - <<'EOF'
from transformers import WhisperForConditionalGeneration, WhisperProcessor, GenerationConfig
from peft import PeftModel
base = "openai/whisper-large-v3-turbo"          # or the checkpoint you started from
m = WhisperForConditionalGeneration.from_pretrained(base, torch_dtype="float16")
m = PeftModel.from_pretrained(m, "runs/lora-best").merge_and_unload()
m.save_pretrained("export/gsw-turbo-merged", safe_serialization=True)
WhisperProcessor.from_pretrained(base).save_pretrained("export/gsw-turbo-merged")   # tokenizer.json + preprocessor_config.json
GenerationConfig.from_pretrained(base).save_pretrained("export/gsw-turbo-merged")    # keeps alignment_heads, lang_to_id
EOF

# 2) convert (faster-whisper README command)
ct2-transformers-converter --model export/gsw-turbo-merged --output_dir export/gsw-turbo-ct2 \
  --copy_files tokenizer.json preprocessor_config.json --quantization float16
```

- Command and flags as in the
  [faster-whisper README, "Model conversion"](https://github.com/SYSTRAN/faster-whisper#model-conversion).
- Quantisation values: `int8`, `int8_float32`, `int8_float16`, `int8_bfloat16`, `int16`, `float16`,
  `bfloat16`, `float32`. "Quantization can also be enabled or changed when loading the model"
  ([CT2 docs](https://opennmt.net/CTranslate2/quantization.html)). Convert once to `float16`, then load
  with `compute_type="int8_float16"` on the 4070 and `int8` on the laptop CPU.
- gcoli reports that `int8_float16` costs about 0.3 WER points on this model family.
- **Why both copy files matter (read from the code):**
  - Without `tokenizer.json`, faster-whisper loads `openai/whisper-tiny`'s tokenizer. Tiny's vocabulary
    has 51,865 tokens, but v3 and turbo have 51,866.
  - Without `preprocessor_config.json`, the `FeatureExtractor` defaults to `feature_size=80`, but
    v3 and turbo need **128** mel bins
    ([transcribe.py](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py),
    [feature_extractor.py](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/feature_extractor.py),
    [config.json](https://huggingface.co/openai/whisper-large-v3-turbo/raw/main/config.json)).
  - The nebi export passed `--copy_files preprocessor_config.json generation_config.json` but no
    `tokenizer.json`, which is why our download script fetches it separately.
- If you trained with i4ds/Whisper-finetune (openai-whisper `.pt` format), use its
  `convert_openai_to_hf` + `TransformersConverter(copy_files=["tokenizer.json", ...])` path in
  [`wandb_to_ct2_upload.py`](https://github.com/i4ds/Whisper-finetune/blob/main/src/whisper_finetune/scripts/wandb_to_ct2_upload.py).

Versions on PyPI on 2026-10-09: faster-whisper 1.2.1 (MIT), ctranslate2 4.8.2 (MIT), transformers 5.19.0,
peft 0.21.2, bitsandbytes 0.50.2. Not tested together.

---

## 5. LLM side: QLoRA of a 7-8B model or few-shot? (e)

**Evidence.** None of these studies is on our task, and none uses about 30 long dialogues.

| Study | Finding |
|---|---|
| Mosbach et al., "Few-shot Fine-tuning vs. In-context Learning: A Fair Comparison and Evaluation", Findings ACL 2023 ([arXiv 2305.16938](https://arxiv.org/abs/2305.16938)) | Controlled comparison, 125 M to 30 B params: "both approaches generalize similarly; they exhibit large variation". |
| Liu et al., T-Few, NeurIPS 2022 ([arXiv 2205.05638](https://arxiv.org/abs/2205.05638), [proceedings](https://proceedings.neurips.cc/paper_files/paper/2022/hash/0cde695b83bd186c1fd456302888454c-Abstract-Conference.html)) | Few-shot PEFT ((IA)³ on T0) beats ICL in accuracy and cost on RAFT classification. That needs a careful recipe, and the tasks are short-text classification. |
| Bertsch et al., NAACL 2025 ([arXiv 2405.00200](https://arxiv.org/abs/2405.00200)) | "finetuning is more data hungry than ICL but can exceed long-context ICL performance with additional data". |

**Our situation:**

- There are 30 dialogues, but only 22 independent groups, and only 4 "review" examples.
- The Stufe2 pairs differ only in context, which is exactly what a QLoRA on 30 examples would memorise.
- Each test fold holds 4 to 5 groups, so one fold swings precision and recall by about 20 points
  (estimate). No QLoRA gain will be measurable this weekend.

**Recommendation:**

- Use the labelled dialogues as (a) grouped-CV data to tune the criteria prompts and fusion thresholds,
  and (b) a pool of few-shot exemplars drawn from the training folds only.
- Spend GPU time on self-consistency sampling, which the `gpu` profile already does with 5 samples at
  T=0.7, not on QLoRA.

**If you try QLoRA anyway:**

- Memory: Unsloth lists **6 GB minimum for 8B QLoRA** and 22 GB for 16-bit LoRA
  ([Unsloth requirements](https://unsloth.ai/docs/get-started/beginner-start-here/unsloth-requirements)).
  QLoRA itself was introduced as fitting 65 B on one 48 GB GPU ([arXiv 2305.14314](https://arxiv.org/abs/2305.14314)).
- Our transcripts are 1.9 to 7.9 k characters, so a 4 k-token sequence is enough. At batch 1 with
  gradient checkpointing, expect about 8 to 10 GB on the 4070 (estimate). Training is about 30 x 3 k
  tokens x 3 epochs, roughly 270 k tokens, i.e. minutes (estimate).
- Serving: vLLM serves adapters with `--enable-lora --lora-modules name=path --max-lora-rank <r>`
  ([vLLM LoRA docs](https://docs.vllm.ai/en/latest/features/lora.html)). The repo has an example of LoRA on
  bitsandbytes, AWQ and GPTQ quantised bases; bitsandbytes "requires installing vllm-bnb-plugin"
  ([example](https://github.com/vllm-project/vllm/blob/main/examples/features/lora/lora_with_quantization_offline.py)).
- Train one adapter per fold and report CV numbers, never numbers on the training dialogues.

---

## 6. Concrete recipe for the 4070

### 6.1 Dialect-output ASR, the only ASR worth training this weekend

1. **Data, all packed to 30 s windows with whisper-prep:**
   - **public:** `i4ds/swiss-german-city-sentences_v2` with `sentence_ch` as the target.
     - Prefer the ZH, AG and similar codes. Our scripts look Zurich-like; I did not verify this.
     - Take about 20 to 40 h subsampled.
     - Use the sentence-fusion config with `maintain_speaker_chance: 0.5`, `overlap_chance: 0.5`,
       `max_overlap_duration: 0.2` and `n_samples_per_srt: 16` (values from the whisper-prep README).
     - Add SwissDial if the form is approved in time.
   - **in-domain:** our calls, aligned and cut as in section 3.3, used **only** in 5-fold group CV.
   - **eval:** the held-out fold (dialect CER, plus a word-timestamp check against forced alignment).
2. **Model:** start from `openai/whisper-large-v3-turbo` (MIT). Optionally start from
   `gcoli/whisper-large-v3-turbo-swiss-german-mit` (MIT, already Swiss German acoustics); A/B the two.
3. **LoRA:** r=32, alpha=64, dropout 0.05, `target_modules=["q_proj","v_proj"]` (gcoli and Vaibhavs10).
   Variant: r=16 on `q,k,v,out_proj,fc1,fc2`, for more capacity to learn a new orthography.
4. **Optimisation** (lr from gcoli: 1e-3 gave nothing, 3e-4 worked):
   - `learning_rate=3e-4`, linear decay, `warmup_ratio=0.05`, `weight_decay=0.0`
   - `per_device_train_batch_size=8`, `gradient_accumulation_steps=2`
   - `bf16=True`, `gradient_checkpointing=True` with `gradient_checkpointing_kwargs={"use_reentrant": False}`
   - `num_train_epochs=2-3`, eval and save every about 200 steps, `load_best_model_at_end` on CER
   - `model.config.apply_spec_augment=True`, `mask_time_prob=0.05` (fields from
     [WhisperConfig](https://github.com/huggingface/transformers/blob/main/src/transformers/models/whisper/configuration_whisper.py))
   - `use_cache=False`
5. **Labels:**
   - Build them as `<|startoftranscript|><|de|><|transcribe|>` + (50 %: timestamped text `<|0.00|> ... <|3.20|>`,
     50 %: `<|notimestamps|>` + plain text) + `<|endoftext|>`. The v3/turbo tokenizer has all
     `<|0.00|>`...`<|30.00|>` tokens as added tokens (ids 50365 to 51865,
     [added_tokens.json](https://huggingface.co/openai/whisper-large-v3-turbo/raw/main/added_tokens.json)),
     and `WhisperTokenizer.set_prefix_tokens(..., predict_timestamps=...)` exists
     ([tokenization_whisper.py](https://github.com/huggingface/transformers/blob/main/src/transformers/models/whisper/tokenization_whisper.py)).
   - In 50 % of samples, prepend `<|startofprev|>` + the previous window's text, at most 223 tokens, and
     mask its labels with -100.
   - The HF default collator does none of this; you must write a custom one.
   - Lower-risk alternative: use **i4ds/Whisper-finetune** (it implements all of this) with
     `model.lora: True`, `batch_size: 8`, `accum_grad_steps: 4`, `optimizer.8bit: True`, both
     gradient-checkpointing flags `True`, `no_timestamp_training: False`, `no_timestamp_rate: 0.5`,
     `prompt_use_rate: 0.5`, `mp_dtype: bfloat16`.
     - Memory at batch 8 on 12 GB is unverified (estimate: fits).
     - It needs `wandb`; run it with `WANDB_MODE=offline`.
6. **Expected time** (estimate): 30 h packed is about 3,600 windows, so 15 to 40 min per epoch. One
   5-fold CV on our calls takes about 5 x 5 min. Total under 3 h.
7. **Export:** follow section 4, then add a profile with `asr.model: models/asr/gsw-dialect-turbo-ct2`,
   `compute_type: int8_float16` and `condition_on_previous_text: false`.

### 6.2 Standard German ASR (optional; probably skip)

Only do this if the Standard German view wins and ASR errors are the bottleneck (check with the oracle).

- Same LoRA recipe on [`i4ds/spc_r_whisper`](https://huggingface.co/datasets/i4ds/spc_r_whisper)
  (Standard German, already 30 s windows with timestamps and prompts) plus our calls with LLM-translated
  Standard German targets (CV only).
- Start from gcoli turbo MIT.
- Expect small gains: gcoli got 2.8 WER points over base turbo, and Flurin17 6.5 points on its own
  training-regime sample.

### 6.3 Full fine-tune variant, only if LoRA plateaus

- turbo with an **encoder-frozen** decoder fine-tune (`model.model.encoder.requires_grad_(False)`)
- `optim="adamw_bnb_8bit"`, lr 1e-5 (HF blog value for full fine-tunes), batch 16
- fits easily (estimate)
- A full encoder+decoder fine-tune on 12 GB needs batch 1-2 x accum 16+ and 8-bit Adam, and is likely to
  OOM. Not recommended this weekend.

---

## 7. Not verified / open questions

- The hours per epoch on an RTX 4070 are extrapolated from one 3080 Ti run plus FLOP arithmetic. Measure
  the first 50 steps and rescale.
- SwissDial licence: neither the paper, the project page nor the form states one. "CC BY-NC" comes from
  secondary sources. Approval latency is unknown.
- The `i4ds/swiss-german-city-sentences_v2` licence is "other" with no text. Its hours are an estimate
  from the parquet size, and its TTS origin is unknown.
- `i4ds/spc_r_whisper` has no licence field. I assume it inherits CC BY 4.0 from SPC_R; not confirmed.
- ArchiMob size and SWISSUbase registration were not checked.
- How well word timestamps (alignment-head DTW) survive LoRA on Swiss German is not measured anywhere I
  found. That is why the check in section 2.3 is mandatory.
- MMS (uroman) or the German wav2vec2 aligner on Swiss German dialect text: no published accuracy found.
- vLLM LoRA on AWQ/GPTQ bases is shown only in an example script, and the docs page does not state it.
  The bitsandbytes route needs a plugin.
- No evidence was found on whether LLM checks are more accurate on Swiss German dialect text than on
  Standard German. The oracle experiment in recommendation 1 is the way to find out.

---

## Sources

Papers

1. Timmel et al., Fine-tuning Whisper on Low-Resource Languages for Real-World Applications, arXiv 2412.15726 - https://arxiv.org/abs/2412.15726 (HTML v3: https://arxiv.org/html/2412.15726v3)
2. Timmel et al., Swiss Parliaments Corpus Re-Imagined (SPC_R), arXiv 2506.07726 - https://arxiv.org/abs/2506.07726
3. Plüss et al., SDS-200, LREC 2022, arXiv 2205.09501 - https://arxiv.org/abs/2205.09501
4. Plüss et al., STT4SG-350, ACL 2023, arXiv 2305.18855 - https://arxiv.org/abs/2305.18855
5. Dogan-Schönberger et al., SwissDial, arXiv 2103.11401 - https://arxiv.org/abs/2103.11401
6. Pilz & Schneider, STT4SG-350ASR - https://swissnlp.org/wp2020/wp-content/uploads/2025/09/STT4SG-350ASR-Transcribed_SwissGerman.pdf
7. Mosbach et al., Few-shot Fine-tuning vs. In-context Learning, Findings ACL 2023 - https://arxiv.org/abs/2305.16938
8. Liu et al., Few-Shot PEFT is Better and Cheaper than ICL (T-Few), NeurIPS 2022 - https://arxiv.org/abs/2205.05638 ; https://proceedings.neurips.cc/paper_files/paper/2022/hash/0cde695b83bd186c1fd456302888454c-Abstract-Conference.html
9. Bertsch et al., In-Context Learning with Long-Context Models, NAACL 2025 - https://arxiv.org/abs/2405.00200
10. Dettmers et al., QLoRA, arXiv 2305.14314 - https://arxiv.org/abs/2305.14314
11. Akeret, Subtitle-Aligned Fine-Tuning of Whisper for Swiss German ASR, arXiv 2606.07608 - https://arxiv.org/abs/2606.07608 (context only)
12. D'Intino & Hutter, SRB-300, arXiv 2506.08836 - https://arxiv.org/abs/2506.08836 (context only; dataset access not stated)

Model cards and configs

13. openai/whisper-large-v3-turbo - https://huggingface.co/openai/whisper-large-v3-turbo ; config.json, generation_config.json, added_tokens.json under /raw/main/
14. openai/whisper-tiny config (vocab 51865, 80 mels) - https://huggingface.co/openai/whisper-tiny/raw/main/config.json
15. gcoli/whisper-large-v3-turbo-swiss-german-mit - https://huggingface.co/gcoli/whisper-large-v3-turbo-swiss-german-mit ; https://huggingface.co/gcoli/whisper-large-v3-turbo-swiss-german-mit/raw/main/training_provenance.json
16. gcoli/whisper-large-v3-swiss-german-mit - https://huggingface.co/gcoli/whisper-large-v3-swiss-german-mit/raw/main/training_provenance.json
17. Flurin17/whisper-large-v3-turbo-swiss-german - https://huggingface.co/Flurin17/whisper-large-v3-turbo-swiss-german
18. nebi/whisper-large-v3-turbo-swiss-german-ct2-int8 - https://huggingface.co/nebi/whisper-large-v3-turbo-swiss-german-ct2-int8
19. MahmoudAshraf/mms-300m-1130-forced-aligner - https://huggingface.co/MahmoudAshraf/mms-300m-1130-forced-aligner
20. jonatasgrosman/wav2vec2-large-xlsr-53-german - https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-german

Datasets and access pages

21. FHNW i4ds datasets (SPC, ASGDTS, Gemeinderat Zürich) - https://www.cs.technik.fhnw.ch/i4ds-datasets
22. SwissNLP datasets (SDS-200, STT4SG-350, STT4SG-350-ASR, SwissGPC) - https://swissnlp.org/datasets/
23. i4ds/spc_r - https://huggingface.co/datasets/i4ds/spc_r
24. i4ds/spc_r_whisper - https://huggingface.co/datasets/i4ds/spc_r_whisper
25. i4ds/swiss-german-city-sentences_v2 - https://huggingface.co/datasets/i4ds/swiss-german-city-sentences_v2
26. SwissDial project page - https://mtc.ethz.ch/publications/open-source/swiss-dial.html ; form https://form.jotform.com/223344961502048
27. ArchiMob - https://www.spur.uzh.ch/en/research/projects-all/lab-projects/ArchiMob0.html

Code and docs

28. i4ds/Whisper-prep - https://github.com/i4ds/Whisper-prep
29. i4ds/Whisper-finetune - https://github.com/i4ds/Whisper-finetune (configs/config_turbo_best.yaml, configs/example_config.yaml, src/whisper_finetune/scripts/wandb_to_ct2_upload.py)
30. faster-whisper README and transcribe.py / feature_extractor.py - https://github.com/SYSTRAN/faster-whisper
31. CTranslate2 Transformers converter (WhisperLoader) - https://github.com/OpenNMT/CTranslate2/blob/master/python/ctranslate2/converters/transformers.py
32. CTranslate2 quantization docs - https://opennmt.net/CTranslate2/quantization.html
33. HF blog, Fine-Tune Whisper - https://huggingface.co/blog/fine-tune-whisper
34. HF Whisper fine-tuning event README - https://github.com/huggingface/community-events/blob/main/whisper-fine-tuning-event/README.md
35. HF transformers, GPU memory anatomy - https://huggingface.co/docs/transformers/model_memory_anatomy
36. HF transformers Whisper tokenizer / config source - https://github.com/huggingface/transformers/tree/main/src/transformers/models/whisper
37. Vaibhavs10/fast-whisper-finetuning - https://github.com/Vaibhavs10/fast-whisper-finetuning
38. openai/whisper discussion #838 (timestamp/prompt training mix) - https://github.com/openai/whisper/discussions/838
39. ctc-forced-aligner - https://github.com/MahmoudAshraf97/ctc-forced-aligner
40. stable-ts - https://github.com/jianfch/stable-ts
41. torchaudio forced_align - https://docs.pytorch.org/audio/main/generated/torchaudio.functional.forced_align.html
42. Unsloth requirements - https://unsloth.ai/docs/get-started/beginner-start-here/unsloth-requirements
43. vLLM LoRA docs - https://docs.vllm.ai/en/latest/features/lora.html ; example https://github.com/vllm-project/vllm/blob/main/examples/features/lora/lora_with_quantization_offline.py
44. NVIDIA RTX 4070 family specs - https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4070-family/
45. Case data README (local) - data_upstream/inventx-case-study/data/README.md
