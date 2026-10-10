# sprintd test50 – held-out Swiss German test calls

Fifty fictional phone calls between a bank advisor (Beratung) and a customer (Kundin or Kunde), in Swiss German, for testing the Sodium Secure compliance detector (alarm, review, no_alert). Held out: never use these texts or this audio to train or tune anything.

- 50 calls, 77.4 minutes of audio in total (82–112 s per call, mean 93 s), 253–305 words per call (mean 277)
- Verdicts: 17 alarm, 6 review, 27 no_alert
- Final validation: 0 errors (logs/validation.txt); `python3 check_rules.py families-test50.json` gives 50/50

## How it was built
1. Fifty dialogues written in Standard German with their labels (`texts_test50.jsonl`, field `de`).
2. Every sentence translated to Swiss German and synthesised by the FHNW STT4SG TTS demo (https://stt4sg.fhnw.ch/tts/, `translate_interface` and `speech_interface`). No local AI models: `make_calls.py` only sends requests, caches results, checks strings and mixes audio (Python standard library).
3. Each translation compared with its DE sentence by string rules (negations, numbers, names, key terms of decisive facts, digits, garbled words, length). On top, every decisive turn was read and all 1132 unique sentences were scanned for TTS glitches. 171 sentences went through `needs_review.csv`: 129 edited minimally, 42 kept as they were. All decisions were confirmed by Paul.
4. Sentences synthesised one by one in their speaker's dialect, then assembled per call (clean, noisy, one stem per speaker) with timestamps from sample counts.

Etiquette towards the FHNW service: one request at a time, 2 s pause, every result cached by sha1(endpoint + dialect + text), resumable, stop after 5 consecutive failures. 2377 API calls over 6 runs; no failed requests.

Usage terms: the TTS model may not be used commercially, the FHNW demos are not meant for production, and FHNW may store the entered texts for research. This is non-commercial hackathon test data: no model training, no commercial use. All names, firms, places and amounts are fictional.

## Files
| Path | Content |
|---|---|
| `texts_test50.jsonl` | One line per call: DE text, CH text per sentence (`ch_auto`, `ch_final`, `edited`), facts, evidence, Belege, Begründung, Offen, keyword hits, noise plan |
| `families-test50.json` | Copy of families-v3.json whose `gold` holds the 50 calls; `python3 check_rules.py families-test50.json predictions.json` scores a detector |
| `manifest.csv` | id, family, type, expected, duration_s, dialects, n_turns, edited_sentences |
| `calls/<id>/<id>_clean.wav` | Full call, both speakers, 16 kHz mono PCM16 |
| `calls/<id>/<id>_noisy.wav` | Telephone version of the clean file (see Audio) |
| `calls/<id>/<id>_Beratung.wav`, `_Kunde.wav` | One stem per speaker, call length, silence while the other speaks |
| `calls/<id>/<id>.json` | Labels plus start and end per turn and sentence, Belege times, noise events, SNR, act audio hash |
| `calls/<id>/<id>_DE.txt`, `_CH.txt` | Transcripts turn by turn with timestamps; `_CH.txt` is the transcript of the audio |
| `calls/<id>/<id>_outcept.txt` | Outcept script format (header like the examples plus the CH turns) |
| `needs_review.csv` | Every reviewed sentence: DE, CH from the TTS, problem, decision, `ch_final`, note |
| `voice_check/` | One sample per dialect voice; `voices.csv` with median pitch |
| `logs/progress.log`, `logs/validation.txt` | Build log and final validation |
| `make_calls.py`, `run.command` | Build script and double-click start |
| `cache/` | API results (translations and speech), so reruns need no API calls. Only on Paul's Mac, not in the team repo (`data/test50/`) |
| `check_rules.py`, `Stichwortliste.json`, `kit/`, `test50-kit.zip` | Team kit: rule logic and scorer, keyword list, example scripts |

## Design
- 15 contrastive pairs (3 per alarm family), 5 review cases, 5 keyword traps, 3 numbers pairs, 4 multi-topic calls.
- Pairs: A and B differ in one early turn (T003–T006) that flips one slot; the act comes at least 5 turns later, word for word identical, with an indirect reference back. The act audio is byte-identical within each pair, clean and noisy (18 of 18 pairs).
- Keywords from `Stichwortliste.json` occur in 6 of 17 alarm calls; the other 11 have to be found from context. Traps contain negated, quoted, refused or public keywords.
- 10–18 turns, 1–3 sentences per turn, at most 180 characters per sentence, numbers written as words.

### Calls by family, type and verdict
| Family | Type | alarm | review | no_alert |
|---|---|---:|---:|---:|
| trade | pair | 3 | · | 3 |
| trade | review | · | 1 | · |
| trade | trap | · | · | 1 |
| access | pair | 3 | · | 3 |
| access | review | · | 1 | · |
| access | trap | · | · | 1 |
| access | multi | 1 | · | · |
| disclosure | pair | 3 | · | 3 |
| disclosure | review | · | 1 | · |
| disclosure | trap | · | · | 1 |
| disclosure | multi | · | 1 | 1 |
| documentation | pair | 3 | · | 3 |
| documentation | review | · | 1 | · |
| documentation | trap | · | · | 1 |
| documentation | multi | 1 | · | · |
| splitting | pair | 3 | · | 3 |
| splitting | review | · | 1 | · |
| splitting | trap | · | · | 1 |
| numbers | numbers_pair | · | · | 6 |
| **total** | | **17** | **6** | **27** |

Multi-topic calls are listed under the family that decides them (worst family wins).

### Dialects
Each call uses two different dialects; pair members share theirs. One FHNW voice per dialect: male in Graubünden, St. Gallen and Luzern, female elsewhere. Paul listened to all eight voice samples and confirmed they sound different; calls with two voices of the same gender pair voices of clearly different pitch.

| Dialect | Voice | Pitch (Hz) | Beratung | Kunde | Slots |
|---|---|---:|---:|---:|---:|
| Aargau | female | 195 | 4 | 7 | 11 |
| Basel | female | 250 | 8 | 5 | 13 |
| Bern | female | 211 | 7 | 5 | 12 |
| Graubünden | male | 111 | 8 | 6 | 14 |
| Luzern | male | 140 | 4 | 10 | 14 |
| St. Gallen | male | 123 | 6 | 7 | 13 |
| Valais | female | 211 | 7 | 5 | 12 |
| Zürich | female | 229 | 6 | 5 | 11 |

Calls per dialect combination (rows Beratung, columns Kunde):

| Beratung \ Kunde | Aargau | Basel | Bern | Graubü | Luzern | St. Ga | Valais | Zürich |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Aargau | · | · | · | · | 2 | 2 | · | · |
| Basel | 2 | · | 2 | · | 2 | · | · | 2 |
| Bern | · | · | · | 3 | 2 | 2 | · | · |
| Graubünden | 4 | 2 | · | · | · | · | 1 | 1 |
| Luzern | · | · | 2 | · | · | · | 2 | · |
| St. Gallen | · | 1 | 1 | · | · | · | 2 | 2 |
| Valais | · | 2 | · | 1 | 2 | 2 | · | · |
| Zürich | 1 | · | · | 2 | 2 | 1 | · | · |

## Audio
- Sentences trimmed at −40 dBFS and normalised to −20 dBFS RMS (peak at most −1 dBFS); 300–900 ms between turns, 120–300 ms between sentences, no overlaps.
- Noisy version: telephone band 300–3400 Hz (two RBJ biquads), pink noise at a planned SNR of 16.5–23.5 dB (measured 16.9–23.4 dB), one bell or knock partly over the key sentence of the act turn (−12 to −6 dB relative to the speech), one word restart on the context turn (first word cut at 35 %, 150 ms pause, full sentence), fixed −1 dB headroom (0 samples limited).
- The noise level comes from a fixed calibration noise per pair, so both members of a pair carry the same noise and the act turn stays byte-identical in the noisy files too.
- Every event is logged with its time in `<id>.json` (`noise_events`).

## Known limits
- Translation and pronunciation are the TTS's own. Dialect forms are sometimes mixed (for example Standard German digit words in a Basel sentence), and each dialect has a single voice, so the voice also gives away the dialect.
- Calls last 1.4–1.9 minutes. The TTS speaks faster than the brief's estimate, so 15 calls end under 1.5 minutes; word counts (253–305) stay within the brief's 150–450.
- Speech-rate check: 8–26 characters per second on the untrimmed TTS output instead of 8–22, because the Luzern voice reads at 21–24. No sentence had to be split; 9 one-word replies stay below 8 because the TTS adds silence around them, which trimming removes (WARN lines in logs/validation.txt).
- 203 sentence occurrences (129 unique sentences) use an edited CH text; `ch_auto` keeps the original TTS output.
- Python on the Mac had no TLS certificates, so `make_calls.py` used `/usr/bin/curl` for the API.

## Rerun
Rebuild on Paul's Mac, where the cache is: double-click `run.command`, or in Terminal `cd ~/Downloads/Sprintd_Zurich && caffeinate -i python3 make_calls.py --wait-review`. A rerun only calls the API for new or changed sentences; without the cache (e.g. from the repo copy) it would request all of them again, so don't rerun there.

- `--only <id>` one call (repeatable) · `--offline` no API calls · `--validate` validation only · `--voice-check` voice samples only
- Exit codes: 0 done, 2 stopped after 5 API failures, 3 sentences wait in `needs_review.csv`, 4 validation errors, 130 interrupted
- Change a CH sentence: set `decision` to `edit` and fill `ch_final` in `needs_review.csv` (add a row with the key if needed), then rerun; `keep` accepts the TTS text.

## Validation
1. Rule logic reproduces every expected verdict (worst family wins).
2. Pairs: one differing turn (T003–T006), identical act at least 5 turns later, lengths within ±5 words.
3. Every evidence turn exists and contains its fact; Belege times lie inside their turns.
4. `needs_review.csv`: 171 rows, 0 without a decision.
5. Audio: no empty or clipped snippet, timestamps monotonic, SNR 16.9–23.4 dB, act audio identical in 18 of 18 pairs.
6. No 9-word sequence shared with the example scripts (DE and CH: 0 found); no name used in more than two calls (0 found); no names from the examples (0 found).
7. **Open:** a Swiss German speaker on the team listens to these 10 calls, especially the Belege. If a decisive word is not understandable, rephrase that DE sentence (or set `ch_final`) and rerun.

| Call | Type | Expected | Dialects | Belege (key sentence) |
|---|---|---|---|---|
| T50-trade-01-A | pair | alarm | Basel / Luzern | T004 00:21.4–00:26.9, T012 01:07.8–01:12.2 |
| T50-access-02-B | pair | alarm | Graubünden / Aargau | T006 00:23.2–00:28.2, T012 00:53.6–00:59.0 |
| T50-disclosure-01-A | pair | alarm | Basel / Zürich | T005 00:20.4–00:25.9, T011 00:56.1–01:03.4 |
| T50-documentation-03-A | pair | alarm | St. Gallen / Zürich | T006 00:31.3–00:38.7, T012 01:06.3–01:12.8 |
| T50-splitting-03-A | pair | alarm | Bern / Luzern | T006 00:25.1–00:31.2, T012 00:54.4–00:58.1 |
| T50-trade-review | review | review | Graubünden / Valais | T006 00:29.1–00:32.9, T012 01:03.0–01:08.6 |
| T50-trade-trap | trap | no_alert | Zürich / St. Gallen | T004 00:18.3–00:23.9, T012 01:04.4–01:10.9 |
| T50-multi-01 | multi | alarm | Zürich / Graubünden | T008 00:36.2–00:42.4, T012 00:58.6–01:02.8 |
| T50-numbers-01-A | numbers_pair | no_alert | Bern / St. Gallen | T005 00:24.6–00:30.2, T012 01:01.1–01:06.4 |
| T50-trade-01-B | pair | no_alert | Basel / Luzern | T004 00:21.4–00:26.8, T012 01:09.2–01:13.5 |

